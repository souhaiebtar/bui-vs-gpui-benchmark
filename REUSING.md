# Reusing this project

This repository is built so its parts can be lifted out independently. Nothing
in it is a monolith: the measurement library, the two scenes, the harness and the
two rendering comparisons all stand alone.

Read this page by what you want to do.

---

## 1. "I want to benchmark *my* GUI framework against one of these"

You need three pieces: the measurement library, a scene, and a driver.

### Step 1 — take `bench-common`

Copy the directory, change the package name, keep the code:

```sh
cp -r bench-common my-bench-common
```

It has **no dependencies at all** — pure `std` plus two `extern "C"` libc calls.
That is deliberate: it must be linkable into any framework's binary without
dragging in a dependency tree.

The public surface:

```rust
use bench_common as bench;

// once, at the top of main()
let cfg = bench::Config::from_args();
let measured = bench::start("my-framework", &cfg);
measured.arm_watchdog(std::time::Duration::from_secs(60));

// once per rendered frame
bench::frame();

// the scene content, if you want the same cells as this repo
bench::cell_color(i, t);   // 0xRRGGBB
bench::cell_label(i, t);   // String
cfg.grid();                // (cols, w, h, font_size) for N cells in the window

// what it measures (useful for your own reporting)
bench::cpu_ns();
bench::memory();           // Mem { working_set, peak_working_set, private_bytes }
bench::gpu_ns();           // Option<u64>, Linux DRM engine nanoseconds
```

`bench::start` spawns a background thread that waits for the first frame, waits
for the frame rate to settle, measures for `--seconds`, prints one JSON line to
stdout and calls `exit(0)`. Your app never needs its own quit path.

The JSON line carries a `frames_measured` count alongside every metric. Use it,
not `first_frame_ms`, to decide whether a run produced anything: a fast app can
legitimately reach its first frame in under 0.1 ms, so a duration of `0` is not
evidence of failure. `first_frame_ms` is printed with one decimal for that reason.

`Config::from_args()` understands:

| Flag | Meaning |
|---|---|
| `--cells N` | how many grid cells |
| `--mode anim\|one\|idle` | what changes per frame |
| `--warmup S` / `--seconds S` | measurement window |
| `--width` / `--height` | window size |
| `--gpu` | opt into a GPU renderer (framework-specific) |
| `--uncapped` | disable vsync pacing |
| `--title T` | window title (so screenshots can find it) |

### Step 2 — write a `run()` and reuse a scene

Take `examples/01-grid-scene/scene.rs` unchanged and provide the three things it
asks for:

```rust
// my-framework/src/main.rs
use my_framework::prelude::*;

include!("../../scene.rs");   // brings in Scene, scene_main(), mod bench

impl Render for Scene {
    fn render(&mut self, window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        let (w, h, font) = self.cell;
        let t = self.frame();
        if self.mode.animated() {
            window.request_animation_frame();
        }
        // ... build N divs from self.color(i, t) and self.label(i, t) ...
    }
}

fn run(cfg: bench::Config, scene: Scene) { /* open the window */ }

fn main() {
    scene_main("my-framework", bench::Config::from_args());
}
```

That is exactly how both crates here are structured — see
`examples/01-grid-scene/bui/src/main.rs` for a worked example: the shared scene is
85 lines, and the whole framework-specific file around it is 92 lines including
its doc comment.

### Step 3 — drive it

`bench/run.py` is the runner. To add a framework, edit two dicts at the top:

```python
BINARIES = {
    "mine": "grid-scene-mine",        # binary name under target/release
    ...
}

configs = [
    ("bui",  [],       "bui (CPU raster)"),
    ("mine", ["--gpu"], "mine (GPU)"),          # add your row
    ("gpui", [],       "gpui (GPU, Vulkan)"),
]
```

Everything else — interleaving, retries, median-with-spread, report generation —
works unchanged. `sweep_grid()` and `sweep_form()` are the two loops; `verdict()`
and `write_report()` turn results into Markdown.

### What you get for free by reusing it

- **Fair comparison by construction:** same scene source, same window, same
  compiler profile, same accounting.
- **The three metrics that matter:** CPU ms/frame, GPU engine ms/frame, and their
  sum. Most benchmarks report only one, which lets a framework look good by
  pushing work to the other half of the machine.
- **Failure detection:** `is_valid()` rejects runs that never drew a frame
  (compositor occlusion, headless CI) instead of averaging in a fake 0.00 ms.
- **Report generation** with settings and binary checksums baked in, so two runs
  are comparable.

---

## 2. "I only want the measurement code"

