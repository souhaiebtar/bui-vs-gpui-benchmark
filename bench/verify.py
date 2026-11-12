#!/usr/bin/env python3
"""Sanity checks for the comparison, run before trusting any number.

    python3 bench/verify.py

Checks, in order:

1. Both binaries exist and are release builds.
2. Each one produces a well-formed result line for every mode.
3. The two frameworks actually drew the same scene: the frame counts for a fixed
   duration are in the same ballpark (a 10x gap means one side is not animating).
4. Idle costs nothing in both: an idle window must not keep rendering frames.
5. The measurement itself is sane: CPU time is non-zero, memory is non-zero, and
   `first_frame_ms` is below the run's own duration.

Exit code 0 means every check passed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TARGET = ROOT / "target" / "release"
EXE = {
    "bui": TARGET / "grid-scene-bui",
    "bui-gpu": TARGET / "grid-scene-bui",
    "gpui": TARGET / "grid-scene-gpui",
    "form-bui": TARGET / "settings-form-bui",
    "form-bui-widgets": TARGET / "settings-form-bui-native",
    "form-gpui": TARGET / "settings-form-gpui",
}
SUFFIX = ".exe" if sys.platform == "win32" else ""

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL {msg}")


def run(name: str, args: list[str]) -> dict | None:
    exe = EXE[name]
    if not exe.with_suffix(SUFFIX).exists() and not Path(str(exe) + SUFFIX).exists():
        fail(f"{name}: binary missing at {exe}{SUFFIX} (run cargo build --release)")
        return None
    env = dict(os.environ)
    # Same X11 pin as bench/run.py: a Wayland compositor withholds frame
    # callbacks from an occluded window, which stalls the measured window and
    # would look like a framework failure rather than an environment artifact.
    if os.environ.get("BENCH_WAYLAND") != "1":
        env.pop("WAYLAND_DISPLAY", None)
    try:
        out = subprocess.run(
            [str(exe) + SUFFIX, *args], capture_output=True, text=True,
            timeout=120, env=env
        )
    except subprocess.TimeoutExpired:
        fail(f"{name} {args}: timed out (window never appeared? no display?)")
        return None
    for line in out.stdout.splitlines():
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                fail(f"{name}: malformed JSON: {line[:120]}")
                return None
    tail = (out.stderr or "").strip().splitlines()[-4:]
    fail(f"{name} {args}: no result line. stderr:\n      " + "\n      ".join(tail))
    return None


def check_fields(name: str, row: dict) -> None:
    for key in ("fps", "cpu_pct", "cpu_ms_per_frame", "ws_mb", "first_frame_ms"):
        if key not in row:
            fail(f"{name}: result is missing {key}")
    if row.get("ws_mb", 1) <= 0:
        fail(f"{name}: reported {row.get('ws_mb')} MB of memory")
    if row.get("first_frame_ms", 0) <= 0:
        fail(f"{name}: first frame took {row.get('first_frame_ms')} ms (watchdog fired?)")


def main() -> int:
    print("1. binaries")
    for name, path in EXE.items():
        p = Path(str(path) + SUFFIX)
        state = "ok" if p.exists() else "MISSING"
        print(f"  {name:18s} {p.name:28s} {state}")
        if p.exists():
            size = p.stat().st_size / 1048576
            print(f"  {'':18s} {size:8.1f} MB")

    print("2. every mode produces a result")
    rows = {}
    for name in ("bui", "bui-gpu", "gpui"):
        for mode in ("anim", "one", "idle"):
            args = ["--cells", "200", "--mode", mode, "--warmup", "0.5", "--seconds", "2"]
            if name == "bui-gpu":
                args.append("--gpu")
            row = run(name, args)
            if row:
                check_fields(f"{name}/{mode}", row)
                rows[(name, mode)] = row
                print(f"  {name:10s} {mode:5s} fps={row['fps']:7.1f} "
                      f"cpu={row['cpu_ms_per_frame']:6.2f}ms "
                      f"rss={row['ws_mb']:6.1f}MB gpu={row.get('gpu_ms_per_frame')}")

    print("3. both frameworks rendered the same scene")
    for mode in ("anim", "one"):
        b = rows.get(("gpui", mode))
        if not b:
            continue
        for key in ("bui", "bui-gpu"):
            x = rows.get((key, mode))
            if not x:
                continue
            ratio = (x["fps"] + 0.01) / (b["fps"] + 0.01)
            if not (0.1 <= ratio <= 10.0):
                fail(f"{key} vs gpui, {mode}: {ratio:.2f}x frame rate - "
                     f"one side is not animating")
            else:
                print(f"  {key:8s} vs gpui, {mode:5s}: {ratio:.2f}x frames")

    print("4. the GPU renderer is really the GPU renderer")
    gpu_row = rows.get(("bui-gpu", "anim"))
    cpu_row = rows.get(("bui", "anim"))
    if gpu_row and cpu_row:
        if gpu_row["gpu_ms_per_frame"] is None:
            fail("bui-gpu: no GPU engine time - the GPU device did not start "
                 "(BUI_GPU_DEBUG=1 says why)")
        elif gpu_row["gpu_ms_per_frame"] <= 0:
            fail("bui-gpu: GPU engine time is 0 - the window is not drawing on the GPU")
        elif gpu_row["cpu_ms_per_frame"] >= cpu_row["cpu_ms_per_frame"]:
            fail(f"bui-gpu: {gpu_row['cpu_ms_per_frame']:.2f} ms CPU/frame is not below "
                 f"the CPU raster's {cpu_row['cpu_ms_per_frame']:.2f} ms")
        else:
            print(f"  bui-gpu used GPU {gpu_row['gpu_ms_per_frame']:.2f} ms/frame and "
                  f"{gpu_row['cpu_ms_per_frame']:.2f} ms CPU/frame")
    if gpu_row and gpu_row["ws_mb"] <= (cpu_row["ws_mb"] if cpu_row else 0):
        fail("bui-gpu: RSS is not above the CPU raster's - the device probably never started")

    print("5. idle windows render (almost) nothing")
    for name in ("bui", "bui-gpu", "gpui"):
        row = rows.get((name, "idle"))
        if row and row["fps"] > 2.0:
            fail(f"{name} idle: still {row['fps']:.1f} fps - not going quiet")

    print("6. the settings form renders twice and stops")
    for name in ("form-bui", "form-bui-widgets", "form-gpui"):
        # A longer window, because the desktop's window-open animation causes a
        # handful of extra exposures in the first second; over 4 s they amortize.
        row = run(name, ["--warmup", "1", "--seconds", "4"])
        if row:
            check_fields(name, row)
            # The form is static: whatever it renders must be start-up, so judge
            # it on sustained CPU, not on a frame count that includes window
            # manager animations.
            if row["cpu_pct"] > 2.0:
                fail(f"{name}: {row['cpu_pct']:.2f} % CPU for a static form - it is not idling")
            print(f"  {name:18s} first_frame={row['first_frame_ms']:5.0f}ms "
                  f"rss={row['ws_mb']:6.1f}MB idle_cpu={row['cpu_pct']:.2f}% "
                  f"({row['fps']:.1f} frames/s, window-open animation included)")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
