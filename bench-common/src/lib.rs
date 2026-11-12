//! Scene parameters and process measurement shared by every example.
//!
//! Nothing in here knows which framework is being measured: the same code
//! counts frames, reads the CPU clock and the RSS for a BUI process and for a
//! gpui process, so the two columns of the results tables are comparable.
//!
//! Measurements are taken from a background thread:
//!
//! * **time to first frame** - from `main()` to the first rendered frame;
//! * **warm-up** - let the framework settle, JIT-free but cache-warm;
//! * **measured window** - CPU time, wall time, frames, RSS sampled every
//!   100 ms, plus GPU engine time on Linux (`/proc/<pid>/fdinfo`);
//! * one JSON line on stdout, then `exit(0)` so a stuck event loop can't
//!   poison the numbers.
//!
//! On Linux process CPU time comes from `CLOCK_PROCESS_CPUTIME_ID`, which counts
//! every thread (so 150 % means 1.5 cores) at nanosecond resolution. On Windows
//! it comes from `QueryProcessCycleTime` - `GetProcessTimes` is charged per
//! ~15.6 ms scheduler tick and aliases badly with a 60 Hz frame loop.

#![allow(dead_code)]

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

/// Frames actually rendered. Every app calls [`frame`] once per render, so this
/// counts *rendered* frames, not presented frames: a framework that renders
/// twice per presented frame is charged for both.
pub static FRAMES: AtomicU64 = AtomicU64::new(0);

/// Count one rendered frame.
pub fn frame() -> u64 {
    FRAMES.fetch_add(1, Ordering::Relaxed)
}

/// How many frames have been rendered so far.
pub fn frames() -> u64 {
    FRAMES.load(Ordering::Relaxed)
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/// `--mode` selects what changes between frames.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Every cell changes every frame: full restyle, relayout and repaint.
    Anim,
    /// The whole scene is re-rendered but only the first cell changes, which is
    /// what a hover, a clock or a ticking value really looks like.
    One,
    /// Render once and go quiet. Should cost 0 % CPU.
    Idle,
}

impl Mode {
    pub fn name(self) -> &'static str {
        match self {
            Mode::Anim => "anim",
            Mode::One => "one",
            Mode::Idle => "idle",
        }
    }
    pub fn animated(self) -> bool {
        self != Mode::Idle
    }
    pub fn one(self) -> bool {
        self == Mode::One
    }
}

pub struct Config {
    pub cells: usize,
    pub mode: Mode,
    pub warmup: f64,
    pub seconds: f64,
    pub width: f32,
    pub height: f32,
    /// Draw on the GPU renderer where the framework has one (BUI only; gpui is
    /// always GPU-rendered).
    pub gpu: bool,
    /// Do not wait for vsync between frames. Without this both frameworks cap
    /// at the display's refresh rate and every frame rate reads 60.
    pub uncapped: bool,
    /// Window title, so `bench/shots.py` (and you) can find the window.
    pub title: Option<String>,
}

impl Config {
    pub fn from_args() -> Config {
        let args: Vec<String> = std::env::args().collect();
        let get = |k: &str, d: &str| {
            args.iter()
                .position(|a| a == k)
                .and_then(|i| args.get(i + 1))
                .cloned()
                .unwrap_or_else(|| d.to_owned())
        };
        let mode = match get("--mode", "anim").as_str() {
            "one" => Mode::One,
            "idle" => Mode::Idle,
            _ => Mode::Anim,
        };
        Config {
            cells: get("--cells", "100").parse().unwrap_or(100),
            mode,
            warmup: get("--warmup", "3").parse().unwrap_or(3.0),
            seconds: get("--seconds", "10").parse().unwrap_or(10.0),
            width: get("--width", "1000").parse().unwrap_or(1000.0),
            height: get("--height", "800").parse().unwrap_or(800.0),
            gpu: args.iter().any(|a| a == "--gpu")
                || std::env::var("BUI_GPU").map(|v| v == "1").unwrap_or(false),
            uncapped: args.iter().any(|a| a == "--uncapped")
                || std::env::var("BENCH_UNCAPPED")
                    .map(|v| v == "1")
                    .unwrap_or(false),
            title: args
                .iter()
                .position(|a| a == "--title")
                .and_then(|i| args.get(i + 1))
                .cloned(),
        }
    }

