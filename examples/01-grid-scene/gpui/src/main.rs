//! Example 1, framework B: the shared grid scene on **gpui**.
//!
//! gpui is Zed's UI framework (`gpui` 0.2.2): layout in a taffy-based engine,
//! rendering through blade on Vulkan (Linux) / Metal (macOS) / D3D or Vulkan
//! (Windows). There is no software renderer: every frame goes to the GPU.
//!
//! Run:
//! ```text
//! cargo run --release -p grid-scene-gpui -- --cells 1000 --mode anim
//! ```

use gpui::{
    div, point, px, rgb, size, App, AppContext, Bounds, Context, IntoElement, ParentElement,
    Render, Styled, Window, WindowBounds, WindowOptions,
};

// The same shared scene source the BUI binary compiles.
include!("../../scene.rs");

impl Render for Scene {
    fn render(&mut self, window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        let (w, h, font) = self.cell;
        let t = self.frame();
        if self.mode.animated() {
            window.request_animation_frame();
        }
        // gpui's root `div` fills the window: no body, no default margin.
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
            }))
    }
}

/// Open the window and run gpui's event loop. gpui renders on the GPU always,
/// so `cfg.gpu` has no effect. `--uncapped` is reported for symmetry but is not
/// actionable: gpui 0.2.2 exposes no vsync switch on Linux, and its Wayland
/// surface uses whatever present mode the compositor negotiates. In practice
/// gpui is CPU-bound on this class of scene, so its cap rarely binds.
fn run(cfg: bench::Config, scene: Scene) {
    let title = cfg.title.clone();
    gpui::Application::new().run(move |cx: &mut App| {
        let bounds = Bounds::new(point(px(0.0), px(0.0)), size(px(cfg.width), px(cfg.height)));
        cx.open_window(
            WindowOptions {
                window_bounds: Some(WindowBounds::Windowed(bounds)),
                titlebar: title.clone().map(|title| gpui::TitlebarOptions {
                    title: Some(title.into()),
                    ..Default::default()
                }),
                ..Default::default()
            },
            |_, cx| cx.new(|_| scene),
        )
        .unwrap();
        cx.activate(true);
    });
}

const APP_LABEL: &str = "gpui";

fn main() {
    // gpui has no software renderer: every frame goes to the GPU, so the
    // renderer is GPU whatever the arguments say.
    let mut cfg = bench::Config::from_args();
    cfg.gpu = true;
    scene_main(APP_LABEL, cfg);
}
