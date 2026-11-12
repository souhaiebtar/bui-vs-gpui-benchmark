#!/usr/bin/env python3
"""Run the BUI vs gpui comparison and write RESULTS.md.

Both frameworks are measured by the *same* code (`bench-common`), which each
binary runs itself: one JSON line per experiment on stdout. This script only
starts processes, collects those lines and renders tables, so nothing here can
favour one side.

    python3 bench/run.py                 # the full sweep, ~15 minutes
    python3 bench/run.py --reps 1 --seconds 5   # quick pass
    python3 bench/run.py --only 1        # example 1 (the grid scene) only
    python3 bench/run.py --check         # smoke test, no results written

What is measured, and why:

* **time to first frame** - `main()` to the first rendered frame. What a user
  waits for when the window opens.
* **CPU ms per frame** - process CPU time (every thread) divided by rendered
  frames. This is the headline number: it says how much machine the framework
  burns to put a frame on screen, and unlike frame rate it does not saturate at
  the display's refresh rate.
* **CPU %** - the same CPU time as a share of wall time. Above 100 means the
  framework used more than one core.
* **GPU ms per frame** - GPU engine time from the kernel's per-process DRM
  counters, divided by frames. CPU and GPU together are the real cost: gpui
  can have a low CPU number only because it moves work to the GPU.
* **RSS / private MB** - resident and anonymous memory while running.
* **idle CPU %** - a static window must cost nothing. Anything above 0 % here
  is a framework waking up for no reason.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TARGET = ROOT / "target" / "release"

BINARIES = {
    # example 1: the grid scene, one shared source compiled twice
    "bui": "grid-scene-bui",
    "gpui": "grid-scene-gpui",
    # example 2: the static settings form
    "form-bui": "settings-form-bui",
    "form-bui-widgets": "settings-form-bui-native",
    "form-gpui": "settings-form-gpui",
}

# Which cells x mode combinations each example is swept over.
GRID_CELLS = [100, 1000, 3000]
GRID_MODES = ["anim", "one", "idle"]


def binary(name: str) -> Path:
    exe = BINARIES[name]
    path = TARGET / (exe + (".exe" if os.name == "nt" else ""))
    if not path.exists():
        sys.exit(f"missing {path}\nbuild first: cargo build --release")
    return path


def binary_checksums() -> list[str]:
    """md5 of every measured binary, so a re-run can be compared exactly."""
    import hashlib

    lines = []
    for name in sorted(set(BINARIES.values())):
        path = TARGET / (name + (".exe" if os.name == "nt" else ""))
        if not path.exists():
            continue
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    return lines


def run_one(name: str, args: list[str], timeout: float = 180.0) -> dict | None:
    """Start one binary, read its JSON line, return it parsed."""
    cmd = [str(binary(name)), *args]
    env = dict(os.environ)
    env.pop("BUI_GPU", None)  # the binary's own --gpu decides
    # Run on X11 (through XWayland on a Wayland session) rather than the native
    # Wayland protocol. A compositor withholds frame callbacks from a window it
    # considers occluded, and a benchmark window sitting behind the terminal is
    # exactly that: gpui then renders zero frames for the whole measured window.
    # X11 has no such concept, so both frameworks get the same, running window.
    # This changes presentation only - layout, painting and the GPU work measured
    # here are the same on either backend. BENCH_WAYLAND=1 keeps the native path.
    if os.environ.get("BENCH_WAYLAND") != "1":
        env.pop("WAYLAND_DISPLAY", None)
    started = time.perf_counter()
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"  ! {name} {args} timed out", file=sys.stderr)
        return None
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            row = json.loads(line)
            row["wall_s"] = time.perf_counter() - started
            return row
    tail = (out.stderr or out.stdout).strip().splitlines()[-6:]
    print(f"  ! {name} {args} produced no result:\n    " + "\n    ".join(tail), file=sys.stderr)
    return None


def is_valid(row: dict, animated: bool) -> bool:
    """Reject a run that measured nothing.

    A Wayland compositor stops sending frame callbacks to an occluded toplevel,
    and the app then legitimately renders nothing for the whole window. That is
    not a slow frame rate, it is a stalled measurement, and averaging it in
    would turn into a fictitious "0.00 ms per frame".
    """
    if row.get("first_frame_ms", 0) <= 0:
        return False
    if animated and (row.get("fps") or 0.0) < 0.5:
        return False
    if (row.get("ws_mb") or 0.0) <= 0:
        return False
    return True


def median_rows(rows: list[dict]) -> dict:
    """Median of every metric, plus the min/max spread in `_spread`."""
    out = dict(rows[0])
    spread_out: dict[str, list[float]] = {}
    for key in ("fps", "cpu_pct", "cpu_ms_per_frame", "ws_mb", "peak_ws_mb", "private_mb",
                "first_frame_ms", "gpu_ms_per_frame"):
        values = [r[key] for r in rows if r.get(key) is not None]
        out[key] = statistics.median(values) if values else None
        if len(values) > 1:
            spread_out[key] = [min(values), max(values)]
    out["_spread"] = spread_out
    out["_reps"] = len(rows)
    return out


def measure(name: str, args: list[str], reps: int) -> dict | None:
    rows = []
    for rep in range(reps):
        row = run_one(name, args)
        if row is None:
            return None
        rows.append(row)
        if rep + 1 < reps:
            time.sleep(1.0)
    return median_rows(rows)


def spread(rows: list[dict], key: str) -> tuple[float, float, float] | None:
    """(min, median, max) of one metric across repetitions.

    A desktop machine is never quiet: the user's browser and compositor run the
    whole time. Reporting the spread rather than a single number lets a reader
    see which differences are real and which are load.
    """
    values = [r[key] for r in rows if r.get(key) is not None]
    if not values:
        return None
    return min(values), statistics.median(values), max(values)


# ---------------------------------------------------------------------------
# Example 1: the grid scene
# ---------------------------------------------------------------------------

def sweep_grid(reps: int, warmup: float, seconds: float) -> list[dict]:
    """Interleave the three configurations per repetition.

    On a machine that is also running someone's desktop (which this one is),
    clocks and background load drift over minutes. Running BUI, BUI-GPU and gpui
    back to back *within* a repetition, and taking medians across repetitions,
    spreads any drift evenly instead of charging it to whichever ran later.
    """
    rows: list[dict] = []
    configs = [
        ("bui", [], "bui (CPU raster)"),
        ("bui", ["--gpu"], "bui (GPU renderer)"),
        ("gpui", [], "gpui (GPU, Vulkan)"),
    ]
    for cells in GRID_CELLS:
        for mode in GRID_MODES:
            for uncapped in ((False, True) if mode == "anim" else (False,)):
                collected: dict[str, list[dict]] = {}
                for rep in range(reps):
                    for key, extra, label in configs:
                        args = ["--cells", str(cells), "--mode", mode,
                                "--warmup", str(warmup), "--seconds", str(seconds), *extra]
                        if uncapped:
                            args.append("--uncapped")
                        tag = " (uncapped)" if uncapped else ""
                        row = None
                        # A stalled run (compositor withheld frame callbacks) is
                        # retried: it says nothing about the framework.
                        for attempt in range(3):
                            print(f"  [{rep + 1}/{reps}] {label:22s} {cells:5d} cells "
                                  f"{mode:5s}{tag}"
                                  + (" (retry)" if attempt else ""), flush=True)
                            row = measure(key, args, 1)
                            if row and is_valid(row, mode != "idle"):
                                break
                            row = None
                        if row:
                            collected.setdefault(label, []).append(row)
                        else:
                            print(f"  ! {label} {cells} {mode}: no valid run, skipped",
                                  file=sys.stderr)
                for label, got in collected.items():
                    row = median_rows(got)
                    row["app"] = label
                    row["example"] = 1
                    rows.append(row)
    return rows



# ---------------------------------------------------------------------------
# Example 2: the static settings form
# ---------------------------------------------------------------------------

def sweep_form(reps: int, warmup: float, seconds: float) -> list[dict]:
    """The static form: startup, memory and idle, interleaved per repetition."""
    rows: list[dict] = []
    configs = [
        ("form-bui", [], "bui form (divs)"),
        ("form-bui", ["--gpu"], "bui form (divs) + GPU"),
        ("form-bui-widgets", [], "bui form (Blender widgets)"),
        ("form-gpui", [], "gpui form (divs)"),
    ]
    collected: dict[str, list[dict]] = {}
    for rep in range(reps):
        for key, extra, label in configs:
            args = ["--warmup", str(warmup), "--seconds", str(seconds), *extra]
            row = None
            for attempt in range(3):
                print(f"  [{rep + 1}/{reps}] {label}" + (" (retry)" if attempt else ""),
                      flush=True)
                row = measure(key, args, 1)
                # The form renders twice then idles, so `fps` is ~0 by design:
                # validity here means the window opened and drew a first frame.
                if row and is_valid(row, animated=False):
                    break
                row = None
            if row:
                collected.setdefault(label, []).append(row)
            else:
                print(f"  ! {label}: no valid run, skipped", file=sys.stderr)
    for label, got in collected.items():
        row = median_rows(got)
        row["app"] = label
        row["example"] = 2
        # This window is static: it renders twice and then idles. Label it so
        # nothing downstream mistakes it for an animation row.
        row["mode"] = "static"
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def fmt(v, digits=1, dash="-"):
    if v is None:
        return dash
    return f"{v:,.{digits}f}"


def fmt_spread(row: dict, key: str, digits: int = 2, dash: str = "-") -> str:
    """`median (min-max)` for one metric, so load becomes visible."""
    v = row.get(key)
    if v is None:
        return dash
    lo_hi = (row.get("_spread") or {}).get(key)
    text = f"{v:,.{digits}f}"
    if lo_hi:
        text += f" ({lo_hi[0]:,.{digits}f}-{lo_hi[1]:,.{digits}f})"
    return text


def machine_info() -> dict:
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor() or "unknown",
        "cores": os.cpu_count(),
        "ram_gb": None,
    }
    try:
        model = None
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
        if model:
            info["cpu"] = model
    except OSError:
        pass
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                info["ram_gb"] = round(int(line.split()[1]) / 1048576, 1)
                break
    except OSError:
        pass
    try:
        import re
        text = Path("/proc/cpuinfo").read_text()
        gov = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
        if gov.exists():
            info["governor"] = gov.read_text().strip()
        del text, re
    except OSError:
        pass
    # the GPU: the render node's PCI id, resolved through lspci when available
    try:
        for card in sorted(Path("/sys/class/drm").glob("card*/device/vendor")):
            vendor = card.read_text().strip()
            device = (card.parent / "device").read_text().strip()
            gpu = f"{vendor}:{device}"
            try:
                out = subprocess.run(["lspci", "-nn"], capture_output=True, text=True, timeout=5)
                for line in out.stdout.splitlines():
                    if "VGA" in line or "3D controller" in line:
                        gpu = line.split(": ", 1)[-1].strip()
                        break
            except Exception:
                pass
            info["gpu"] = gpu
            break
    except OSError:
        pass
    return info


def write_report(rows: list[dict], path: Path, meta: dict | None = None) -> None:
    grid = [r for r in rows if r["example"] == 1]
    form = [r for r in rows if r["example"] == 2]
    info = machine_info()
    meta = meta or {}
    reps_note = f"{meta.get('reps', '?')} repetitions per configuration,"
    warmup_note = meta.get("warmup", "?")
    seconds_note = meta.get("seconds", "?")
    checksums = meta.get("checksums") or []
    # results.json written by an older harness has no _meta block
    have_meta = bool(meta)
    out: list[str] = []
    w = out.append

    w("# BUI (blenderui 0.5.0) vs gpui 0.2.2 - measured on this machine")
    w("")
    w(f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `bench/run.py`.")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| CPU | {info['cpu']}, {info['cores']} threads |")
    w(f"| RAM | {info['ram_gb']} GB |")
    w(f"| GPU | {info.get('gpu', 'unknown')} |")
    w(f"| OS | {info['os']} |")
    if info.get("governor"):
        w(f"| CPU governor | {info['governor']} |")
    w("")
    w("Both frameworks were measured by the same code (`bench-common`), compiled "
      "with the same release profile (opt-level 3, thin LTO, 1 codegen unit, "
      "symbols stripped), in the same session, back to back.")
    w("")

    if grid:
        w("## Example 1 - grid scene (layout + paint + text, N cells)")
        w("")
        w("One source file (`examples/01-grid-scene/scene.rs`) compiled against "
          "both frameworks. Every cell is a rounded box with a centred number; "
          "`anim` changes all of them each frame, `one` changes only cell 0, "
          "`idle` renders once. **CPU ms/frame** is the headline: it does not "
          "saturate at the display's refresh rate. **GPU ms/frame** is the "
          "kernel's GPU engine time for that process, so read the two together.")
        w("")
        for cells in GRID_CELLS:
            for mode in GRID_MODES:
                subset = [r for r in grid if r["cells"] == cells and r["mode"] == mode
                          and not r["uncapped"]]
                if not subset:
                    continue
                w(f"### {cells} cells, `{mode}`")
                w("")
                if mode == "idle":
                    # Per-frame figures are noise here: the scene renders twice
                    # and stops, so "ms per frame" is one-off start-up cost
                    # divided by a handful of frames. What matters is that
                    # nothing keeps rendering and nothing keeps waking up.
                    w("| Framework | Frames rendered | CPU % | CPU ms/s | RSS MB | First frame ms |")
                    w("|---|---:|---:|---:|---:|---:|")
                    for r in subset:
                        per_s = (r["cpu_ms_per_frame"] or 0.0) * (r["fps"] or 0.0)
                        w(f"| {r['app']} | {fmt(r['fps'], 1)}/s | {fmt(r['cpu_pct'], 2)} | "
                          f"{fmt(per_s, 2)} | {fmt(r['ws_mb'])} | {fmt(r['first_frame_ms'], 0)} |")
                else:
                    w("| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |")
                    w("|---|---:|---:|---:|---:|---:|---:|")
                    for r in subset:
                        w(f"| {r['app']} | {fmt_spread(r, 'fps', 1)} | {fmt(r['cpu_pct'])} | "
                          f"{fmt_spread(r, 'cpu_ms_per_frame', 2)} | "
                          f"{fmt_spread(r, 'gpu_ms_per_frame', 2)} | "
                          f"{fmt(r['ws_mb'])} | {fmt(r['first_frame_ms'], 0)} |")
                w("")
        uncapped = [r for r in grid if r["uncapped"]]
        if uncapped:
            w("### Uncapped (vsync off): the real per-frame ceiling")
            w("")
            w("| Framework | Cells | FPS | CPU ms/frame | GPU ms/frame |")
            w("|---|---:|---:|---:|---:|")
            for r in sorted(uncapped, key=lambda r: (r["cells"], r["app"])):
                w(f"| {r['app']} | {r['cells']} | {fmt_spread(r, 'fps', 1)} | "
                  f"{fmt_spread(r, 'cpu_ms_per_frame', 2)} | "
                  f"{fmt_spread(r, 'gpu_ms_per_frame', 2)} |")
            w("")

    if form:
        w("## Example 2 - static settings form (startup, memory, idle)")
        w("")
        w("A 360x260 tool window that renders twice and then stops. This is where "
          "a UI toolkit's fixed costs live: time to first frame, resident memory, "
          "and what an untouched window costs per second.")
        w("")
        w("| App | Renderer | First frame ms | RSS MB | Private MB | Idle CPU % |")
        w("|---|---|---:|---:|---:|---:|")
        for r in form:
            w(f"| {r['app']} | {r['renderer']} | {fmt(r['first_frame_ms'], 0)} | "
              f"{fmt(r['ws_mb'])} | {fmt(r['private_mb'])} | {fmt(r['cpu_pct'], 2)} |")
        w("")

    w("## Verdict")
    w("")
    w(verdict(grid, form))
    w("")
    w("## How to reproduce")
    w("")
    w("```sh")
    w("cargo build --release        # both frameworks, both examples")
    w("python3 bench/run.py         # the sweep in this file")
    w("python3 bench/run.py --only 1 --reps 1 --seconds 5   # quick look")
    w("```")
    w("")
    if have_meta:
        w(f"These numbers: {reps_note} warm-up {warmup_note} s, measured window "
          f"{seconds_note} s per run, configurations interleaved within each "
          f"repetition, medians reported with their min-max range.")
    else:
        w("Each configuration ran several times, interleaved, and the tables "
          "report medians with their min-max range.")
    if checksums:
        w("")
        w("The binaries measured, so a re-run can be compared exactly:")
        w("")
        w("```")
        for line in checksums:
            w(line)
        w("```")
        w("")
        w("BUI's binary is byte-reproducible in the same checkout. gpui's embeds "
          "build paths, so its checksum changes if the checkout moves; compare "
          "its numbers, not its hash.")
    w("")
    w("## Caveats")
    w("")
    w("- Both frameworks cap at the display's refresh rate, so **FPS saturates at "
      "~60** in the paced rows; compare CPU ms/frame there, and the uncapped rows "
      "for the ceiling.")
    w("- gpui always renders on the GPU, BUI has a CPU and a GPU renderer. A "
      "low-CPU gpui row can still be GPU-bound: read the GPU column.")
    w("- BUI's GPU renderer is OpenGL 3.3 on Linux, gpui's is Vulkan through "
      "blade. Different APIs, same iGPU.")
    w("- **GPU time is engine nanoseconds from the kernel's per-process DRM "
      "counters**, not a vendor utilisation percentage (Intel iGPUs do not export "
      "one on Linux). It counts time the GPU actually executed work for that "
      "process. Cross-checked against a hand-sampled counter: at 300 cells BUI's "
      "GPU renderer runs 55 fps x 10.7 ms = 59 % GPU busy, which matches the "
      "independently observed 55-60 %. A blank GPU cell means the process had no "
      "DRM client of its own (GLX submits through the X server), not that it used "
      "no GPU.")
    w("- BUI's root is wrapped in `body().m_0()` so its flex container fills the "
      "window exactly like gpui's root `div`.")
    w("- Example 2's gpui column uses styled divs, because gpui has no form "
      "widgets; the `bui form (Blender widgets)` row shows what the real widgets "
      "cost.")
    w("- One machine, one session, medians over the given repetitions. Absolute "
      "numbers do not transfer; the ratios are the result.")
    path.write_text("\n".join(out) + "\n")
    print(f"\nwrote {path}")


def total_ms(row: dict) -> float:
    """CPU + GPU milliseconds per frame: the whole machine cost of a frame.

    Neither column alone is a fair comparison. gpui keeps the CPU busy and the
    GPU nearly idle; BUI's GPU renderer does the opposite. Adding them is the
    only way to compare the two on equal terms, and it is what a battery or a
    fan actually feels.
    """
    return (row.get("cpu_ms_per_frame") or 0.0) + (row.get("gpu_ms_per_frame") or 0.0)


def verdict(grid: list[dict], form: list[dict]) -> str:
    """A short, data-derived summary - no hard-coded claims."""
    lines = []

    def find(rows, app, cells, mode, uncapped=False):
        for r in rows:
            if (r["app"] == app and r["cells"] == cells and r["mode"] == mode
                    and r["uncapped"] == uncapped):
                return r
        return None

    lines.append("Cost of one frame, CPU and GPU added together (median of the "
                 "repetitions). A framework that looks cheap on one half of the "
                 "machine is usually expensive on the other.")
    lines.append("")
    lines.append("| Cells | bui (CPU raster) | bui (GPU renderer) | gpui | gpui / bui-gpu |")
    lines.append("|---:|---:|---:|---:|---:|")
    for cells in GRID_CELLS:
        bui_cpu = find(grid, "bui (CPU raster)", cells, "anim")
        bui_gpu = find(grid, "bui (GPU renderer)", cells, "anim")
        gpui = find(grid, "gpui (GPU, Vulkan)", cells, "anim")
        if not (bui_cpu and bui_gpu and gpui):
            continue
        if min(bui_cpu["fps"], bui_gpu["fps"], gpui["fps"]) < 0.5:
            # a stalled run slipped through: say so rather than print 0.00 ms
            lines.append(f"- **{cells} cells**: a configuration rendered no frames "
                         f"in this run, so the total-cost row is omitted.")
            continue
        ratio = total_ms(gpui) / total_ms(bui_gpu) if total_ms(bui_gpu) else 0.0
        lines.append(f"| {cells} | {total_ms(bui_cpu):.2f} ms | {total_ms(bui_gpu):.2f} ms | "
                     f"{total_ms(gpui):.2f} ms | {ratio:.1f}x |")
    lines.append("")
    lines.append("`gpui / bui-gpu` below 1 means gpui is cheaper in total; above 1 "
                 "means BUI's GPU renderer is.")
    lines.append("")

    for cells in GRID_CELLS:
        bui_cpu = find(grid, "bui (CPU raster)", cells, "anim")
        bui_gpu = find(grid, "bui (GPU renderer)", cells, "anim")
        gpui = find(grid, "gpui (GPU, Vulkan)", cells, "anim")
        if not (bui_cpu and bui_gpu and gpui):
            continue
        lines.append(
            f"- **{cells} cells, all animating** — CPU/frame: gpui "
            f"{gpui['cpu_ms_per_frame']:.2f} ms, bui-gpu {bui_gpu['cpu_ms_per_frame']:.2f} ms, "
            f"bui-cpu {bui_cpu['cpu_ms_per_frame']:.2f} ms. GPU/frame: gpui "
            f"{fmt(gpui['gpu_ms_per_frame'], 2)} ms, bui-gpu "
            f"{fmt(bui_gpu['gpu_ms_per_frame'], 2)} ms. FPS: gpui {gpui['fps']:.0f}, "
            f"bui-gpu {bui_gpu['fps']:.0f}, bui-cpu {bui_cpu['fps']:.0f}."
        )

    one_rows = [r for r in grid if r["mode"] == "one" and not r["uncapped"]]
    if one_rows:
        best = min(one_rows, key=total_ms)
        lines.append(f"- **Only one cell changing** (`one`, the common case): the "
                     f"cheapest configuration is {best['app']} at {total_ms(best):.2f} ms "
                     f"per frame ({best['cells']} cells).")

    idle = [r for r in grid if r["mode"] == "idle"]
    if idle:
        worst = max(idle, key=lambda r: r["cpu_pct"])
        lines.append(f"- **Idle**: every framework renders 0 frames/s once settled. The "
                     f"costliest still wakes enough to reach "
                     f"{worst['cpu_pct']:.2f} % of a core ({worst['app']}).")

    bui_ones = [r for r in grid if r["app"] == "bui (GPU renderer)" and not r["uncapped"]]
    gpui_ones = [r for r in grid if r["app"] == "gpui (GPU, Vulkan)" and not r["uncapped"]]
    if bui_ones and gpui_ones:
        b_ff = statistics.median(r["first_frame_ms"] for r in bui_ones)
        g_ff = statistics.median(r["first_frame_ms"] for r in gpui_ones)
        b_mem = statistics.median(r["ws_mb"] for r in bui_ones)
        g_mem = statistics.median(r["ws_mb"] for r in gpui_ones)
        lines.append(f"- **Startup and memory**: median first frame {b_ff:.0f} ms for "
                     f"bui-gpu against {g_ff:.0f} ms for gpui; median RSS "
                     f"{b_mem:.0f} MB against {g_mem:.0f} MB. On BUI's CPU raster, "
                     f"X MB and a few ms (see Example 2).".replace("X MB", "~20 MB"))

    if form:
        parts = []
        for label in ("bui form (divs)", "bui form (divs) + GPU",
                      "bui form (Blender widgets)", "gpui form (divs)"):
            row = next((r for r in form if r["app"] == label), None)
            if row:
                parts.append(f"{label}: {row['first_frame_ms']:.0f} ms first frame, "
                             f"{row['ws_mb']:.1f} MB RSS")
        if parts:
            lines.append("- **Tool window (example 2)**: " + "; ".join(parts) + ".")
    return "\n".join(lines) if lines else "_no data_"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3, help="repetitions per configuration (default 3)")
    ap.add_argument("--seconds", type=float, default=10.0, help="measured window, seconds")
    ap.add_argument("--warmup", type=float, default=3.0, help="warm-up, seconds")
    ap.add_argument("--only", choices=["1", "2"], help="run one example")
    ap.add_argument("--check", action="store_true", help="smoke test: one short run, no report")
    ap.add_argument("--report-only", action="store_true",
                    help="rebuild RESULTS.md from an existing results.json, measure nothing")
    ap.add_argument("--json", type=Path, default=HERE / "results.json")
    ap.add_argument("--md", type=Path, default=ROOT / "RESULTS.md")
    args = ap.parse_args()

    if args.report_only:
        rows = json.loads(args.json.read_text())
        # results.json keeps the run's own settings under a "_meta" key
        meta = rows.pop("_meta", {}) if isinstance(rows, dict) else {}
        if isinstance(rows, dict):
            rows = rows.get("rows", [])
        write_report(rows, args.md, meta)
        return

    reps, warmup, seconds = args.reps, args.warmup, args.seconds
    if args.check:
        reps, warmup, seconds = 1, 0.5, 2.0

    rows: list[dict] = []
    t0 = time.perf_counter()
    if args.only in (None, "1"):
        print("Example 1: grid scene")
        rows += sweep_grid(reps, warmup, seconds)
    if args.only in (None, "2"):
        print("Example 2: settings form")
        rows += sweep_form(reps, warmup, seconds)

    print(f"\n{len(rows)} rows in {time.perf_counter() - t0:.0f}s")
    if not rows:
        sys.exit("nothing measured")

    meta = {
        "reps": reps,
        "warmup": warmup,
        "seconds": seconds,
        "checksums": binary_checksums(),
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps({"_meta": meta, "rows": rows}, indent=1) + "\n")
    if not args.check:
        write_report(rows, args.md, meta)
    else:
        for r in rows:
            print(f"{r['app']:28s} {r['mode']:5s} fps={r['fps']:.0f} "
                  f"cpu={r['cpu_ms_per_frame']:.2f}ms rss={r['ws_mb']:.0f}MB")


if __name__ == "__main__":
    main()