    /// Grid layout filling the window: (columns, cell width, cell height, font
    /// size). Cells keep roughly their aspect ratio, as many as fit.
    pub fn grid(&self) -> (usize, f32, f32, f32) {
        let gap = 2.0;
        let cols = ((self.cells as f32 * self.width / self.height).sqrt().ceil() as usize).max(1);
        let rows = self.cells.div_ceil(cols);
        let w = (self.width - gap) / cols as f32 - gap;
        let h = (self.height - gap) / rows as f32 - gap;
        (
            cols,
            w.floor(),
            h.floor(),
            (h * 0.55).clamp(8.0, 14.0).floor(),
        )
    }

    /// The frame number cell `i` shows: everything follows `t`, or only cell 0
    /// in [`Mode::One`].
    pub fn t_for(&self, i: usize, t: u64) -> u64 {
        if self.mode.one() && i != 0 {
            0
        } else {
            t
        }
    }
}

// ---------------------------------------------------------------------------
// The scene content (identical for both frameworks)
// ---------------------------------------------------------------------------

/// The colour of cell `i` at frame `t` as `0xRRGGBB`.
pub fn cell_color(i: usize, t: u64) -> u32 {
    let h = ((i as u64 * 7 + t * 3) % 360) as f32 / 60.0;
    let (s, v) = (0.55f32, 0.75f32);
    let c = v * s;
    let x = c * (1.0 - (h % 2.0 - 1.0).abs());
    let (r, g, b) = match h as u32 {
        0 => (c, x, 0.0),
        1 => (x, c, 0.0),
        2 => (0.0, c, x),
        3 => (0.0, x, c),
        4 => (x, 0.0, c),
        _ => (c, 0.0, x),
    };
    let m = v - c;
    let byte = |f: f32| ((f + m) * 255.0).round() as u32;
    (byte(r) << 16) | (byte(g) << 8) | byte(b)
}

/// The label of cell `i` at frame `t`.
pub fn cell_label(i: usize, t: u64) -> String {
    format!("{}", (i as u64 * 13 + t) % 1000)
}

// ---------------------------------------------------------------------------
// Process measurement
// ---------------------------------------------------------------------------

/// Memory of the process, in bytes.
#[repr(C)]
#[derive(Default, Clone, Copy)]
pub struct Mem {
    pub working_set: usize,
    pub peak_working_set: usize,
    pub private_bytes: usize,
}

pub use platform::{cpu_ns, memory};

/// Windows: exact cycle counts and the working set, straight from kernel32.
#[cfg(windows)]
mod platform {
    use super::Mem;
    use std::time::Duration;

    #[repr(C)]
    #[derive(Default)]
    struct FileTime {
        lo: u32,
        hi: u32,
    }

