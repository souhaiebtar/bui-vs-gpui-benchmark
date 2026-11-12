# BUI (blenderui 0.5.0) vs gpui 0.2.2 - measured on this machine

Generated 2026-11-12 18:41 by `bench/run.py`.

| | |
|---|---|
| CPU | 11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz, 8 threads |
| RAM | 15.0 GB |
| GPU | Intel Corporation TigerLake-LP GT2 [Iris Xe Graphics] [8086:9a49] (rev 01) |
| OS | Linux 7.3.3-cachyos-x64v4 |
| CPU governor | powersave |

Both frameworks were measured by the same code (`bench-common`), compiled with the same release profile (opt-level 3, thin LTO, 1 codegen unit, symbols stripped), in the same session, back to back.

## Example 1 - grid scene (layout + paint + text, N cells)

One source file (`examples/01-grid-scene/scene.rs`) compiled against both frameworks. Every cell is a rounded box with a centred number; `anim` changes all of them each frame, `one` changes only cell 0, `idle` renders once. **CPU ms/frame** is the headline: it does not saturate at the display's refresh rate. **GPU ms/frame** is the kernel's GPU engine time for that process, so read the two together.

### 100 cells, `anim`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 49.8 (33.9-49.9) | 13.6 | 2.73 (2.66-5.26) | - | 19.2 | 2 |
| bui (GPU renderer) | 57.3 (51.0-57.3) | 3.7 | 0.64 (0.63-1.18) | 9.84 (7.69-10.71) | 84.6 | 2 |
| gpui (GPU, Vulkan) | 60.0 (58.8-60.0) | 13.0 | 2.16 (1.95-4.90) | 1.96 (1.86-2.73) | 88.1 | 72 |

### 100 cells, `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 53.8 (53.7-54.0) | 9.4 | 1.74 (1.70-1.77) | - | 18.0 | 2 |
| bui (GPU renderer) | 57.2 (57.1-57.3) | 3.1 | 0.54 (0.54-0.55) | 7.17 (7.17-7.18) | 83.5 | 1 |
| gpui (GPU, Vulkan) | 60.0 (60.0-60.0) | 6.9 | 1.14 (1.14-1.23) | 1.78 (1.77-1.79) | 88.1 | 54 |

### 100 cells, `idle`

| Framework | Frames rendered | CPU % | CPU ms/s | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|
| bui (CPU raster) | 0.0/s | 0.10 | 0.00 | 17.2 | 1 |
| bui (GPU renderer) | 0.0/s | 0.10 | 0.00 | 82.7 | 2 |
| gpui (GPU, Vulkan) | 0.0/s | 0.20 | 0.00 | 88.1 | 58 |

### 1000 cells, `anim`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 41.0 (40.0-41.9) | 29.4 | 7.16 (6.50-7.74) | - | 24.2 | 2 |
| bui (GPU renderer) | 50.5 (48.8-50.6) | 14.4 | 2.85 (2.78-3.68) | 21.12 (21.02-21.22) | 90.4 | 2 |
| gpui (GPU, Vulkan) | 58.8 (53.6-59.9) | 65.7 | 11.17 (10.26-13.27) | 2.03 (2.03-2.04) | 102.4 | 54 |

### 1000 cells, `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 42.6 (41.7-44.3) | 28.7 | 6.72 (5.73-7.17) | - | 24.1 | 2 |
| bui (GPU renderer) | 50.1 (49.5-50.9) | 15.8 | 3.16 (2.67-3.35) | 21.06 (20.95-21.35) | 90.3 | 1 |
| gpui (GPU, Vulkan) | 59.3 (52.0-59.8) | 71.3 | 12.25 (10.36-13.65) | 2.03 (2.00-2.07) | 102.2 | 57 |

### 1000 cells, `idle`

| Framework | Frames rendered | CPU % | CPU ms/s | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|
| bui (CPU raster) | 0.0/s | 0.10 | 0.00 | 22.7 | 2 |
| bui (GPU renderer) | 0.0/s | 0.10 | 0.00 | 88.6 | 2 |
| gpui (GPU, Vulkan) | 0.0/s | 0.20 | 0.00 | 102.3 | 54 |

