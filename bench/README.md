# The benchmark harness

| File | What it does |
|---|---|
| `run.py` | The sweep. Starts every binary, collects one JSON line from each, writes `results.json` and `RESULTS.md`. |
| `verify.py` | Sanity checks before you trust a number: does each column measure what it claims? Does the GPU renderer really use the GPU? Do both frameworks render the same scene? |
| `shots.py` | Screenshots of each example into `docs/shots/`. Documentation only, never evidence. |
| `machine.sh` | Prints the CPU, GPU, display and toolchain the numbers came from. |
| `results.json` | The last sweep, including the settings it ran with and the checksums of the binaries measured. |

## Before a run

```sh
cargo build --release
python3 bench/verify.py     # ~1 minute
```

`verify.py` fails loudly on the things that quietly invalidate a comparison:

* a binary missing or built in debug;
* a mode that produces no result (window never appeared);
* the two frameworks rendering wildly different numbers of frames, which means
  one side is not animating;
* `--gpu` not actually reaching the GPU (no DRM client, or no drop in CPU);
* an idle window that keeps rendering;
* a static form that keeps burning CPU.

## During a run

Every configuration runs several times, **interleaved**: BUI, BUI-GPU and gpui
back to back inside one repetition. On a machine that is also someone's desktop,
clocks drift over minutes; interleaving spreads that drift across the
frameworks instead of charging it to whichever ran last.

A run that renders under 0.5 fps (for an animated scene) or never produces a
first frame is retried up to three times, then dropped. A Wayland compositor
stops sending frame callbacks to an occluded window, which stalls the whole
measured window and would otherwise appear as a flattering "0.00 ms per frame".

## Why X11

`run.py` clears `WAYLAND_DISPLAY` so both frameworks open X11 windows (through
XWayland on a Wayland session). Benchmark windows sit behind the terminal, and a
Wayland compositor withholds frame callbacks from windows it thinks are
occluded: gpui then renders zero frames while BUI (X11-only on Linux) does not
care. Running both on X11 removes that asymmetry. Set `BENCH_WAYLAND=1` to keep
the native path.

## After a run

```sh
python3 bench/run.py --report-only      # rebuild RESULTS.md from results.json
```

The report states its own settings (repetitions, warm-up, measured window) and
the md5 of every binary measured, so two runs can be compared exactly.
