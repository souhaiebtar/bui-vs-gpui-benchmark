//! Example 2, variant: the same settings form on **BUI with Blender's own
//! widgets**.
//!
//! `settings-form-bui` draws the form from `div`s so gpui can draw the same
//! thing. This variant uses the widgets BUI exists for - `NumberField`,
//! `Checkbox`, `ProgressBar` - which is what a real BUI app would write. Compare
//! it with the div version to see what the native widgets cost on top.
//!
//! Run:
//! ```text
//! cargo run --release -p settings-form-bui-native -- --seconds 10
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
        let field = |label: &'static str, value: f64| {
            div()
                .flex()
                .items_center()
                .gap(px(8.0))
                .child(div().w(px(70.0)).text_color(rgb(0xb8b8b8)).child(label))
                .child(NumberField().value(format!("{value}")).step(0.1).flex_1())
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
                .child(field("Name", 1.0))
                .child(field("Location X", 0.0))
                .child(field("Location Y", 0.0))
                .child(Checkbox().checked(true).child("Shadows"))
                .child(ProgressBar().value("0.4"))
                .child(Button().child("Apply")),
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

const APP_LABEL: &str = "bui-widgets";

fn main() {
    settings_main(APP_LABEL, bench::Config::from_args());
}
