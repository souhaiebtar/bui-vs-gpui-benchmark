# Documentation compared: BUI vs GPUI

A side-by-side look at how the two projects document themselves — measured, not
impressionistic. This matters for anyone choosing between them: the framework you
can learn is the framework you can ship.

All figures below were counted from **`blenderui` 0.5.0's repository**
(`github.com/ppmpreetham/BUI`) and **`gpui` 0.2.2** as published on crates.io, on
2026-11-12. Counting method is given for each number so you can re-check it.

---

## 1. The numbers

| Measure | BUI | GPUI | Ratio |
|---|---:|---:|---:|
| Lines of prose documentation (`docs/*.md`) | 4,354 | 133 | **33x** |
| Number of `docs/*.md` pages | 15 | 2 | 7.5x |
| Lines in the top-level README | 2,303 | 66 | **35x** |
| Whole-repo Markdown lines (excl. `node_modules`) | 12,783 | 199 | **64x** |
| Website documentation pages | 68 (`.mdx`) | — (none) | — |
| Code blocks on the website / in docs | 6,029 | 100 (incl. README) | **60x** |
| Rust examples shipped | 21 | 28 | 0.75x |
| Lines in those examples | 1,629 | 5,636 | 0.29x |
| Comment lines in those examples | 127 (7.8 %) | 56 (1.0 %) | 2.3x denser |
| Doc-comment lines in the framework source | 1,903 | 5,742 | 0.33x |
| Doc-comment **density** (docs ÷ source lines) | 8.5 % | 7.3 % | 1.2x |
| Public `fn`s in the Rust API | 406 | 1,347 | 0.3x |
| Direct + transitive dependencies (example app) | **23** | **1,415** | **0.016x** |

How each was counted:

- prose lines: `wc -l docs/*.md` — BUI ships a `docs/` folder in-repo; gpui ships
  two files (`contexts.md`, `key_dispatch.md`), 133 lines total.
- website pages: `find website/src/content/docs -name '*.mdx' | wc -l`.
- code blocks: count of lines starting with ` ``` ` across all doc files, halved.
  For BUI that means `website/src/content/docs/**/*.mdx` (the 68 pages); for gpui
  `docs/*.md` plus the README.
- doc comments: `grep -h -E '^\s*//[/!]'` over the framework's `src/**/*.rs`.
- dependencies: `cargo tree -p <example-crate> | wc -l`.

---

## 2. The shape of each documentation set

### BUI: a book, organised by reader

BUI's README is explicitly written as chapters ("This README is a small book.
Read it front to back for the whole story"), and the website mirrors it in 11
sections:

| Section | Pages | What it covers |
|---|---:|---|
| `rust/` | 15 | the gpui-style Rust API, HTML/CSS, hooks, tables, headless testing |
| `concepts/` | 9 | how it works, rendering, damage rendering, Blender widgets, text, theming, images, video, window hosts |
| `project/` | 7 | status, roadmap, FAQ, contributing, coverage |
| `tutorials/` | 7 | one "first app" per language: Python, tkinter, Qt, Rust, React, C, Dear ImGui |
| `imgui/` | 6 | the Dear ImGui integration |
| `javascript/` | 5 | React, Svelte, the native DOM API |
| `python/` | 5 | tkinter compat, Qt syntax, components |
| `reference/` | 6 | env vars, CMake options, platforms, binary size, coverage, glossary |
| `performance/` | 3 | benchmarks, profiling, how to run them |
| `start/` | 2 | installation, introduction |
| `c/` | 2 | the C kit API and embedding |

The organising principle is **audience and port of entry**: you can arrive as a
Python/tkinter user, a React developer, a Rust developer or a C embedder, and
each has a tutorial, a guide and a reference.

Every page carries front-matter naming its sources, for example
`performance/run-benchmarks.mdx`:

```yaml
sources: ["README.md", "bindings/rust/bench/README.md", "bench/run.py",
          "bindings/rust/bench/common/measure.rs", "bench/python/..."]
```

That is a documentation-honesty device worth stealing: each page declares which
source files claim what it claims, so drift is detectable.

### GPUI: doc comments and the Zed source

GPUI's approach is the opposite. Its README is 66 lines: what it is, how to build
it on macOS, and an orientation paragraph pointing at three "registers"
(entities, views, elements) with module names. Then this:

