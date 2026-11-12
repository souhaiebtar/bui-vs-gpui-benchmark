// The settings form, written once and compiled against BOTH frameworks.
//
// Example 2 measures what a real tool window costs: a small, static form whose
// cost is startup time, memory and idle CPU, not frame rate. gpui has no form
// widgets (no text field, no slider, no button), so the controls are styled
// divs - the same divs in both crates, which keeps the two layouts identical.
//
// Only the two frame-counting lines and the window handle type differ between
// the crates, so this file asks each `main.rs` for one small impl:
//
//     impl form::AnimationFrame for blenderui::Window { ... }
//     impl form::AnimationFrame for gpui::Window       { ... }

#[path = "../../bench-common/src/lib.rs"]
mod bench;

pub struct Settings {
    pub renders: u32,
}

impl Default for Settings {
    fn default() -> Settings {
        Settings::new()
    }
}

impl Settings {
    pub fn new() -> Settings {
        Settings { renders: 0 }
    }

    /// Count this render, and ask for exactly one more so that "first frame on
    /// screen" means the same thing in both frameworks: some present the first
    /// frame only after a second render pass.
    pub fn first_frames(&mut self, window: &mut impl AnimationFrame) {
        bench::frame();
        self.renders += 1;
        if self.renders == 1 {
            window.request_animation_frame();
        }
    }
}

/// The one window method this shared file needs from either framework.
/// BUI's takes `&mut self`, gpui's takes `&self`; both satisfy `&mut`.
pub trait AnimationFrame {
    fn request_animation_frame(&mut self);
}

pub fn settings_main(label: &'static str, cfg: bench::Config) {
    let measured = bench::start(label, &cfg);
    measured.arm_watchdog(std::time::Duration::from_secs(60));
    run(cfg);
}
