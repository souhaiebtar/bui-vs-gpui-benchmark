// The grid scene, written once and compiled against BOTH frameworks.
//
// `examples/01-grid-scene/bui/` and `examples/01-grid-scene/gpui/` both
// `include!` this file; each crate's own `main.rs` supplies three things:
//
//   * the framework's prelude (`div`, `px`, `rgb`, `Render`, `Window`, `Context`);
//   * `fn run(cfg, scene)` - open the window and hand over the event loop;
//   * `APP_LABEL` - the name printed in the results.
//
// What the scene draws is deliberately identical in both:
//
//   * a full-window flex container with `flex-wrap`, a 2 px gap, 2 px padding;
//   * N cells, each a rounded box of the same colour and size, holding the same
//     centred number at the same font size;
//   * `--mode anim` changes every cell's colour and label each frame and asks
//     for the next frame; `--mode one` changes only cell 0; `--mode idle`
//     renders once and stops.
//
// This is the scene BUI's own benchmark uses against gpui: it stresses layout
// (N flex children), paint (N rounded rects) and text (N shaped runs) together.
//
// Everything a frame needs is computed once, in `Scene::new`. A `render` that
// parsed `std::env::args()` per frame, or recomputed the grid per frame, would
// charge both frameworks for the benchmark's own bookkeeping.

#[path = "../../bench-common/src/lib.rs"]
mod bench;

/// Everything either framework mutates between frames.
pub struct Scene {
    pub cells: usize,
    pub mode: bench::Mode,
    /// Cell geometry, computed once: (width, height, font size).
    pub cell: (f32, f32, f32),
    /// Frame counter.
    pub t: u64,
}

impl Scene {
    pub fn new(cfg: &bench::Config) -> Scene {
        let (_, w, h, font) = cfg.grid();
        Scene { cells: cfg.cells, mode: cfg.mode, cell: (w, h, font), t: 0 }
    }

    /// Call once per render. Counts the frame and returns the frame number the
    /// cells should show, advancing it when the mode animates.
    pub fn frame(&mut self) -> u64 {
        bench::frame();
        let t = self.t;
        if self.mode.animated() {
            self.t += 1;
        }
        t
    }

    /// The frame number cell `i` shows for a render at frame `t`.
    pub fn t_for(&self, i: usize, t: u64) -> u64 {
        if self.mode == bench::Mode::One && i != 0 {
            0
        } else {
            t
        }
    }

    pub fn color(&self, i: usize, t: u64) -> u32 {
        bench::cell_color(i, self.t_for(i, t))
    }

    pub fn label(&self, i: usize, t: u64) -> String {
        bench::cell_label(i, self.t_for(i, t))
    }
}

/// Parse the arguments, start the measuring thread, then hand the event loop to
/// the framework. The measuring thread exits the process when the measured
/// window is over, so no app needs its own quit path.
///
/// `cfg` comes from the crate's own `main`, which is where the renderer is
/// truthfully declared: BUI reads `--gpu`, gpui is GPU-only so it forces it on.
pub fn scene_main(label: &'static str, cfg: bench::Config) {
    let measured = bench::start(label, &cfg);
    measured.arm_watchdog(std::time::Duration::from_secs(60));
    let scene = Scene::new(&cfg);
    run(cfg, scene);
}