### 3000 cells, `anim`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 30.9 (28.7-33.1) | 46.7 | 15.13 (12.71-17.53) | - | 32.9 | 2 |
| bui (GPU renderer) | 38.0 (34.9-39.4) | 35.9 | 9.44 (8.39-11.73) | 29.17 (28.62-29.59) | 100.8 | 2 |
| gpui (GPU, Vulkan) | 20.0 (17.9-26.8) | 79.5 | 37.57 (32.73-45.90) | 2.62 (2.56-2.67) | 133.9 | 56 |

### 3000 cells, `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 32.8 (31.2-34.5) | 44.6 | 13.62 (12.07-15.27) | - | 33.5 | 2 |
| bui (GPU renderer) | 38.5 (36.9-40.1) | 35.0 | 9.09 (8.02-10.21) | 29.14 (28.83-29.41) | 100.7 | 2 |
| gpui (GPU, Vulkan) | 20.1 (18.7-21.4) | 73.9 | 35.91 (34.11-43.03) | 2.64 (2.59-2.64) | 133.9 | 57 |

### 3000 cells, `idle`

| Framework | Frames rendered | CPU % | CPU ms/s | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|
| bui (CPU raster) | 0.0/s | 0.10 | 0.00 | 32.3 | 2 |
| bui (GPU renderer) | 0.0/s | 0.10 | 0.00 | 100.1 | 2 |
| gpui (GPU, Vulkan) | 0.0/s | 0.20 | 0.00 | 133.5 | 54 |

### Uncapped (vsync off): the real per-frame ceiling

| Framework | Cells | FPS | CPU ms/frame | GPU ms/frame |
|---|---:|---:|---:|---:|
| bui (CPU raster) | 100 | 50.9 (30.4-51.0) | 2.22 (2.19-5.89) | - |
| bui (GPU renderer) | 100 | 57.1 (55.3-57.2) | 0.57 (0.57-0.78) | 7.22 (7.20-7.30) |
| gpui (GPU, Vulkan) | 100 | 60.0 (60.0-60.0) | 1.78 (1.75-1.82) | 1.78 (1.77-1.78) |
| bui (CPU raster) | 1000 | 40.3 (39.7-41.7) | 7.63 (6.69-7.98) | - |
| bui (GPU renderer) | 1000 | 50.5 (49.9-50.6) | 2.84 (2.80-3.22) | 21.08 (20.99-21.15) |
| gpui (GPU, Vulkan) | 1000 | 59.7 (58.5-59.8) | 11.09 (10.19-11.55) | 2.04 (2.02-2.05) |
| bui (CPU raster) | 3000 | 33.2 (31.1-33.6) | 12.67 (12.26-14.93) | - |
| bui (GPU renderer) | 3000 | 39.5 (38.1-39.7) | 8.34 (8.15-9.36) | 28.89 (28.55-29.05) |
| gpui (GPU, Vulkan) | 3000 | 25.2 (19.6-28.0) | 33.75 (32.55-40.03) | 2.62 (2.59-2.65) |

## Example 2 - static settings form (startup, memory, idle)

A 360x260 tool window that renders twice and then stops. This is where a UI toolkit's fixed costs live: time to first frame, resident memory, and what an untouched window costs per second.

| App | Renderer | First frame ms | RSS MB | Private MB | Idle CPU % |
|---|---|---:|---:|---:|---:|
| bui form (divs) | cpu | 2 | 10.1 | 2.1 | 0.10 |
| bui form (divs) + GPU | gpu | 2 | 81.5 | 19.8 | 0.10 |
| bui form (Blender widgets) | cpu | 2 | 10.2 | 2.1 | 0.10 |
| gpui form (divs) | gpu | 59 | 87.1 | 24.6 | 0.20 |

## Verdict

Cost of one frame, CPU and GPU added together (median of the repetitions). A framework that looks cheap on one half of the machine is usually expensive on the other.

| Cells | bui (CPU raster) | bui (GPU renderer) | gpui | gpui / bui-gpu |
|---:|---:|---:|---:|---:|
| 100 | 2.73 ms | 10.48 ms | 4.12 ms | 0.4x |
| 1000 | 7.16 ms | 23.97 ms | 13.20 ms | 0.6x |
| 3000 | 15.13 ms | 38.61 ms | 40.19 ms | 1.0x |

