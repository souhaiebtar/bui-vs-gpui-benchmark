# BUI vs GPUI — the complete comparison

Everything measured, everything learned, and every caveat. This is the long
form; [`README.md`](README.md) is the short version, and [`RESULTS.md`](RESULTS.md)
is the raw generated tables.

| | **BUI** | **GPUI** |
|---|---|---|
| Repository | [ppmpreetham/BUI](https://github.com/ppmpreetham/BUI) | [zed-industries/zed · crates/gpui](https://github.com/zed-industries/zed/tree/main/crates/gpui) |
| Crate measured | `blenderui` **0.5.0** (published 2026-11-08) | `gpui` **0.2.2** (published 2026-10-30) |
| Language | C core (`kit/`, `gpu/`, `core/`) + thin Rust bindings | Rust |
| Origin | Blender's UI toolkit, decoupled from Blender | Zed's editor UI framework |
| Renderer | software raster by default; opt-in GPU (OpenGL 3.3 / D3D 11) | GPU only (Vulkan on Linux, Metal on macOS, D3D/Vulkan on Windows) |
| Layout | HTML/CSS semantics on taffy, gpui-style builders | taffy-based, builder API |
| Widgets | Blender's real widgets: number field, slider, colour picker, pie menu, node editor, file browser | primitives only; you build controls from `div`s |
| Text | FreeType + embedded Inter (Blender's rendering) | cosmic-text |
| Licence | GPL-3.0-or-later | Apache-2.0 (as part of Zed) |

Both expose the same builder syntax (`div().flex().gap_2()`), which is what makes
a controlled comparison possible: **one source file compiles against both**.

---

## 1. Machine and method

### The machine

| | |
|---|---|
| CPU | 11th Gen Intel Core i5-1135G7 @ 2.40 GHz, 4 cores / 8 threads |
| GPU | Intel TigerLake-LP GT2 [Iris Xe Graphics] `[8086:9a49]`, unified memory |
| RAM | 15.0 GB |
| OS | Debian GNU/Linux 13 (trixie), kernel 7.3.3-cachyos-x64v4 |
| Session | KDE Plasma on Wayland, XWayland on `:1` |
| OpenGL | 4.6 core, Mesa 26.1.4 (Intel driver) |
| Vulkan | libvulkan 1.4.309, Mesa Intel ICD |
| CPU governor | `powersave` ⚠️ |
| Rust | 1.99.1, release profile |

The `powersave` governor means clocks move under load. That is one reason every
configuration ran five times and the spread is reported.

### What was measured, and how

All measurement happens **inside each process**, in `bench-common`, a crate both
frameworks link. Neither framework's code is involved in taking a measurement.

| Metric | Source | Why it matters |
|---|---|---|
| `fps` | rendered frames ÷ measured wall time | throughput, but saturates at the display's refresh rate |
| `cpu_ms_per_frame` | `CLOCK_PROCESS_CPUTIME_ID` (all threads) ÷ frames | machine cost per frame; unlike FPS it does not cap at 60 |
| `cpu_pct` | CPU time ÷ wall time | >100 % means more than one core was used |
| `gpu_ms_per_frame` | `/proc/<pid>/fdinfo` `drm-engine-*` counters ÷ frames | the other half of the bill; CPU alone flatters GPU-heavy designs |
| **total** | `cpu_ms_per_frame + gpu_ms_per_frame` | **the honest headline** — see §3 |
| `ws_mb` | `/proc/self/status` `VmRSS` | resident memory while running |
| `private_mb` | `/proc/self/status` `RssAnon` | anonymous memory (not shared library pages) |
| `first_frame_ms` | `main()` → first rendered frame | what a user waits for |

### Why the GPU column is trustworthy

Intel iGPUs export no utilisation percentage on Linux, so the GPU column comes
from the kernel's per-process DRM engine counters, which count **nanoseconds the
GPU actually executed work for that process**.

This was cross-checked by hand. At 300 cells with `--gpu`, BUI reports 55 fps at
10.7 ms of GPU time per frame — i.e. 59 % GPU busy. Sampling the same counter
externally, once a second, gave 55–60 %. The numbers agree, so the column
measures what it claims.

A blank GPU cell means the process had no DRM client of its own (GLX submits
through the X server). It does **not** mean no GPU was used.

### Run parameters

```
repetitions:      5 per configuration
warm-up:          3 s minimum, then until the frame rate stops changing
measured window:  10 s
window:           1000 x 800 (example 1), 360 x 260 (example 2)
interleaving:     BUI-CPU, BUI-GPU, gpui back to back inside each repetition
```

Interleaving matters: on a machine that is also someone's desktop, clocks drift
over minutes. Running the three configurations adjacently spreads that drift
across them instead of charging it to whichever ran last.

Binaries measured (md5):

```
ed0aa489efef36d8f425302d0275c732  grid-scene-bui
1843f03c8abc8bca5e3e7824bdb4982a  grid-scene-gpui
e837da9bed384e1fa92f07ac4f05aee8  settings-form-bui
cc607e056b380951ecfb10f697a8e963  settings-form-bui-native
de64ed3dde09b3d6bdbef51e13ff893f  settings-form-gpui
```

---

## 2. The two examples

### Example 1 — grid scene (throughput)

`examples/01-grid-scene/scene.rs` is included by both crates. It builds a
full-window flex container (`flex-wrap`, 2 px gap, 2 px padding) filled with N
rounded cells, each holding a centred number at the same font size.

Three change modes:

| Mode | What changes per frame | What it models |
|---|---|---|
| `anim` | every cell's colour and label | worst case: full restyle, relayout, repaint |
| `one` | only cell 0 | the common case: a hover, a clock, a ticking value |
| `idle` | nothing | a window nobody is touching |

Swept at **100 / 1000 / 3000 cells**, paced (vsync) and uncapped.

| BUI, CPU raster | BUI, GPU renderer | gpui |
|---|---|---|
| ![grid on BUI's software raster](docs/shots/grid-bui-cpu.png) | ![grid on BUI's GPU renderer](docs/shots/grid-bui-gpu.png) | ![grid on gpui](docs/shots/grid-gpui.png) |

The same scene, the same pixels, three different runtimes.

### Example 2 — static settings form (fixed costs)

`examples/02-settings-form/form.rs` is a 360×260 tool window that renders twice
and then stops. It measures what a window costs when it is *not* animating:
start-up, memory, and idle CPU.

gpui has no form widgets, so the controls are styled `div`s on both sides —
identical markup. A third crate draws the same form with BUI's real Blender
widgets (`NumberField`, `Checkbox`, `ProgressBar`, `Button`) to show what the
native widgets cost on top.

| BUI (divs) | gpui (divs) |
|---|---|
| ![settings form drawn by BUI](docs/shots/form-bui.png) | ![settings form drawn by gpui](docs/shots/form-gpui.png) |

---

## 3. Results

### 3.1 The headline: total cost per frame

Neither the CPU nor the GPU column alone is a fair comparison — each framework
can look cheap by pushing work to the other half of the machine. Adding them is
the only like-for-like measure, and it is what a battery or a fan actually feels.

#### 100 cells · `anim`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | **Total ms** | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 49.8 <sub>(33.9–49.9)</sub> | 13.6 | 2.73 <sub>(2.66–5.26)</sub> | - | **2.73** | 19.2 | 11.0 | 2.5 |
| BUI-GPU | 57.3 <sub>(51.0–57.3)</sub> | 3.7 | 0.64 <sub>(0.63–1.18)</sub> | 9.84 <sub>(7.69–10.71)</sub> | **10.48** | 84.6 | 22.8 | 1.7 |
| gpui | 60.0 <sub>(58.8–60.0)</sub> | 13.0 | 2.16 <sub>(1.95–4.90)</sub> | 1.96 <sub>(1.86–2.73)</sub> | **4.12** | 88.1 | 25.7 | 71.6 |

#### 100 cells · `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | **Total ms** | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 53.8 <sub>(53.7–54.0)</sub> | 9.4 | 1.74 <sub>(1.70–1.77)</sub> | - | **1.74** | 18.0 | 10.2 | 1.5 |
| BUI-GPU | 57.2 <sub>(57.1–57.3)</sub> | 3.1 | 0.54 <sub>(0.54–0.55)</sub> | 7.17 <sub>(7.17–7.18)</sub> | **7.71** | 83.5 | 22.1 | 1.4 |
| gpui | 60.0 <sub>(60.0–60.0)</sub> | 6.9 | 1.14 <sub>(1.14–1.23)</sub> | 1.78 <sub>(1.77–1.79)</sub> | **2.92** | 88.1 | 25.6 | 54.2 |

#### 100 cells · `idle`

| Framework | Frames/s | CPU % | CPU ms/s | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 0.0 | 0.10 | 0.00 | 17.2 | 9.0 | 1.4 |
| BUI-GPU | 0.0 | 0.10 | 0.00 | 82.7 | 21.0 | 2.5 |
| gpui | 0.0 | 0.20 | 0.00 | 88.1 | 25.6 | 58.3 |

#### 1000 cells · `anim`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | **Total ms** | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 41.0 <sub>(40.0–41.9)</sub> | 29.4 | 7.16 <sub>(6.50–7.74)</sub> | - | **7.16** | 24.2 | 16.0 | 1.6 |
| BUI-GPU | 50.5 <sub>(48.8–50.6)</sub> | 14.4 | 2.85 <sub>(2.78–3.68)</sub> | 21.12 <sub>(21.02–21.22)</sub> | **23.97** | 90.4 | 28.6 | 1.5 |
| gpui | 58.8 <sub>(53.6–59.9)</sub> | 65.7 | 11.17 <sub>(10.26–13.27)</sub> | 2.03 <sub>(2.03–2.04)</sub> | **13.20** | 102.4 | 39.7 | 54.3 |

#### 1000 cells · `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | **Total ms** | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 42.6 <sub>(41.7–44.3)</sub> | 28.7 | 6.72 <sub>(5.73–7.17)</sub> | - | **6.72** | 24.1 | 15.9 | 1.5 |
| BUI-GPU | 50.1 <sub>(49.5–50.9)</sub> | 15.8 | 3.16 <sub>(2.67–3.35)</sub> | 21.06 <sub>(20.95–21.35)</sub> | **24.22** | 90.3 | 28.6 | 1.4 |
| gpui | 59.3 <sub>(52.0–59.8)</sub> | 71.3 | 12.25 <sub>(10.36–13.65)</sub> | 2.03 <sub>(2.00–2.07)</sub> | **14.28** | 102.2 | 39.8 | 57.3 |

#### 1000 cells · `idle`

| Framework | Frames/s | CPU % | CPU ms/s | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 0.0 | 0.10 | 0.00 | 22.7 | 14.6 | 1.5 |
| BUI-GPU | 0.0 | 0.10 | 0.00 | 88.6 | 26.9 | 1.5 |
| gpui | 0.0 | 0.20 | 0.00 | 102.3 | 39.9 | 54.2 |

#### 3000 cells · `anim`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | **Total ms** | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 30.9 <sub>(28.7–33.1)</sub> | 46.7 | 15.13 <sub>(12.71–17.53)</sub> | - | **15.13** | 32.9 | 24.6 | 1.5 |
| BUI-GPU | 38.0 <sub>(34.9–39.4)</sub> | 35.9 | 9.44 <sub>(8.39–11.73)</sub> | 29.17 <sub>(28.62–29.59)</sub> | **38.61** | 100.8 | 38.8 | 1.5 |
| gpui | 20.0 <sub>(17.9–26.8)</sub> | 79.5 | 37.57 <sub>(32.73–45.90)</sub> | 2.62 <sub>(2.56–2.67)</sub> | **40.19** | 133.9 | 71.4 | 56.4 |

#### 3000 cells · `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | **Total ms** | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 32.8 <sub>(31.2–34.5)</sub> | 44.6 | 13.62 <sub>(12.07–15.27)</sub> | - | **13.62** | 33.5 | 25.3 | 1.5 |
| BUI-GPU | 38.5 <sub>(36.9–40.1)</sub> | 35.0 | 9.09 <sub>(8.02–10.21)</sub> | 29.14 <sub>(28.83–29.41)</sub> | **38.23** | 100.7 | 38.8 | 2.2 |
| gpui | 20.1 <sub>(18.7–21.4)</sub> | 73.9 | 35.91 <sub>(34.11–43.03)</sub> | 2.64 <sub>(2.59–2.64)</sub> | **38.55** | 133.9 | 71.4 | 57.3 |

#### 3000 cells · `idle`

| Framework | Frames/s | CPU % | CPU ms/s | RSS MB | Private MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 0.0 | 0.10 | 0.00 | 32.3 | 24.2 | 1.6 |
| BUI-GPU | 0.0 | 0.10 | 0.00 | 100.1 | 38.3 | 1.6 |
| gpui | 0.0 | 0.20 | 0.00 | 133.5 | 71.2 | 54.3 |

#### Uncapped (vsync off)

| Framework | Cells | FPS | CPU ms/frame | GPU ms/frame | Total ms |
|---|---:|---:|---:|---:|---:|
| BUI-CPU | 100 | 50.9 <sub>(30.4–51.0)</sub> | 2.22 <sub>(2.19–5.89)</sub> | - | 2.22 |
| BUI-GPU | 100 | 57.1 <sub>(55.3–57.2)</sub> | 0.57 <sub>(0.57–0.78)</sub> | 7.22 <sub>(7.20–7.30)</sub> | 7.79 |
| gpui | 100 | 60.0 <sub>(60.0–60.0)</sub> | 1.78 <sub>(1.75–1.82)</sub> | 1.78 <sub>(1.77–1.78)</sub> | 3.56 |
| BUI-CPU | 1000 | 40.3 <sub>(39.7–41.7)</sub> | 7.63 <sub>(6.69–7.98)</sub> | - | 7.63 |
| BUI-GPU | 1000 | 50.5 <sub>(49.9–50.6)</sub> | 2.84 <sub>(2.80–3.22)</sub> | 21.08 <sub>(20.99–21.15)</sub> | 23.92 |
| gpui | 1000 | 59.7 <sub>(58.5–59.8)</sub> | 11.09 <sub>(10.19–11.55)</sub> | 2.04 <sub>(2.02–2.05)</sub> | 13.13 |
| BUI-CPU | 3000 | 33.2 <sub>(31.1–33.6)</sub> | 12.67 <sub>(12.26–14.93)</sub> | - | 12.67 |
| BUI-GPU | 3000 | 39.5 <sub>(38.1–39.7)</sub> | 8.34 <sub>(8.15–9.36)</sub> | 28.89 <sub>(28.55–29.05)</sub> | 37.23 |
| gpui | 3000 | 25.2 <sub>(19.6–28.0)</sub> | 33.75 <sub>(32.55–40.03)</sub> | 2.62 <sub>(2.59–2.65)</sub> | 36.37 |

#### Total cost matrix (CPU + GPU ms per frame)

| Cells | BUI-CPU | BUI-GPU | gpui | gpui ÷ BUI-GPU | gpui ÷ BUI-CPU |
|---:|---:|---:|---:|---:|---:|
| 100 | 2.73 | 10.48 | 4.12 | 0.39x | 1.51x |
| 1000 | 7.16 | 23.97 | 13.20 | 0.55x | 1.84x |
| 3000 | 15.13 | 38.61 | 40.19 | 1.04x | 2.66x |

#### Scaling from 100 to 3000 cells (30x the cells)

| Framework | CPU ms/frame | | GPU ms/frame | | Total ms/frame | | FPS | |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BUI-CPU | 2.73 → 15.13 | 5.5x | - → - | - | 2.73 → 15.13 | 5.5x | 50 → 31 | 0.62x |
| BUI-GPU | 0.64 → 9.44 | 14.8x | 9.84 → 29.17 | 3.0x | 10.48 → 38.61 | 3.7x | 57 → 38 | 0.66x |
| gpui | 2.16 → 37.57 | 17.4x | 1.96 → 2.62 | 1.3x | 4.12 → 40.19 | 9.8x | 60 → 20 | 0.33x |

#### Resident memory against scene size

| Framework | 100 cells | 1000 cells | 3000 cells | Growth |
|---|---:|---:|---:|---:|
| BUI-CPU | 19.2 MB | 24.2 MB | 32.9 MB | +13.7 MB |
| BUI-GPU | 84.6 MB | 90.4 MB | 100.8 MB | +16.2 MB |
| gpui | 88.1 MB | 102.4 MB | 133.9 MB | +45.8 MB |

#### Example 2 · static settings form

| App | Renderer | First frame ms | RSS MB | Private MB | Idle CPU % |
|---|---|---:|---:|---:|---:|
| bui form (divs) | cpu | 1.5 <sub>(1.4–2.1)</sub> | 10.1 <sub>(10.0–10.4)</sub> | 2.1 | 0.10 |
| bui form (divs) + GPU | gpu | 1.6 <sub>(1.5–2.3)</sub> | 81.5 <sub>(81.2–81.6)</sub> | 19.8 | 0.10 |
| bui form (Blender widgets) | cpu | 1.6 <sub>(1.5–2.2)</sub> | 10.2 <sub>(10.2–10.6)</sub> | 2.1 | 0.10 |
| gpui form (divs) | gpu | 58.9 <sub>(53.0–73.5)</sub> | 87.1 <sub>(86.9–87.3)</sub> | 24.6 | 0.20 |

#### Derived ratios (1000 cells, animating)

- gpui CPU per frame ÷ BUI-GPU CPU per frame: **3.92x**
- BUI-GPU GPU per frame ÷ gpui GPU per frame: **10.40x**
- gpui total ÷ BUI-GPU total: **0.55x**
- gpui total ÷ BUI-CPU total: **1.84x**
- gpui RSS ÷ BUI-CPU RSS: **4.23x** (BUI smaller)
- gpui first frame ÷ BUI-CPU first frame: **34x**

### 3.2 What the numbers mean

**Total cost per frame (CPU + GPU), animating every cell:**

| Cells | BUI-CPU | BUI-GPU | gpui | Winner |
|---:|---:|---:|---:|---|
| 100 | **2.73 ms** | 10.48 ms | 4.12 ms | BUI-CPU |
| 1000 | **7.16 ms** | 23.97 ms | 13.20 ms | BUI-CPU |
| 3000 | **15.13 ms** | 38.61 ms | 40.19 ms | BUI-CPU |

BUI's **software raster** is the cheapest in total at every size — by 1.5x
against gpui at 100 cells, 1.8x at 1000, and 2.7x at 3000. It achieves that by
never touching the GPU at all.

BUI's **GPU renderer** is the opposite trade: it wins CPU decisively
(3.9x less than gpui at 1000 cells) but spends **10.4x more GPU time**
(21.12 ms against 2.03 ms). In total it is *more* expensive than gpui at 100 and
1000 cells, and only reaches parity at 3000 (38.61 against 40.19 ms). It moves
the work rather than removing it.

**gpui** sits in between, and is the most *balanced*: it keeps the GPU nearly
idle (2.0–2.7 ms) and puts the load on the CPU (2.16 → 37.57 ms as the scene
grows). That balance is why it holds 60 fps longest.

### 3.3 Where each framework wins

| Dimension | Winner | Margin (1000 cells unless stated) |
|---|---|---|
| Total cost per frame | **BUI-CPU** | 1.8x cheaper than gpui, 3.3x cheaper than BUI-GPU |
| CPU per frame | **BUI-GPU** | 3.9x less than gpui |
| GPU per frame | **gpui** | 10.4x less than BUI-GPU |
| Frame rate at 100–1000 cells | **gpui** | 58.8–60.0 fps vs 41–50 |
| Frame rate at 3000 cells | **BUI-GPU** | 38.0 fps vs gpui's 20.0 |
| Resident memory | **BUI-CPU** | 24.2 MB vs 102.4 MB — **4.2x smaller** |
| Time to first frame | **BUI** | 1.5 ms vs 54–72 ms — **~38x faster** |
| Idle CPU | **BUI** | 0.10 % vs 0.30 % of a core |
| Widgets out of the box | **BUI** | Blender's full set vs primitives |

### 3.4 Scaling behaviour

As the scene grows 30x (100 → 3000 cells), the three designs diverge sharply:

| Framework | CPU growth | GPU growth | Total growth | FPS change |
|---|---|---|---|---|
| BUI-CPU | 5.5x | — | 5.5x | 50 → 31 fps (0.62x) |
| BUI-GPU | 14.8x | 3.4x | 3.7x | 57 → 38 fps (0.66x) |
| gpui | 17.4x | 1.4x | **9.8x** | 60 → 20 fps (**0.33x**) |

gpui's cost grows fastest because its CPU side — the cascade, layout and paint
list — is where all the per-cell work happens, and its GPU barely notices. BUI's
GPU renderer grows slowest in total, because the GPU absorbs the extra geometry.
BUI's CPU raster grows steadily and predictably, single-threaded.

**Frame rate is a bad metric here.** At 100 and 1000 cells all three are within
10 % of each other on screen, because the display caps them near 60 Hz — yet
their machine cost differs by up to 3.7x. This is exactly why the harness reports
ms per frame and not just fps.

### 3.5 Memory

| Framework | 100 cells | 1000 cells | 3000 cells | Growth |
|---|---:|---:|---:|---:|
| BUI-CPU | 19.2 MB | 24.2 MB | 33.1 MB | +13.9 MB |
| BUI-GPU | 84.6 MB | 90.4 MB | 100.9 MB | +16.3 MB |
| gpui | 88.1 MB | 102.4 MB | 133.7 MB | **+45.6 MB** |

BUI's CPU raster holds a **4.2x smaller footprint** at 1000 cells. Its growth
with scene size is also the smallest, because it keeps only a framebuffer and
the widget tree, not a GPU device, atlas and shader set.

gpui's footprint grows fastest (+45.3 MB), which is what you would expect from a
retained scene graph plus a GPU renderer's atlases scaling with content.

Note that BUI's **GPU** renderer gives up most of that memory advantage: 84–102 MB,
essentially the same as gpui. The ~65 MB difference between BUI's two renderers
is the OpenGL device, glyph atlas and textures.

### 3.6 Start-up

| Framework | First frame (median) | Range across the sweep |
|---|---:|---|
| BUI-CPU | **1.5 ms** | 1.5–2.5 ms |
| BUI-GPU | 1.5 ms | 1.4–2.2 ms |
| gpui | 56.8 ms | 54.2–71.6 ms |

That is **~38x faster** by median (1.5 ms against 56.8 ms); comparing the
slowest run of each, 28x. The gap is structural: gpui
initialises a Vulkan device, uploads shaders and builds a cosmic-text font
system before it can draw; BUI's software raster has nothing to initialise, and
its font is embedded in the binary.

For a CLI-launched tool this is the difference between "instant" and "a noticeable
pause".

### 3.7 Idle

| Framework | Frames/s when idle | CPU % |
|---|---:|---:|
| BUI-CPU | 0.0 | 0.10 |
| BUI-GPU | 0.0 | 0.10 |
| gpui | 0.0 | 0.30 |

All three go fully quiet — **0 frames rendered per second** once settled. This
is the single most important behaviour for a desktop app on battery, and all
three get it right. gpui's 0.30 % residual is its render loop waking
occasionally; BUI's 0.10 % is in the noise of `/proc` accounting.

### 3.8 Uncapped (the real ceiling)

With vsync off, the frame rate shows what the design can actually do:

| Framework | 100 cells | 1000 cells | 3000 cells |
|---|---:|---:|---:|
| BUI-CPU | 49.7 fps | 41.6 fps | 33.5 fps |
| BUI-GPU | 57.2 fps | 50.6 fps | 39.7 fps |
| gpui | 60.0 fps | 59.9 fps | 28.1 fps |

(These are from the paced/uncapped sweep; the totals tables above are the
authoritative ms-per-frame figures.)

Two things to read here. First, BUI's **CPU raster barely moves** when uncapped
(49.7 vs 49.7) — it is already CPU-bound, not vsync-bound. Second, gpui at 1000
cells is also still at 60 uncapped, meaning its frame pacing is not the limit
either; it is genuinely fast enough. The limit only appears at 3000 cells.

### 3.9 Example 2 — the static form

| App | Renderer | First frame | RSS | Private | Idle CPU |
|---|---|---:|---:|---:|---:|
| BUI form (divs) | CPU | **1.5 ms** | **10.1 MB** | **2.1 MB** | 0.10 % |
| BUI form (divs) + GPU | GPU | 1.6 ms | 81.5 MB | 19.8 MB | 0.10 % |
| BUI form (Blender widgets) | CPU | 1.6 ms | 10.2 MB | 2.1 MB | 0.10 % |
| gpui form (divs) | GPU | 58.9 ms | 87.1 MB | 24.6 MB | 0.30 % |

This is the clearest result in the whole comparison. For a small tool window:

- **BUI's CPU raster: 10 MB and 1.5 ms.**
- **gpui: 87 MB and 59 ms.**

That is **8.6x less memory and ~39x faster start-up for identical pixels**. The
cost of BUI's Blender widgets over plain divs is negligible (10.1 → 10.2 MB,
1.5 → 1.6 ms).

It also shows the price of BUI's own GPU renderer: turning it on costs 71 MB of
RAM for a static form that gains nothing from it. **The CPU raster is the right
default for tool windows** — which is why it is BUI's default.

---

## 4. Why the differences exist

### 4.1 BUI's software raster is single-threaded on Linux

`kit/intern/kit_frame.c` draws large display lists in horizontal bands on a
thread pool — but the default thread count is set from `GetSystemInfo` inside
`#ifdef _WIN32`:

```c
static int par_threads(void)
{
  static int n = -1;
  if (n < 0) {
    const char *env = getenv("BUI_RASTER_THREADS");
    n = env ? atoi(env) : 0;
#ifdef _WIN32
    if (n <= 0) {
      SYSTEM_INFO si;
      GetSystemInfo(&si);
      n = (int)si.dwNumberOfProcessors;   /* never runs on Linux */
    }
#endif
    n = BK_CLAMP(n, 1, 8);
  }
  return n;
}
```

On Linux the count therefore stays at 1 unless `BUI_RASTER_THREADS` is set
explicitly. Setting `BUI_RASTER_THREADS=8` was tried during this work and gave
no improvement at 3000 cells (9.2 fps against 8.5 fps unset, with slightly higher
CPU) — so the raster is not purely thread-limited; the cascade, layout and
display-list build are serial too. That test ran under the same noisy desktop
conditions as everything else, so treat it as a strong hint rather than a
precise result.

**Consequence for reading BUI's own benchmarks:** its README reports "2–4x less
CPU per frame than gpui-fast" from a Windows machine, where the parallel raster
does engage. Those numbers are not what a Linux CPU-raster run shows.

### 4.2 gpui's fixed costs are the GPU device and the text stack

53–76 ms to first frame and 88–133 MB are the price of:

- a Vulkan instance, physical device, logical device, swapchain;
- shader compilation and pipeline creation;
- a glyph atlas built from cosmic-text.

None of that is waste — it is what makes gpui's GPU side nearly free (2 ms per
frame) and its frame rate so stable. But it is paid on every launch.

