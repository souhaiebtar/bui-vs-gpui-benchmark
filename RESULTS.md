# BUI (blenderui 0.5.0) vs gpui 0.2.2 - measured on this machine

Generated 2026-11-12 11:07 by `bench/run.py`.

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
| bui (CPU raster) | 49.7 (49.5-51.0) | 13.8 | 2.78 (2.20-2.86) | - | 19.2 | 2 |
| bui (GPU renderer) | 57.1 (54.5-57.3) | 3.5 | 0.62 (0.58-0.64) | 8.18 (7.22-8.52) | 84.4 | 3 |
| gpui (GPU, Vulkan) | 59.9 (59.9-60.0) | 12.4 | 2.06 (1.79-2.16) | 2.00 (1.78-2.07) | 88.1 | 72 |

### 100 cells, `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 53.0 (52.9-53.1) | 11.0 | 2.08 (2.07-2.12) | - | 18.1 | 2 |
| bui (GPU renderer) | 57.3 (57.3-57.3) | 3.5 | 0.61 (0.61-0.61) | 8.37 (8.08-8.86) | 83.6 | 3 |
| gpui (GPU, Vulkan) | 60.0 (59.9-60.0) | 8.2 | 1.36 (1.27-1.58) | 2.00 (1.86-2.28) | 88.0 | 76 |

### 100 cells, `idle`

| Framework | Frames rendered | CPU % | CPU ms/s | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|
| bui (CPU raster) | 0.0/s | 0.10 | 0.00 | 17.1 | 2 |
| bui (GPU renderer) | 0.0/s | 0.10 | 0.00 | 82.7 | 2 |
| gpui (GPU, Vulkan) | 0.0/s | 0.30 | 0.00 | 88.0 | 56 |

### 1000 cells, `anim`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 42.0 (41.9-42.1) | 27.0 | 6.41 (6.39-6.48) | - | 24.2 | 2 |
| bui (GPU renderer) | 50.7 (50.5-50.7) | 14.3 | 2.82 (2.79-2.88) | 21.09 (21.03-21.38) | 90.4 | 2 |
| gpui (GPU, Vulkan) | 59.8 (59.8-59.9) | 61.2 | 10.22 (10.20-10.30) | 2.04 (2.03-2.05) | 102.5 | 53 |

### 1000 cells, `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 44.4 (44.4-44.4) | 25.2 | 5.68 (5.66-5.69) | - | 24.0 | 2 |
| bui (GPU renderer) | 51.0 (50.9-51.1) | 13.5 | 2.65 (2.63-2.66) | 21.04 (20.98-21.14) | 90.1 | 3 |
| gpui (GPU, Vulkan) | 59.8 (59.7-59.9) | 61.2 | 10.22 (10.16-10.29) | 2.03 (2.02-2.03) | 102.2 | 60 |

### 1000 cells, `idle`

| Framework | Frames rendered | CPU % | CPU ms/s | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|
| bui (CPU raster) | 0.0/s | 0.10 | 0.00 | 22.8 | 2 |
| bui (GPU renderer) | 0.0/s | 0.10 | 0.00 | 88.7 | 2 |
| gpui (GPU, Vulkan) | 0.0/s | 0.30 | 0.00 | 102.2 | 56 |

### 3000 cells, `anim`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 33.4 (33.2-33.5) | 41.7 | 12.49 (12.45-12.69) | - | 32.9 | 2 |
| bui (GPU renderer) | 39.7 (39.5-39.8) | 32.6 | 8.20 (8.19-8.33) | 29.01 (28.82-29.31) | 101.5 | 2 |
| gpui (GPU, Vulkan) | 27.9 (27.8-28.5) | 90.9 | 32.58 (32.39-32.68) | 2.65 (2.63-2.66) | 133.4 | 66 |

### 3000 cells, `one`

| Framework | FPS | CPU % | CPU ms/frame | GPU ms/frame | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|---:|
| bui (CPU raster) | 35.4 (35.3-35.5) | 40.2 | 11.35 (11.30-11.45) | - | 33.6 | 2 |
| bui (GPU renderer) | 40.5 (40.3-40.6) | 31.2 | 7.70 (7.64-7.85) | 28.43 (28.01-28.70) | 101.7 | 2 |
| gpui (GPU, Vulkan) | 26.0 (25.1-27.5) | 85.9 | 33.08 (32.84-33.57) | 2.66 (2.62-2.68) | 133.9 | 57 |

### 3000 cells, `idle`

| Framework | Frames rendered | CPU % | CPU ms/s | RSS MB | First frame ms |
|---|---:|---:|---:|---:|---:|
| bui (CPU raster) | 0.0/s | 0.10 | 0.00 | 32.3 | 2 |
| bui (GPU renderer) | 0.0/s | 0.10 | 0.00 | 99.6 | 2 |
| gpui (GPU, Vulkan) | 0.0/s | 0.30 | 0.00 | 133.8 | 57 |

### Uncapped (vsync off): the real per-frame ceiling