    #[repr(C)]
    #[derive(Default)]
    struct MemCounters {
        cb: u32,
        page_faults: u32,
        peak_working_set: usize,
        working_set: usize,
        quota_peak_paged: usize,
        quota_paged: usize,
        quota_peak_nonpaged: usize,
        quota_nonpaged: usize,
        pagefile: usize,
        peak_pagefile: usize,
        private_bytes: usize,
    }

    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetCurrentProcess() -> isize;
        fn QueryProcessCycleTime(p: isize, cycles: *mut u64) -> i32;
        fn K32GetProcessMemoryInfo(p: isize, m: *mut MemCounters, cb: u32) -> i32;
    }

    static mut HZ: f64 = 1.0e9;

    /// Calibrate the TSC once, against the wall clock.
    pub fn calibrate() {
        // SAFETY: rdtsc has no preconditions on x86_64; HZ is written once,
        // before any measuring thread reads it.
        unsafe {
            let (t0, c0) = (std::time::Instant::now(), core::arch::x86_64::_rdtsc());
            std::thread::sleep(Duration::from_millis(50));
            let (t1, c1) = (std::time::Instant::now(), core::arch::x86_64::_rdtsc());
            HZ = (c1 - c0) as f64 / (t1 - t0).as_secs_f64();
        }
    }

    /// CPU nanoseconds used by every thread of the process.
    pub fn cpu_ns() -> u64 {
        let mut cycles = 0u64;
        // SAFETY: the current-process pseudo handle and a valid out pointer.
        unsafe { QueryProcessCycleTime(GetCurrentProcess(), &mut cycles) };
        // SAFETY: HZ is set before measuring starts (see `calibrate`).
        (cycles as f64 / unsafe { HZ } * 1e9) as u64
    }

    pub fn memory() -> Mem {
        let mut m = MemCounters {
            cb: std::mem::size_of::<MemCounters>() as u32,
            ..Default::default()
        };
        // SAFETY: `m` is a writable PROCESS_MEMORY_COUNTERS_EX and `cb` is its size.
        unsafe { K32GetProcessMemoryInfo(GetCurrentProcess(), &mut m, m.cb) };
        Mem {
            working_set: m.working_set,
            peak_working_set: m.peak_working_set,
            private_bytes: m.private_bytes,
        }
    }
}

/// Linux: `CLOCK_PROCESS_CPUTIME_ID` counts every thread exactly; memory and
/// GPU engine time come from `/proc/self`.
#[cfg(target_os = "linux")]
mod platform {
    use super::Mem;
    use std::fs;

    const CLOCK_PROCESS_CPUTIME_ID: i32 = 2;

    #[repr(C)]
    struct Timespec {
        sec: i64,
        nsec: i64,
    }

    unsafe extern "C" {
        fn clock_gettime(clock: i32, ts: *mut Timespec) -> i32;
    }

    /// Nothing to calibrate: the kernel reports nanoseconds.
    pub fn calibrate() {}

    /// CPU nanoseconds used by every thread of the process.
    pub fn cpu_ns() -> u64 {
        let mut ts = Timespec { sec: 0, nsec: 0 };
        // SAFETY: a valid clock id and a valid out pointer.
        unsafe { clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &mut ts) };
        u64::try_from(ts.sec).unwrap_or(0) * 1_000_000_000 + u64::try_from(ts.nsec).unwrap_or(0)
    }

    fn status_bytes(key: &str) -> usize {
        let Ok(text) = fs::read_to_string("/proc/self/status") else {
            return 0;
        };
        text.lines()
            .find_map(|l| l.strip_prefix(key))
            .and_then(|v| v.split_whitespace().next()?.parse::<usize>().ok())
            .map_or(0, |kb| kb * 1024)
    }

    pub fn memory() -> Mem {
        Mem {
            working_set: status_bytes("VmRSS:"),
            peak_working_set: status_bytes("VmHWM:"),
            private_bytes: status_bytes("RssAnon:"),
        }
    }
}

/// GPU engine time of this process, in nanoseconds, summed over every DRM
/// client it owns (Linux only). `None` where the kernel does not export it.
///
/// Intel/AMD iGPUs do not report utilisation as a percentage on Linux, but the
/// DRM per-client `drm-engine-*` counters do give exact engine nanoseconds, and
/// those are what the GPU column of the results is built from.
///
/// Note that a GL client on X11 may have no DRM fd of its own: GLX rendering is
/// submitted through the X server, whose own DRM client does the work. In that
/// case this returns `None` and the GPU column is honestly blank rather than a
/// made-up zero. `BENCH_GPU_DEBUG=1` prints what was found.
pub fn gpu_ns() -> Option<u64> {
    #[cfg(target_os = "linux")]
    {
        let pid = std::process::id();
        let mut total = 0u64;
        let mut found = false;
        let Ok(entries) = std::fs::read_dir(format!("/proc/{pid}/fdinfo")) else {
            return None;
        };
        for entry in entries.flatten() {
            let Ok(text) = std::fs::read_to_string(entry.path()) else {
                continue;
            };
            if !text.contains("drm-engine") {
                continue;
            }
            found = true;
            for line in text.lines() {
                let Some(rest) = line.strip_prefix("drm-engine") else {
                    continue;
                };
                // `drm-engine-<engine>:\t<ns> ns`
                let Some((_, value)) = rest.split_once(':') else {
                    continue;
                };
                let ns: u64 = value
                    .trim()
                    .trim_end_matches(" ns")
                    .trim()
                    .parse()
                    .unwrap_or(0);
                total = total.saturating_add(ns);
            }
        }
        if std::env::var("BENCH_GPU_DEBUG")
            .map(|v| v == "1")
            .unwrap_or(false)
        {
            let where_from = format!("/proc/{pid}/fdinfo");
            if found {
                eprintln!("gpu_ns: {total} ns ({where_from})");
            } else {
                eprintln!("gpu_ns: no DRM client in this process ({where_from})");
            }
        }
        found.then_some(total)
    }
    #[cfg(not(target_os = "linux"))]
    {
        None
    }
}