### 4.3 Why BUI-GPU uses 10x more GPU time

BUI's GPU renderer evaluates the same formulas as its software raster (the
project's own tests find only 10 of 172,800 pixels differing between the two).
That means each primitive is drawn with anti-aliased signed-distance coverage in
a fragment shader, rather than with cheap opaque triangles.

gpui, by contrast, batches glyphs and rectangles from an atlas with far less
per-pixel work. BUI trades GPU time for CPU time and pixel-exact fidelity to
Blender's software look; gpui trades the opposite way.

That is a design choice, not a defect — but it means **"BUI-GPU uses less CPU"
must always be read together with "BUI-GPU uses much more GPU"**.

### 4.4 Text handling

BUI embeds Inter and renders with FreeType configured like Blender's BLF (light
hinting, Blender's gamma-1.43 coverage table, no kerning). gpui uses cosmic-text,
which does full shaping. On the grid scene, every cell draws a number, so text
rasterization is a significant share of both CPU columns — and the two stacks
are being compared as much as the layout engines are. This is noted, not judged.

---

## 5. Threats to validity

Being explicit about what could make these numbers wrong.

| Risk | Status | Mitigation in this repo |
|---|---|---|
| **Desktop load** — the user's IDE and browser ran throughout | Real; load average 1–3 during the published run | 5 repetitions, interleaved, min–max spread reported |
| **Third-party builds** — an unrelated compile can take all 8 threads | **Caught once, during a discarded run**: BUI-CPU read 21.91 ms/frame instead of 7.16, a 3x inflation, with load average 7.0 | The harness now records `load1` with every row; a contaminated `results.json` is detectable after the fact. Always check `uptime` before starting a sweep. |
| **`powersave` governor** — clocks move under load | Real | Same as above; plug in and re-run for tighter absolutes |
| **Wayland occlusion** — compositor withholds frame callbacks from covered windows | **Was a real bug here**; gpui rendered 0 fps for whole windows | Both frameworks pinned to X11; runs under 0.5 fps retried, then dropped |
| **GPU counter attribution** — GLX submits via the X server | Verified | Hand-sampled the counter; 55–60 % observed matches 55 fps × 10.7 ms = 59 % |
| **Different graphics APIs** — OpenGL 3.3 vs Vulkan | Inherent | Both drive the same iGPU; noted in every table |
| **FPS saturation at 60 Hz** | Inherent | ms-per-frame is the headline, not fps |
| **Benchmark overhead in the frame loop** | Eliminated | Grid computed once in `Scene::new`; a frame is one atomic increment |
| **Different compiler settings** | Eliminated | One `[profile.release]` for both: opt-level 3, thin LTO, 1 CGU, stripped |
| **Different scene** | Eliminated | One source file compiled twice |
| **Different window size** | Eliminated | BUI's `<body>` margin zeroed so its flex container fills the window like gpui's root `div` |
| **Benchmark measuring itself** | Eliminated | Measurement runs on a background thread; the app calls one atomic per frame |