`bench-common/src/lib.rs` is 565 lines and self-contained. The parts you probably
want, in isolation:

**Process CPU time, exact, all threads.** `CLOCK_PROCESS_CPUTIME_ID` on Linux
counts nanoseconds per thread. Do *not* use `getrusage` or `GetProcessTimes`
alone: the former is coarse, and the latter is charged per ~15.6 ms scheduler
tick, which aliases catastrophically with a 60 Hz frame loop and can under-report
by 3x. (BUI's own benchmark README documents exactly this trap.)

**GPU engine time per process, on Linux, without root or a vendor tool:**

```rust
// /proc/<pid>/fdinfo/* contains, per DRM client:
//   drm-client-id: 158
//   drm-engine-render: 31611373266 ns
//   drm-engine-copy:   0 ns
```

Sum `drm-engine-*` across all fds, sample twice, divide by frames. This works on
Intel and AMD iGPUs, which export no utilisation percentage on Linux. Caveat:
a GLX client may have no DRM fd of its own (submissions go through the X server),
in which case you get `None` — report it as unknown, never as zero.

**Resident vs private memory.** `VmRSS` and `RssAnon` from `/proc/self/status`.
`RssAnon` is the honest "what this app costs" number; `VmRSS` includes shared
library pages that the OS would map anyway.

**Settling instead of sleeping.** `settle()` waits for the frame rate to stop
changing rather than sleeping a fixed time. Without it, whichever framework warms
up more slowly (font caches, GPU device bring-up) gets charged for it.

### Verified standalone extraction

This was tested, not assumed. A crate containing only `bench-common` and a
framework-free binary — no GUI toolkit at all — builds and reports:

```sh
# /tmp/reuse-test: [workspace] with bench-common + app
cargo build --release && ./target/release/app --cells 300 --mode anim --warmup 1 --seconds 2
# {"app":"bench-common-standalone","renderer":"cpu",...,"fps":61.9,"cpu_pct":0.7,
#  "cpu_ms_per_frame":0.109,"ws_mb":2.6,"gpu_ms_per_frame":null,
#  "first_frame_ms":0.2,"frames_measured":233}
```

So the measurement layer is genuinely independent of the frameworks in this repo:
2.6 MB resident, zero dependencies, nothing to port. That is the piece most worth
reusing.

---

## 3. "I want to build a headless-testable GUI app in either framework"

Both example crates are minimal, buildable applications — better starting points
than either project's own hello-world because they are small, typed, and verified.

| Start from | Gives you |
|---|---|
| `examples/02-settings-form/bui-native/` | **The good one for a real BUI app.** A form using `NumberField`, `Checkbox`, `ProgressBar`, `Button` — Blender's actual widgets, which gpui does not have. 81 lines total. |
| `examples/02-settings-form/bui/` | The same form from `div`s, if you want the plain layout primitives. |
| `examples/01-grid-scene/bui/` | Animation loop + damage-friendly rendering, plus the `--gpu` switch. |
| `examples/01-grid-scene/gpui/` | The minimal correct gpui app: `Application::new().run`, `open_window`, `Render` impl, `request_animation_frame`. |

Delete the `bench` include and `scene_main(...)` call, replace with your own
`main`, done. The `Cargo.toml` shows the exact dependency line you need
(`blenderui = "0.5.0"` or `gpui = "0.2.2"`).

Useful transferable details that took time to find:

- **BUI's root is `<body>`**, which has a browser's default 8 px margin. Wrap in
  `body().m_0()` or you get an 8 px inset you did not ask for.
- **BUI's `request_animation_frame` needs `&mut self`**; gpui's needs `&self`.
- **gpui needs `cx.activate(true)`** or the window opens unfocused.
- **`--uncapped`**: BUI exposes `Window::set_vsync(false)`; gpui 0.2.2 has no
  equivalent on Linux.
- **On Wayland, both frameworks may draw nothing if occluded.** See §6.

---

## 4. "I want the screenshots / the figures"

| Need | Use |
|---|---|
| PNGs of each example | already committed in `docs/shots/` |
| Regenerate them | `python3 bench/shots.py` (needs `import` or `xwd`+`ffmpeg`) |
| The screenshots as tables in Markdown | copy the pattern from `README.md` §"The two examples" |
| A visual diff of the two frameworks | `grid-bui-cpu.png` and `grid-gpui.png` are the same scene; compare directly |

`shots.py` forces the X11 window path (`env.pop("WAYLAND_DISPLAY")`) because
Wayland has no cross-application window capture. It matches windows by title, so
`--title` exists on all apps.

---

## 5. "I want the numbers without re-running anything"

```sh
python3 bench/run.py --report-only          # RESULTS.md from committed results.json
```

`bench/results.json` holds every row plus `_meta` (repetitions, warmup, seconds)
and the md5 of each binary measured. So the published tables are regenerable
without touching a GPU, and you can diff two runs by their `_meta.checksums`.

To pull numbers into your own analysis:

```python
import json
data = json.load(open("bench/results.json"))
rows = data["rows"]

def total_ms(r):
    return (r["cpu_ms_per_frame"] or 0) + (r["gpu_ms_per_frame"] or 0)

anim = [r for r in rows if r["example"] == 1 and r["mode"] == "anim"]
for r in anim:
    print(f'{r["app"]:22s} {r["cells"]:5d} cells  {total_ms(r):6.2f} ms')
```

Each row carries `_spread` (min/max per metric) so you can report confidence, not
just medians.

---

## 6. Traps when reusing this setup

Each of these cost real time and would silently produce wrong numbers.

**Wayland occlusion stalls the frame loop.** A compositor withholds frame
callbacks from windows it thinks are occluded, so a benchmark window behind your
terminal renders **zero frames** for the whole measured window. It then reports a
flattering "0.00 ms per frame". Both harnesses here clear `WAYLAND_DISPLAY` to
force X11 (via XWayland) and reject any run under 0.5 fps. If you write your own
driver, do the same or you will publish nonsense.

**`GetProcessTimes` aliases with 60 Hz.** Use `CLOCK_PROCESS_CPUTIME_ID` (Linux)
or `QueryProcessCycleTime` (Windows). Never `GetProcessTimes` for per-frame CPU.

**FPS saturates and hides everything.** At 1000 cells these three configurations
all show ~60 fps on screen while costing 6.4, 23.9 and 12.3 ms of machine per
frame. Report ms/frame.

**CPU alone lets a framework cheat.** gpui does 10.2 ms CPU and 2.0 ms GPU;
BUI-GPU does 2.8 ms CPU and 21.1 ms GPU. Neither column alone is a verdict.

**A desktop is not a lab.** Interleave configurations within each repetition and
report spread. Rows measured minutes apart are not comparable.

**Check `uptime` before you start, and record load while you run.** A sweep of
this repo was once invalidated by an unrelated package build that took all eight
threads: BUI's CPU raster read 21.91 ms/frame where an idle machine gives 7.16 —
a 3x inflation, every row of it. Nothing in the data looked "wrong"; it only
looked slow. The harness now stores `load1` on every row so a contaminated
`results.json` can be spotted afterwards (`max(r["load1"] for r in rows)`), but
the cheap fix is to look before you measure.

**`--gpu` must be asserted, not assumed.** The verifier checks that the GPU
renderer actually lowered CPU and raised RSS; a silently-fallen-back software
path otherwise looks like a spectacular result. (This repo's own verifier caught
the bug where `--gpu` was never passed.)

**A duration of zero is not a failure signal.** `first_frame_ms` can round to `0`
for an app that reaches its first frame in microseconds. Judge a run by
`frames_measured`, which counts renders. (Found by extracting `bench-common` into
a framework-free binary: it reported `first_frame_ms: 0` while rendering happily
at 62 fps.)

**First-frame timing includes framework init, not process start.** Fine for
comparing frameworks; do not call it "app launch time".

---

## 7. What is deliberately not reusable

- **The absolute numbers.** They are one laptop, one session, one power state.
  The ratios are the finding; the milliseconds are local.
- **`third_party/xattr`** — a workaround for a dependency bug, not a library.
  Drop it when `xattr` fixes `ENOATTR` on glibc; check
  `[patch.crates-io]` in `Cargo.toml`.
- **`third_party/stubs`** — symlinks for distros without `libxkbcommon-dev`.
  Use the real `-dev` packages where available.
- **`.cargo/config.toml`** — points at those stubs; delete it if unnecessary.

## 8. Licensing when you copy

| Part | Origin | Licence |
|---|---|---|
| `bench-common`, `bench/*`, this repo's scenes | written here | none declared — add your own (MIT/Apache-2.0 recommended) |
| `third_party/xattr` | crates.io | MIT/Apache-2.0, notices included |
| `blenderui` (dependency) | Blender-derived | **GPL-3.0-or-later** |
| `gpui` (dependency) | Zed | Apache-2.0 |

The scenes (`scene.rs`, `form.rs`) are derived from BUI's own benchmark scene,
which is GPL-3.0-or-later. If you copy them into your own project, honour that.
The `bench-common` measurement code is independent of both frameworks and can be
relicensed freely.