// ---------------------------------------------------------------------------
// The measuring thread
// ---------------------------------------------------------------------------

/// Start the measuring thread. `label` names this configuration in the JSON
/// line, e.g. `"bui-gpu"`. Call once, right at the top of `main()`.
pub fn start(label: &'static str, cfg: &Config) -> Measured {
    platform::calibrate();
    let launched = Instant::now();
    let (warmup, secs) = (cfg.warmup, cfg.seconds);
    let cells = cfg.cells;
    let mode = cfg.mode.name();
    let renderer = if cfg.gpu { "gpu" } else { "cpu" };
    let uncapped = cfg.uncapped;
    std::thread::spawn(move || {
        let first = wait_for_first_frame(launched);
        // Warm up: let the framework settle (font caches, glyph atlases, the GPU
        // device coming up) and the schedulers fill their caches. Wait for the
        // frame rate to *stop changing* rather than for a fixed time: BUI's GPU
        // renderer draws the first frames on the CPU until the device is ready,
        // and a first-run font cache can make early frames 10x slower.
        settle(Duration::from_secs_f64(warmup), Duration::from_secs(1));

        let (wall0, cpu0, frames0, gpu0) =
            (Instant::now(), cpu_ns(), frames(), gpu_ns().unwrap_or(0));
        let mut peak_ws = 0usize;
        let mut ws_sum = 0f64;
        let mut samples = 0u32;
        while wall0.elapsed().as_secs_f64() < secs {
            std::thread::sleep(Duration::from_millis(100));
            let m = memory();
            peak_ws = peak_ws.max(m.working_set);
            ws_sum += m.working_set as f64;
            samples += 1;
        }
        let wall = wall0.elapsed().as_secs_f64();
        let frames = frames() - frames0;
        let cpu = (cpu_ns() - cpu0) as f64 / 1e9;
        let gpu = match (gpu_ns(), gpu0) {
            (Some(end), start) => Some((end.saturating_sub(start)) as f64 / 1e9),
            (None, _) => None,
        };
        let m = memory();
        let mb = |b: f64| b / (1024.0 * 1024.0);
        let gpu_json = match gpu {
            // share of one core's worth of GPU engine time, per frame
            Some(g) if frames > 0 => format!("{:.2}", g * 1000.0 / frames as f64),
            Some(_) => "0.00".to_owned(),
            None => "null".to_owned(),
        };
        println!(
            "{{\"app\":\"{label}\",\"renderer\":\"{renderer}\",\"uncapped\":{uncapped},\
             \"cells\":{cells},\"mode\":\"{mode}\",\"fps\":{:.1},\"cpu_pct\":{:.1},\
             \"cpu_ms_per_frame\":{:.3},\"ws_mb\":{:.1},\"peak_ws_mb\":{:.1},\
             \"private_mb\":{:.1},\"gpu_ms_per_frame\":{gpu_json},\"first_frame_ms\":{:.1},\
             \"frames_measured\":{}}}",
            frames as f64 / wall,
            cpu / wall * 100.0,
            if frames > 0 {
                cpu * 1000.0 / frames as f64
            } else {
                0.0
            },
            mb(ws_sum / samples.max(1) as f64),
            mb(peak_ws as f64),
            mb(m.private_bytes as f64),
            // One decimal, not zero: a fast app really can reach its first frame
            // in under 0.05 ms, and printing "0" makes that indistinguishable
            // from "never drew a frame". `frames_measured` settles it.
            first.as_secs_f64() * 1000.0,
            frames0 + frames,
        );
        // Leave now: a framework that keeps animating must not skew the loop.
        std::process::exit(0);
    });
    Measured { launched }
}