> Currently, the best way to learn about these APIs is to read the Zed source
> code, ask us about it at a fireside hack, or drop a question in the Zed
> Discord. We're working on improving the documentation, creating more examples,
> and will be publishing more guides to GPUI on our blog.

The 28 examples are the real teaching material, and the source carries substantial
doc comments (5,742 lines). One file is documentation-as-code:
`src/_ownership_and_data_flow.rs` — a `.rs` file whose content is a prose essay on
GPUI's data model, listed in the README as the place to start.

### Side by side

| | BUI | GPUI |
|---|---|---|
| Primary learning path | read the docs | read the examples, then the source |
| Doc-comment style | short, usage-oriented; heavy on behaviour ("drag with a hidden, continuous cursor") | explanatory, type-oriented; explains *why* the API is shaped that way |
| Works without reading source? | yes | substantially no |
| Works without a browser/site? | yes (`docs/` is in the repo) | yes, but to a shallow depth |
| Onboarding for a new language | per-language tutorial | n/a (Rust only) |
| Says what is missing | yes, explicitly (see §4) | yes (pre-1.0 warning, "we're improving docs") |
| Performance claims documented | in detail, with a page on running them | not documented in the crate |

---

## 3. Quality, not just quantity

Volume is easy to fake, so here is what the documentation actually *does* well in
each case.

### BUI's strongest documentation

**1. It documents its own trade-offs.** The README states plainly: "the known
limitations: no accessibility support yet, no input methods, and it looks like
Blender, not like your operating system." A project that tells you where it is
weak is easier to trust about where it is strong. §41 then expands it: "BUI draws
its own widgets and does not talk to the platform's accessibility APIs (UI
Automation on Windows, AT-SPI on Linux…)".

**2. It documents the Linux threading limitation**, which is the single biggest
performance caveat of its CPU raster. Three separate pages say it:

> `reference/environment-variables.mdx`: `BUI_RASTER_THREADS` … "Windows: the most
> threads the software raster uses for big canvases. … **Elsewhere, canvases draw
> on one thread.**"

> `performance/profiling.mdx`: "On Windows, canvases with 64 or more items draw in
> parallel bands … **On Linux and macOS the canvas draws on one thread.**"

That is exactly the finding this repository measured independently. BUI's
documentation is accurate about it — the confusion only arises because the
README's headline benchmark numbers come from Windows.

**3. It explains how rendering works rather than just what to call.** The damage
rendering page, the parallel-raster page and the "CPU or GPU" page together let
you predict *why* a slow frame happened, not just observe that it did.

**4. It documents the benchmark methodology**, including the traps. From
`performance/run-benchmarks.mdx`:

> "An earlier version used `GetProcessTimes`. Windows charges that per ~15.6 ms
> clock tick, which aliases with a 60 Hz frame loop and badly under-reported CPU:
> gpui at 1,000 cells showed 6.3 ms per frame when it really used 19 ms. Every
> published number uses the cycle counter."

This repo independently hit the same class of bug (see `REUSING.md` §6). BUI
publishing it is a genuinely useful contribution.

**5. Each performance page names the machine it was measured on**, down to the
CPU, GPU, Mesa version, display refresh rate and power state — and warns "compare
the shape of the results, not single numbers."

### GPUI's strongest documentation

**1. The doc comments are excellent where they exist.** They explain design
intent. `Window::request_animation_frame` documents its scheduling contract; the
`Entity`/`Context` distinction is explained in terms of ownership, not just
signature.

**2. `_ownership_and_data_flow.rs`** is a clever pattern: a compilable file that is
mostly prose, so it cannot rot into a dead link or an outdated snippet — if the
API changes, the file stops compiling.

**3. The examples are broad and runnable.** 28 of them, 5,636 lines covering
animation, grids, drag and drop, data tables, gradients, GIF viewing, images,
shadows, painting, text and input. For a pre-1.0 framework this is a better
learning surface than prose would be, because examples cannot silently disagree
with the compiler.

Worth noting, though: those 5,636 lines contain only **56 comment lines**. They
show *what* to write and leave *why* to the reader — which is the opposite of the
doc-comment style in `src/`, and means an example is a template to copy rather
than a lesson.

**4. It is honest about maturity** in the first paragraph: "still in active
development … still pre-1.0. There will often be breaking changes between
versions."

---

## 4. Where each falls short

**BUI**

- **The README is 2,303 lines.** As a landing page this is enormous; the website
  fixes it, but anyone reading the crate on GitHub or crates.io meets the wall
  first.