`gpui / bui-gpu` below 1 means gpui is cheaper in total; above 1 means BUI's GPU renderer is.

- **100 cells, all animating** — CPU/frame: gpui 2.16 ms, bui-gpu 0.64 ms, bui-cpu 2.73 ms. GPU/frame: gpui 1.96 ms, bui-gpu 9.84 ms. FPS: gpui 60, bui-gpu 57, bui-cpu 50.
- **1000 cells, all animating** — CPU/frame: gpui 11.17 ms, bui-gpu 2.85 ms, bui-cpu 7.16 ms. GPU/frame: gpui 2.03 ms, bui-gpu 21.12 ms. FPS: gpui 59, bui-gpu 50, bui-cpu 41.
- **3000 cells, all animating** — CPU/frame: gpui 37.57 ms, bui-gpu 9.44 ms, bui-cpu 15.13 ms. GPU/frame: gpui 2.62 ms, bui-gpu 29.17 ms. FPS: gpui 20, bui-gpu 38, bui-cpu 31.
- **Only one cell changing** (`one`, the common case): the cheapest configuration is bui (CPU raster) at 1.74 ms per frame (100 cells).
- **Idle**: every framework renders 0 frames/s once settled. The costliest still wakes enough to reach 0.20 % of a core (gpui (GPU, Vulkan)).
- **Startup and memory**: median first frame 2 ms for bui-gpu against 56 ms for gpui; median RSS 90 MB against 102 MB. On BUI's CPU raster, ~20 MB and a few ms (see Example 2).
- **Tool window (example 2)**: bui form (divs): 2 ms first frame, 10.1 MB RSS; bui form (divs) + GPU: 2 ms first frame, 81.5 MB RSS; bui form (Blender widgets): 2 ms first frame, 10.2 MB RSS; gpui form (divs): 59 ms first frame, 87.1 MB RSS.

## How to reproduce

```sh
cargo build --release        # both frameworks, both examples
python3 bench/run.py         # the sweep in this file
python3 bench/run.py --only 1 --reps 1 --seconds 5   # quick look
```

These numbers: 5 repetitions per configuration, warm-up 3.0 s, measured window 10.0 s per run, configurations interleaved within each repetition, medians reported with their min-max range.

The binaries measured, so a re-run can be compared exactly:

```
45525a6bbebb28d8b684a987eaa9f473  grid-scene-bui
a639a5e98ab754e6b37a088a9bee6bf8  grid-scene-gpui
901c11228ff4d2d67d38e058fd2fe198  settings-form-bui
9d836cbae5c41168a22adb2db21c759c  settings-form-bui-native
ca90972c855d7bc1df77ae8404a3f714  settings-form-gpui
```

BUI's binary is byte-reproducible in the same checkout. gpui's embeds build paths, so its checksum changes if the checkout moves; compare its numbers, not its hash.

## Caveats

- Both frameworks cap at the display's refresh rate, so **FPS saturates at ~60** in the paced rows; compare CPU ms/frame there, and the uncapped rows for the ceiling.
- gpui always renders on the GPU, BUI has a CPU and a GPU renderer. A low-CPU gpui row can still be GPU-bound: read the GPU column.
- BUI's GPU renderer is OpenGL 3.3 on Linux, gpui's is Vulkan through blade. Different APIs, same iGPU.
- **GPU time is engine nanoseconds from the kernel's per-process DRM counters**, not a vendor utilisation percentage (Intel iGPUs do not export one on Linux). It counts time the GPU actually executed work for that process. Cross-checked against a hand-sampled counter: at 300 cells BUI's GPU renderer runs 55 fps x 10.7 ms = 59 % GPU busy, which matches the independently observed 55-60 %. A blank GPU cell means the process had no DRM client of its own (GLX submits through the X server), not that it used no GPU.
- BUI's root is wrapped in `body().m_0()` so its flex container fills the window exactly like gpui's root `div`.
- Example 2's gpui column uses styled divs, because gpui has no form widgets; the `bui form (Blender widgets)` row shows what the real widgets cost.
- One machine, one session, medians over the given repetitions. Absolute numbers do not transfer; the ratios are the result.
