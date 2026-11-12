//! Example 2, framework A: a small settings form on **blenderui (BUI)**.
//!
//! This measures what a tool window costs: time to first frame, resident memory
//! and idle CPU. The form is static, so the interesting number is how cheaply
//! the framework can get it on screen and then get out of the way.
//!
//! Run:
//! ```text
//! cargo run --release -p settings-form-bui -- --seconds 10
//! cargo run --release -p settings-form-bui -- --seconds 10 --gpu
//! ```

use blenderui::prelude::*;
use blenderui::Window;

include!("../../form.rs");

impl AnimationFrame for Window {
    fn request_animation_frame(&mut self) {
        Window::request_animation_frame(self);
    }
}

impl Render for Settings {
    fn render(&mut self, window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        self.first_frames(window);
        // A label on the left, a field on the right - the shape of every
        // settings panel, built from divs so gpui can build the same one.
        let field = |label: &'static str| {
            div()
                .flex()
                .items_center()
                .gap(px(8.0))
                .child(div().w(px(70.0)).text_color(rgb(0xb8b8b8)).child(label))
                .child(
                    div()
                        .flex_1()
                        .h(px(20.0))
                        .px(px(6.0))
                        .rounded(px(4.0))
                        .bg(rgb(0x1d1d1d))
                        .border_1()
                        .border_color(rgb(0x3d3d3d))
                        .text_color(rgb(0xe6e6e6))
                        .child("Cube"),
                )
        };
        body().m_0().size_full().child(
            div()
                .size_full()
                .flex()
                .flex_col()
                .gap(px(8.0))
                .p(px(12.0))
                .bg(rgb(0x303030))
                .text_color(rgb(0xe6e6e6))
                .text_size(px(13.0))
                .child(div().text_size(px(16.0)).child("Settings"))
                .child(field("Name"))
                .child(field("Object"))
                .child(
                    div()
                        .flex()
                        .items_center()
                        .gap(px(8.0))
                        .child(
                            div()
                                .w(px(14.0))
                                .h(px(14.0))
                                .rounded(px(3.0))
                                .bg(rgb(0x4772b3)),
                        )
                        .child("Shadows"),
                )
                .child(
                    div().h(px(20.0)).rounded(px(4.0)).bg(rgb(0x545454)).child(
                        div()
                            .w(px(120.0))
                            .h(px(20.0))
                            .rounded(px(4.0))
                            .bg(rgb(0x4772b3)),
                    ),
                )
                .child(
                    div()
                        .w(px(80.0))
                        .h(px(22.0))
                        .rounded(px(4.0))
                        .bg(rgb(0x545454))
                        .flex()
                        .items_center()
                        .justify_center()
                        .child("Apply"),
                ),
        )
    }
}

fn run(cfg: bench::Config) {
    Application::new().gpu(cfg.gpu).run(move |cx: &mut App| {
        let bounds = Bounds {
            origin: point(px(100.0), px(100.0)),
            size: size(px(360.0), px(260.0)),
        };
        cx.open_window(
            WindowOptions {
                window_bounds: Some(WindowBounds::Windowed(bounds)),
                titlebar: cfg.title.clone().map(|title| TitlebarOptions {
                    title: Some(title.into()),
                }),
                ..Default::default()
            },
            |_, cx| cx.new(|_| Settings::new()),
        )
        .unwrap();
    });
}

const APP_LABEL: &str = "bui";

fn main() {
    settings_main(APP_LABEL, bench::Config::from_args());
}
