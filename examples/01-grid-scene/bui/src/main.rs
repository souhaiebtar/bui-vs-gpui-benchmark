//! Example 1, framework A: the shared grid scene on **blenderui (BUI)**.
//!
//! BUI is the Blender UI toolkit extracted from Blender and exposed through the
//! `blenderui` crate. It has two renderers that draw the same pixels:
//!
//! * the **software raster** (default) - work on the CPU, no GPU device;
//! * the **GPU renderer** (OpenGL 3.3 on Linux, Direct3D 11 on Windows) -
//!   opted into with `--gpu` / `BUI_GPU=1`.
//!
//! Run:
//! ```text
//! cargo run --release -p grid-scene-bui -- --cells 1000 --mode anim
//! cargo run --release -p grid-scene-bui -- --cells 1000 --mode anim --gpu
//! ```

use blenderui::prelude::*;

// The shared scene: `Scene`, `scene_main()`, and `mod bench` (the measurement).
include!("../../scene.rs");

impl Render for Scene {
    fn render(&mut self, window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        let (w, h, font) = self.cell;
        let t = self.frame();
        if self.mode.animated() {
            window.request_animation_frame();
        }
        // BUI's root is `<body>`, which has the browser's default 8 px margin.
        // gpui's root fills the window, so drop the margin to compare like for
        // like: same pixels, same layout work.
        body().m_0().size_full().child(
            div()
                .size_full()
                .bg(rgb(0x303030))
                .flex()
                .flex_wrap()
                .content_start()
                .gap(px(2.0))
                .p(px(2.0))
                .children((0..self.cells).map(|i| {
                    div()
                        .w(px(w))
                        .h(px(h))
                        .bg(rgb(self.color(i, t)))
                        .rounded(px(3.0))
                        .flex()
                        .items_center()
                        .justify_center()
                        .text_size(px(font))
                        .text_color(rgb(0xffffff))
                        .child(self.label(i, t))
                })),
        )
    }
}

/// Open the window and run BUI's event loop. `cfg.gpu` picks the renderer.
fn run(cfg: bench::Config, scene: Scene) {
    let title = cfg.title.clone();
    Application::new().gpu(cfg.gpu).run(move |cx: &mut App| {
        let uncapped = cfg.uncapped;
        let (width, height) = (cfg.width, cfg.height);
        let bounds = Bounds {
            origin: point(px(0.0), px(0.0)),
            size: size(px(width), px(height)),
        };
        cx.open_window(
            WindowOptions {
                window_bounds: Some(WindowBounds::Windowed(bounds)),
                titlebar: title.clone().map(|title| TitlebarOptions {
                    title: Some(title.into()),
                }),
                ..Default::default()
            },
            |window, cx| {
                // Frames as fast as the CPU allows, instead of paced to vsync.
                if uncapped {
                    window.set_vsync(false);
                }
                cx.new(|_| scene)
            },
        )
        .unwrap();
    });
}

const APP_LABEL: &str = "bui";

fn main() {
    // `--gpu` / `BUI_GPU=1` selects the GPU renderer; the CPU raster is default.
    scene_main(APP_LABEL, bench::Config::from_args());
}