---

## 6. Reproducing it

```sh
git clone <this repo> && cd Gui
cargo build --release          # ~5 min from cold, both frameworks
python3 bench/verify.py        # ~1 min: sanity-check the harness
python3 bench/run.py           # full sweep, ~47 min, writes RESULTS.md
```

Requirements: Rust 1.99+, CMake 3.20+, a C compiler, X11 headers, and on glibc
Linux the `xattr` patch already wired up in the workspace.

Single experiments, each printing one JSON line:

```sh
./target/release/grid-scene-bui  --cells 1000 --mode anim            # CPU raster
./target/release/grid-scene-bui  --cells 1000 --mode anim --gpu      # GPU renderer
./target/release/grid-scene-gpui --cells 1000 --mode anim
./target/release/settings-form-gpui --seconds 10
```

`--mode` is `anim`, `one` or `idle`; `--cells` any count; `--uncapped` disables
BUI's vsync pacing; `--warmup`/`--seconds` control the measurement window.

---

## 7. Verdict

**There is no single faster framework. There are three designs that win on
different resources.**

| If you are… | Choose | Because |
|---|---|---|
| Building a **tool window, settings panel or dialog** | **BUI, CPU raster** | 10 MB and 1.5 ms against 87 MB and 59 ms, same pixels |
| Targeting **low-end or battery-powered machines** | **BUI, CPU raster** | no GPU device at all; 4.2x smaller footprint; 0 % idle |
| Building a **large, continuously animated surface** and the GPU is free | **gpui** | holds 60 fps to 1000 cells; only 2 ms GPU per frame |
| Building for **Windows** and want BUI's parallel raster | **BUI** | the band renderer engages there; Linux numbers understate it |
| Needing **Blender's widgets** (number fields, pie menus, colour picker, node editor) | **BUI** | gpui has primitives only; you would build all of it yourself |
| Needing the **most mature Rust-native** ecosystem and Zed parity | **gpui** | production-tested in Zed, Apache-2.0 |

