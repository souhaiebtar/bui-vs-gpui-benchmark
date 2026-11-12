#!/usr/bin/env python3
"""Screenshot each example, so the repository shows what was measured.

    python3 bench/shots.py

Needs an X11 or XWayland display (`DISPLAY`). Runs each app in animation mode
for a couple of seconds, grabs the window with ImageMagick's `import` (or
`grim` on Wayland-only setups), and writes `docs/shots/*.png`.

The screenshots are documentation, not evidence: the numbers are in RESULTS.md.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TARGET = ROOT / "target" / "release"
OUT = ROOT / "docs" / "shots"

APPS = [
    ("grid-bui-cpu.png", "grid-scene-bui", "bui-grid-cpu",
     ["--cells", "100", "--mode", "anim", "--title", "bui-grid-cpu",
      "--warmup", "1", "--seconds", "8"]),
    ("grid-bui-gpu.png", "grid-scene-bui", "bui-grid-gpu",
     ["--cells", "100", "--mode", "anim", "--gpu", "--title", "bui-grid-gpu",
      "--warmup", "1", "--seconds", "8"]),
    ("grid-gpui.png", "grid-scene-gpui", "gpui-grid",
     ["--cells", "100", "--mode", "anim", "--title", "gpui-grid",
      "--warmup", "1", "--seconds", "8"]),
    ("form-bui.png", "settings-form-bui", "bui-form",
     ["--title", "bui-form", "--warmup", "1", "--seconds", "8"]),
    ("form-gpui.png", "settings-form-gpui", "gpui-form",
     ["--title", "gpui-form", "--warmup", "1", "--seconds", "8"]),
]


def grabber() -> list[str] | None:
    """The command that grabs one window, if one is available.

    `import` (ImageMagick) and `xwd` both take an X11 window id, which is what
    `window_ids` returns. Wayland has no cross-application grab, so a client
    running on the native Wayland protocol cannot be captured from outside -
    gpui picks Wayland when it can, BUI uses X11/XWayland here.
    """
    if shutil.which("import"):
        return ["import"]
    if shutil.which("xwd"):
        return ["xwd"]
    return None


def window_ids(title: str, timeout: float = 15.0) -> list[str]:
    """X11 window ids whose title matches, waiting until one maps.

    Wayland has no cross-application window grab, so this only works through
    XWayland - which is where these windows appear on a KDE Wayland session.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            out = subprocess.run(["xdotool", "search", "--name", title],
                                 capture_output=True, text=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        ids = [line.strip() for line in out.stdout.split() if line.strip()]
        # keep only mapped, non-tiny windows (toolkit helper windows are 1x1)
        good = []
        for wid in ids:
            try:
                geo = subprocess.run(["xdotool", "getwindowgeometry", wid],
                                     capture_output=True, text=True, timeout=5)
            except subprocess.TimeoutExpired:
                continue
            if "Geometry:" in geo.stdout:
                try:
                    dims = geo.stdout.split("Geometry:")[1].split()[0]
                    w, h = (int(x) for x in dims.split("x"))
                    if w > 200 and h > 150:
                        good.append(wid)
                except (IndexError, ValueError):
                    pass
        if good:
            return good
        time.sleep(0.3)
    return []


def to_png(xwd: bytes) -> bytes:
    """Convert XWD bytes to PNG with whatever is installed."""
    for cmd in (["convert", "xwd:-", "png:-"], ["magick", "xwd:-", "png:-"],
                ["ffmpeg", "-loglevel", "error", "-f", "xwd_pipe", "-i", "-",
                 "-f", "image2pipe", "-vcodec", "png", "-"]):
        if not shutil.which(cmd[0]):
            continue
        out = subprocess.run(cmd, input=xwd, capture_output=True, timeout=60)
        if out.returncode == 0 and out.stdout:
            return out.stdout
    return b""


def main() -> int:
    grab = grabber()
    if not grab:
        print("no screenshot tool: install ImageMagick (`import`) or x11-apps (`xwd`)")
        return 1
    if not os.environ.get("DISPLAY"):
        print("no X11 display: set DISPLAY (XWayland counts) first")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    for name, exe, title, args in APPS:
        path = TARGET / exe
        if not path.exists():
            print(f"  skip {name}: {path} not built")
            continue
        print(f"  {name}")
        time.sleep(0.5)
        # Force the X11 window path so the window can be grabbed: Wayland has
        # no cross-application capture. Rendering and timing are unaffected;
        # this script only takes pictures.
        env = dict(os.environ)
        env.pop("WAYLAND_DISPLAY", None)
        app = subprocess.Popen([str(path), *args], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, env=env)
        try:
            ids = window_ids(title)
            if not ids:
                print(f"    no X11 window titled {title!r} - the app may be "
                      f"running natively on Wayland, which cannot be grabbed")
                continue
            if grab[0] == "xwd":
                # `xwd` writes XWD, which browsers do not show; convert it with
                # whatever image tool this machine has.
                raw = subprocess.run([*grab, "-id", ids[0], "-silent"],
                                     capture_output=True, timeout=30)
                if raw.returncode != 0 or not raw.stdout:
                    print(f"    grab failed: {raw.stderr.decode()[:200]}")
                    continue
                data = to_png(raw.stdout)
                if not data:
                    print("    grabbed XWD but no converter (convert/magick/ffmpeg) found")
                    continue
            else:
                out = subprocess.run([*grab, "-window", ids[0], "png:-"],
                                     capture_output=True, timeout=30)
                data = out.stdout if out.returncode == 0 else b""
                if not data:
                    print(f"    grab failed: {out.stderr.decode()[:200]}")
                    continue
            (OUT / name).write_bytes(data)
            print(f"    wrote {(OUT / name).relative_to(ROOT)} ({len(data) // 1024} KB)")
        finally:
            app.terminate()
            try:
                app.wait(timeout=10)
            except subprocess.TimeoutExpired:
                app.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