| Framework | Cells | FPS | CPU ms/frame | GPU ms/frame |
|---|---:|---:|---:|---:|
| bui (CPU raster) | 100 | 49.7 (49.6-49.8) | 2.82 (2.73-2.85) | - |
| bui (GPU renderer) | 100 | 57.2 (57.1-57.3) | 0.63 (0.62-0.64) | 8.37 (8.20-8.61) |
| gpui (GPU, Vulkan) | 100 | 60.0 (59.9-60.0) | 2.04 (1.93-2.21) | 2.06 (2.00-2.11) |
| bui (CPU raster) | 1000 | 41.6 (41.6-41.7) | 6.68 (6.64-6.77) | - |
| bui (GPU renderer) | 1000 | 50.6 (50.4-50.9) | 2.84 (2.77-2.86) | 21.08 (21.03-21.37) |
| gpui (GPU, Vulkan) | 1000 | 59.9 (59.6-59.9) | 10.24 (10.17-10.35) | 2.04 (2.03-2.04) |
| bui (CPU raster) | 3000 | 33.5 (33.4-33.6) | 12.38 (12.29-12.47) | - |
| bui (GPU renderer) | 3000 | 39.7 (39.7-39.8) | 8.18 (8.12-8.21) | 29.03 (28.68-29.57) |
| gpui (GPU, Vulkan) | 3000 | 28.1 (27.8-28.4) | 32.56 (32.45-32.58) | 2.63 (2.60-2.64) |

## Example 2 - static settings form (startup, memory, idle)

A 360x260 tool window that renders twice and then stops. This is where a UI toolkit's fixed costs live: time to first frame, resident memory, and what an untouched window costs per second.

| App | Renderer | First frame ms | RSS MB | Private MB | Idle CPU % |
|---|---|---:|---:|---:|---:|
| bui form (divs) | cpu | 2 | 10.1 | 2.1 | 0.10 |
| bui form (divs) + GPU | gpu | 3 | 81.5 | 19.8 | 0.10 |
| bui form (Blender widgets) | cpu | 3 | 10.4 | 2.1 | 0.10 |
| gpui form (divs) | gpu | 73 | 87.0 | 24.5 | 0.30 |

## Verdict

Cost of one frame, CPU and GPU added together (median of the repetitions). A framework that looks cheap on one half of the machine is usually expensive on the other.

| Cells | bui (CPU raster) | bui (GPU renderer) | gpui | gpui / bui-gpu |
|---:|---:|---:|---:|---:|
| 100 | 2.78 ms | 8.80 ms | 4.06 ms | 0.5x |
| 1000 | 6.41 ms | 23.91 ms | 12.27 ms | 0.5x |
| 3000 | 12.49 ms | 37.21 ms | 35.23 ms | 0.9x |

`gpui / bui-gpu` below 1 means gpui is cheaper in total; above 1 means BUI's GPU renderer is.

- **100 cells, all animating** — CPU/frame: gpui 2.06 ms, bui-gpu 0.62 ms, bui-cpu 2.78 ms. GPU/frame: gpui 2.00 ms, bui-gpu 8.18 ms. FPS: gpui 60, bui-gpu 57, bui-cpu 50.
- **1000 cells, all animating** — CPU/frame: gpui 10.22 ms, bui-gpu 2.82 ms, bui-cpu 6.41 ms. GPU/frame: gpui 2.04 ms, bui-gpu 21.09 ms. FPS: gpui 60, bui-gpu 51, bui-cpu 42.
- **3000 cells, all animating** — CPU/frame: gpui 32.58 ms, bui-gpu 8.20 ms, bui-cpu 12.49 ms. GPU/frame: gpui 2.65 ms, bui-gpu 29.01 ms. FPS: gpui 28, bui-gpu 40, bui-cpu 33.
- **Only one cell changing** (`one`, the common case): the cheapest configuration is bui (CPU raster) at 2.08 ms per frame (100 cells).
- **Idle**: every framework renders 0 frames/s once settled. The costliest still wakes enough to reach 0.30 % of a core (gpui (GPU, Vulkan)).
- **Startup and memory**: median first frame 2 ms for bui-gpu against 57 ms for gpui; median RSS 90 MB against 102 MB. On BUI's CPU raster, ~20 MB and a few ms (see Example 2).
- **Tool window (example 2)**: bui form (divs): 2 ms first frame, 10.1 MB RSS; bui form (divs) + GPU: 3 ms first frame, 81.5 MB RSS; bui form (Blender widgets): 3 ms first frame, 10.4 MB RSS; gpui form (divs): 73 ms first frame, 87.0 MB RSS.

## How to reproduce

```sh
cargo build --release        # both frameworks, both examples
python3 bench/run.py         # the sweep in this file
python3 bench/run.py --only 1 --reps 1 --seconds 5   # quick look
```

These numbers: 5 repetitions per configuration, warm-up 3.0 s, measured window 10.0 s per run, configurations interleaved within each repetition, medians reported with their min-max range.

The binaries measured, so a re-run can be compared exactly:

```
ed0aa489efef36d8f425302d0275c732  grid-scene-bui
1843f03c8abc8bca5e3e7824bdb4982a  grid-scene-gpui
e837da9bed384e1fa92f07ac4f05aee8  settings-form-bui
cc607e056b380951ecfb10f697a8e963  settings-form-bui-native
de64ed3dde09b3d6bdbef51e13ff893f  settings-form-gpui
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