- **Number-heavy claims are front-loaded and Windows-based.** "2–4x less CPU per
  frame than gpui-fast" needs the caveat nearby that this is Direct3D 11 on
  Windows and that Linux draws single-threaded. The caveat exists, but three
  clicks away.
- **Accuracy of the Rust API docs trails the surface.** The crate exposes 406
  public functions with 1,903 doc-comment lines; gpui carries 5,742 doc-comment
  lines over 1,347 public functions. Per function BUI is comparable (4.7 lines
  against 4.3), but gpui's are more explanatory where they exist — BUI's tend to
  state behaviour, gpui's tend to explain design.
- **`docs/rust.md` is 774 lines**, and reads as a reference with 26 headings
  rather than a guided tour. It also carries changelog-style detail that will age
  ("Not built yet in blenderui: element cells … multi-cell ranges"), which is a
  maintenance risk in a document that is supposed to describe the current API.

**GPUI**

- **No guide-level documentation in the crate.** 133 lines of `docs/` for a
  framework with 1,347 public functions. Tutorials live on the website or in
  blog posts, which are outside the version you depend on.
- **No performance documentation at all.** Not a benchmark page, not a note on
  what rendering costs. For a GPU framework whose selling point is speed, this is
  the most conspicuous gap — and it is why this repository exists.
- **"Read the Zed source" is a high barrier.** Zed is a very large codebase; the
  relevant gpui usage is scattered across editor code, not isolated.
- **Breaking changes between minor versions** with no migration notes in the
  crate. API stability notes live in release announcements.
- **Platform documentation is macOS-heavy.** The README's dependency section is
  entirely Xcode instructions; Linux dependencies (xkbcommon, Vulkan, wayland
  headers) are undocumented, which is why `REUSING.md` and this repo's
  `third_party/` exist at all.

---

## 5. What this means practically

**If you are evaluating BUI**, the documentation will let you decide without
writing code. Start at the concepts pages, check the roadmap page for the
accessibility/IME gaps, and read `performance/benchmarks.mdx` for the machine
those numbers came from.

**If you are evaluating GPUI**, plan to read source. Budget time for it, and start
from the examples rather than the README. The `hello_world`, `animation` and
`grid_layout` examples answer most "how do I…" questions faster than any prose.

**If you are building on either**, BUI's per-page `sources:` front-matter and
GPUI's `_ownership_and_data_flow.rs` are both patterns worth copying into your own
project — the first keeps docs honest about their evidence, the second keeps docs
from rotting.

---

## 6. The gap that produced this repo

Neither project's documentation answers the question this repository asks, and
each is missing exactly half of it:

- **BUI documents its performance thoroughly but on Windows**, using Direct3D 11
  and its parallel raster. What happens on Linux — single-threaded canvas,
  OpenGL 3.3 GPU renderer — is described in prose but not quantified.
- **gpui documents no performance at all**, and its only published comparison
  numbers appear in *BUI's* benchmark.

So a Linux user choosing between them has no shared frame of reference. That is
the gap [`COMPARISON.md`](COMPARISON.md) fills: the same scene, the same
measurement code, both frameworks, one machine, with CPU *and* GPU cost reported
because either one alone can be gamed.

---

## 7. Reproducing the counts

```sh
# BUI
git clone --depth 1 https://github.com/ppmpreetham/BUI bui && cd bui
wc -l docs/*.md | tail -1                                  # 4354
wc -l README.md                                            # 2303
find website/src/content/docs -name '*.mdx' | wc -l        # 68
find . -name '*.md' -not -path '*/node_modules/*' -exec wc -l {} + | tail -1

# GPUI (from the published crate)
curl -sSL https://static.crates.io/crates/gpui/gpui-0.2.2.crate | tar xz
wc -l gpui-0.2.2/docs/*.md                                 # 133
wc -l gpui-0.2.2/README.md                                 # 66
ls gpui-0.2.2/examples/*.rs | wc -l                        # 28

# doc-comment density, either source tree
find <src> -name '*.rs' -exec cat {} + | wc -l             # total lines
find <src> -name '*.rs' -exec grep -h -E '^\s*//[/!]' {} + | wc -l
```

Numbers drift between releases. Both projects are pre-1.0 and actively changing
documentation — treat the ratios as the finding and the absolute counts as a
snapshot dated 2026-11-12.