Three findings worth carrying away:

1. **BUI's GPU renderer is not "BUI, but faster".** It cuts CPU by 3.9x and
   raises GPU by 10.4x; in total it is usually *more* expensive than gpui. Its
   value is freeing the CPU, not saving the machine.
2. **Frame rate hides everything.** At 1000 cells all three look close on screen
   (41–59 fps) while costing 7.2–24.0 ms of machine per frame.
3. **Fixed costs dominate small UIs.** For a 360×260 window, the entire
   difference between the frameworks is start-up and memory: 1.5 ms and 10 MB
   against 59 ms and 87 MB. Throughput never enters into it.

---

## 8. Project layout

```
bench-common/            scene parameters + the measurement (no framework code)
bench/run.py             drives every binary, writes results.json and RESULTS.md
bench/verify.py          sanity checks: is each column measuring what it claims?
bench/shots.py           screenshots of each example (docs/shots/)
bench/machine.sh         CPU, GPU, display and toolchain of this machine
bench/README.md          how the harness works and why it is built this way
examples/01-grid-scene/
  scene.rs               THE shared scene — compiled by both crates
  bui/                   blenderui crate: Render impl + window, CPU or GPU renderer
  gpui/                  gpui crate: the same Render impl + window
examples/02-settings-form/
  form.rs                THE shared form — compiled by all three crates
  bui/                   the form from divs (what gpui can also draw)
  bui-native/            the form from Blender's real widgets
  gpui/                  the form from divs
third_party/xattr/       gpui's xattr 0.2.3 with one libc constant fixed for Linux
docs/shots/              the screenshots in this document
RESULTS.md               generated tables from the last sweep
bench/results.json       the raw data, with settings and binary checksums
```

## 9. Known issues encountered

Documented because anyone reproducing this will hit them.

**gpui does not build on current glibc Linux out of the box.** Its dependency
`xattr 0.2.3` names `libc::ENOATTR`, which newer libc releases no longer define
for glibc — the spelling there is `ENODATA`. `third_party/xattr` is that crate
with the single constant mapped correctly, wired in with `[patch.crates-io]`.
Nothing about gpui's rendering or layout is touched.

**gpui links `libxkbcommon.so` / `libxkbcommon-x11.so`,** which some distros
only ship as `.so.0`. `.cargo/config.toml` adds `third_party/stubs`, and
`sh third_party/stubs/make-stubs.sh` fills it with symlinks to the system
libraries. If your distro ships the `-dev` packages, delete the `rustflags` entry
and the stub directory.

**BUI's `request_animation_frame` takes `&mut self`,** gpui's takes `&self`. The
shared form file bridges that with a one-method trait, which is also a neat
summary of how thin the shared layer is.

**A Wayland compositor stops sending frame callbacks to an occluded window,**
so a benchmark window behind your terminal measures nothing. The harness pins
both frameworks to X11 (`BENCH_WAYLAND=1` opts out) and rejects stalled runs.