/// Handle returned by [`start`], for apps that want to report their own timings.
pub struct Measured {
    launched: Instant,
}

impl Measured {
    /// Time since `main()` started.
    pub fn elapsed(&self) -> Duration {
        self.launched.elapsed()
    }

    /// Print and exit if the window never produces a frame (headless CI, a
    /// missing display, a driver that refuses to start the Vulkan device).
    pub fn arm_watchdog(&self, after: Duration) {
        std::thread::spawn(move || {
            std::thread::sleep(after);
            if frames() == 0 {
                eprintln!(
                    "no frame after {:.0}s - no display or no GPU? DISPLAY={:?} WAYLAND_DISPLAY={:?}",
                    after.as_secs_f64(),
                    std::env::var("DISPLAY").ok(),
                    std::env::var("WAYLAND_DISPLAY").ok()
                );
                std::process::exit(2);
            }
        });
    }
}

fn wait_for_first_frame(launched: Instant) -> Duration {
    loop {
        if frames() > 0 {
            return launched.elapsed();
        }
        if launched.elapsed() > Duration::from_secs(60) {
            return Duration::ZERO;
        }
        std::thread::sleep(Duration::from_millis(1));
    }
}

/// Sleep at least `at_least`, then keep sleeping in 250 ms steps until the
/// frame rate stops rising between steps (or `limit` passes).
///
/// A fixed warm-up would charge the first frames to whichever framework warms
/// up more slowly: BUI decodes Inter and rasterizes glyphs on first use, and its
/// GPU renderer draws on the CPU until the device is up. Settling on a stable
/// rate makes the measured window about steady-state behaviour, which is what
/// "cost per frame" is supposed to mean.
fn settle(at_least: Duration, limit: Duration) {
    std::thread::sleep(at_least);
    let start = Instant::now();
    let mut last = rate_over(Duration::from_millis(250));
    while start.elapsed() < limit {
        std::thread::sleep(Duration::from_millis(250));
        let now = rate_over(Duration::from_millis(250));
        // within 10 % of the previous window: settled
        if last > 0.0 && (now - last).abs() / last < 0.10 {
            return;
        }
        last = now;
    }
}

/// Frames rendered per second over the last `window`.
fn rate_over(window: Duration) -> f64 {
    let (f0, t0) = (frames(), Instant::now());
    std::thread::sleep(window);
    (frames() - f0) as f64 / t0.elapsed().as_secs_f64()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cpu_time_grows_with_work() {
        let c0 = cpu_ns();
        let mut sum = 0u64;
        for i in 0..20_000_000u64 {
            sum = std::hint::black_box(sum.wrapping_add(i));
        }
        std::hint::black_box(sum);
        assert!(cpu_ns() > c0, "CPU time did not grow");
    }

    #[test]
    fn memory_reports_resident_set() {
        let m = memory();
        assert!(m.working_set > 0, "working set is 0");
        assert!(m.peak_working_set >= m.working_set, "peak below current");
    }

    #[test]
    fn grid_fills_the_window() {
        let cfg = Config {
            cells: 1000,
            mode: Mode::Anim,
            warmup: 0.0,
            seconds: 0.0,
            width: 1000.0,
            height: 800.0,
            gpu: false,
            uncapped: false,
            title: None,
        };
        let (cols, w, h, font) = cfg.grid();
        assert!(cols > 1 && w > 1.0 && h > 1.0 && font >= 8.0);
    }
}
