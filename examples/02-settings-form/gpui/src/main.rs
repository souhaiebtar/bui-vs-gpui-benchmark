//! Example 2, framework B: the same settings form on **gpui**.
//!
//! gpui ships no form widgets, so the controls are the same styled divs the BUI
//! binary draws. That makes this a like-for-like test of the framework
//! around the widgets: startup, memory, and what an idle window costs.
//!
//! Run:
//! ```text
//! cargo run --release -p settings-form-gpui -- --seconds 10
//! ```

use gpui::{
    div, point, px, rgb, size, App, AppContext, Bounds, Context, IntoElement, ParentElement,
    Render, Styled, Window, WindowBounds, WindowOptions,
};

include!("../../form.rs");

impl AnimationFrame for Window {
    fn request_animation_frame(&mut self) {
        Window::request_animation_frame(self);
    }
}

impl Render for Settings {
    fn render(&mut self, window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        self.first_frames(window);
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
            )
    }
}

fn run(cfg: bench::Config) {
    gpui::Application::new().run(move |cx: &mut App| {
        let bounds = Bounds::new(point(px(100.0), px(100.0)), size(px(360.0), px(260.0)));
        cx.open_window(
            WindowOptions {
                window_bounds: Some(WindowBounds::Windowed(bounds)),
                titlebar: cfg.title.clone().map(|title| gpui::TitlebarOptions {
                    title: Some(title.into()),
                    ..Default::default()
                }),
                ..Default::default()
            },
            |_, cx| cx.new(|_| Settings::new()),
        )
        .unwrap();
        cx.activate(true);
    });
}

const APP_LABEL: &str = "gpui";

fn main() {
    // gpui has no software renderer: every frame goes to the GPU.
    let mut cfg = bench::Config::from_args();
    cfg.gpu = true;
    settings_main(APP_LABEL, cfg);
}
