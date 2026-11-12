#!/usr/bin/env python3
"""Regenerate the numeric tables of COMPARISON.md from bench/results.json.

Kept in the repo (not /tmp) so the detailed document can be refreshed from new
data without hand-editing 40 tables:

    python3 bench/tables.py > /tmp/tables.md

Then replace the block between `<!-- tables:start -->` and `<!-- tables:end -->`
in COMPARISON.md.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "bench/results.json").read_text())
rows = data["rows"] if isinstance(data, dict) else data
grid = [r for r in rows if r["example"] == 1]
form = [r for r in rows if r["example"] == 2]

APPS = ["bui (CPU raster)", "bui (GPU renderer)", "gpui (GPU, Vulkan)"]
SHORT = {"bui (CPU raster)": "BUI-CPU", "bui (GPU renderer)": "BUI-GPU",
         "gpui (GPU, Vulkan)": "gpui"}
CELLS = (100, 1000, 3000)


def find(app, cells, mode, unc=False):
    for r in grid:
        if (r["app"] == app and r["cells"] == cells and r["mode"] == mode
                and r["uncapped"] == unc):
            return r
    return None


def f(v, n=2, dash="-"):
    return dash if v is None else f"{v:,.{n}f}"


def sp(r, key, n=2):
    """median, with min-max in small text when more than one rep ran."""
    v = r.get(key)
    if v is None:
        return "-"
    lo_hi = (r.get("_spread") or {}).get(key)
    if lo_hi:
        return f"{v:,.{n}f} <sub>({lo_hi[0]:,.{n}f}–{lo_hi[1]:,.{n}f})</sub>"
    return f"{v:,.{n}f}"


def total(r):
    return (r.get("cpu_ms_per_frame") or 0) + (r.get("gpu_ms_per_frame") or 0)


out: list[str] = []

# --- one table per (cells, mode) -----------------------------------------
for cells in CELLS:
    for mode in ("anim", "one", "idle"):
        out.append(f"#### {cells} cells · `{mode}`\n")
        if mode == "idle":
            out.append("| Framework | Frames/s | CPU % | CPU ms/s | RSS MB | Private MB | First frame ms |")
            out.append("|---|---:|---:|---:|---:|---:|---:|")
            for app in APPS:
                r = find(app, cells, mode)
                if not r:
                    continue
                per_s = (r["cpu_ms_per_frame"] or 0) * (r["fps"] or 0)
                out.append(f"| {SHORT[app]} | {f(r['fps'], 1)} | {f(r['cpu_pct'], 2)} | "
                           f"{f(per_s, 2)} | {f(r['ws_mb'], 1)} | {f(r['private_mb'], 1)} | "
                           f"{f(r['first_frame_ms'], 1)} |")
        else:
            out.append("| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | **Total ms** | RSS MB | Private MB | First frame ms |")
            out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
            for app in APPS:
                r = find(app, cells, mode)
                if not r:
                    continue
                out.append(f"| {SHORT[app]} | {sp(r, 'fps', 1)} | {f(r['cpu_pct'], 1)} | "
                           f"{sp(r, 'cpu_ms_per_frame')} | {sp(r, 'gpu_ms_per_frame')} | "
                           f"**{f(total(r))}** | {f(r['ws_mb'], 1)} | {f(r['private_mb'], 1)} | "
                           f"{f(r['first_frame_ms'], 1)} |")
        out.append("")

# --- uncapped -------------------------------------------------------------
out.append("#### Uncapped (vsync off)\n")
out.append("| Framework | Cells | FPS | CPU ms/frame | GPU ms/frame | Total ms |")
out.append("|---|---:|---:|---:|---:|---:|")
for cells in CELLS:
    for app in APPS:
        r = find(app, cells, "anim", unc=True)
        if not r:
            continue
        out.append(f"| {SHORT[app]} | {cells} | {sp(r, 'fps', 1)} | "
                   f"{sp(r, 'cpu_ms_per_frame')} | {sp(r, 'gpu_ms_per_frame')} | "
                   f"{f(total(r))} |")
out.append("")

# --- totals matrix --------------------------------------------------------
out.append("#### Total cost matrix (CPU + GPU ms per frame)\n")
out.append("| Cells | BUI-CPU | BUI-GPU | gpui | gpui ÷ BUI-GPU | gpui ÷ BUI-CPU |")
out.append("|---:|---:|---:|---:|---:|---:|")
for cells in CELLS:
    a, b, c = (find(APPS[0], cells, "anim"), find(APPS[1], cells, "anim"),
               find(APPS[2], cells, "anim"))
    if not (a and b and c):
        continue
    out.append(f"| {cells} | {f(total(a))} | {f(total(b))} | {f(total(c))} | "
               f"{total(c)/total(b):.2f}x | {total(c)/total(a):.2f}x |")
out.append("")

# --- scaling --------------------------------------------------------------
out.append("#### Scaling from 100 to 3000 cells (30x the cells)\n")
out.append("| Framework | CPU ms/frame | | GPU ms/frame | | Total ms/frame | | FPS | |")
out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for app in APPS:
    a, b = find(app, 100, "anim"), find(app, 3000, "anim")
    grow = lambda x, y: f"{y/x:.1f}x" if x else "-"
    gpu_grow = (grow(a["gpu_ms_per_frame"], b["gpu_ms_per_frame"])
                if a["gpu_ms_per_frame"] else "-")
    out.append(f"| {SHORT[app]} | {f(a['cpu_ms_per_frame'])} → {f(b['cpu_ms_per_frame'])} | "
               f"{grow(a['cpu_ms_per_frame'], b['cpu_ms_per_frame'])} | "
               f"{f(a['gpu_ms_per_frame'])} → {f(b['gpu_ms_per_frame'])} | {gpu_grow} | "
               f"{f(total(a))} → {f(total(b))} | {grow(total(a), total(b))} | "
               f"{f(a['fps'], 0)} → {f(b['fps'], 0)} | {f(b['fps']/a['fps'], 2)}x |")
out.append("")

# --- memory ---------------------------------------------------------------
out.append("#### Resident memory against scene size\n")
out.append("| Framework | 100 cells | 1000 cells | 3000 cells | Growth |")
out.append("|---|---:|---:|---:|---:|")
for app in APPS:
    vals = [find(app, c, "anim")["ws_mb"] for c in CELLS]
    out.append(f"| {SHORT[app]} | {vals[0]:.1f} MB | {vals[1]:.1f} MB | {vals[2]:.1f} MB | "
               f"+{vals[2]-vals[0]:.1f} MB |")
out.append("")

# --- example 2 ------------------------------------------------------------
out.append("#### Example 2 · static settings form\n")
out.append("| App | Renderer | First frame ms | RSS MB | Private MB | Idle CPU % |")
out.append("|---|---|---:|---:|---:|---:|")
for r in form:
    out.append(f"| {r['app']} | {r['renderer']} | {sp(r, 'first_frame_ms', 1)} | "
               f"{sp(r, 'ws_mb', 1)} | {f(r['private_mb'], 1)} | {f(r['cpu_pct'], 2)} |")
out.append("")

# --- derived ratios -------------------------------------------------------
out.append("#### Derived ratios (1000 cells, animating)\n")
a, b, c = (find(APPS[0], 1000, "anim"), find(APPS[1], 1000, "anim"),
           find(APPS[2], 1000, "anim"))
out.append(f"- gpui CPU per frame ÷ BUI-GPU CPU per frame: **{c['cpu_ms_per_frame']/b['cpu_ms_per_frame']:.2f}x**")
out.append(f"- BUI-GPU GPU per frame ÷ gpui GPU per frame: **{b['gpu_ms_per_frame']/c['gpu_ms_per_frame']:.2f}x**")
out.append(f"- gpui total ÷ BUI-GPU total: **{total(c)/total(b):.2f}x**")
out.append(f"- gpui total ÷ BUI-CPU total: **{total(c)/total(a):.2f}x**")
out.append(f"- gpui RSS ÷ BUI-CPU RSS: **{c['ws_mb']/a['ws_mb']:.2f}x** (BUI smaller)")
out.append(f"- gpui first frame ÷ BUI-CPU first frame: **{c['first_frame_ms']/a['first_frame_ms']:.0f}x**")
out.append("")

print("\n".join(out))
