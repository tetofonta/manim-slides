# Sharing your slides

Maybe one of the most important features is the ability to share your
presentation with other people, or even with yourself but on another computer!

There exists a variety of solutions, and all of them are exposed here.

We will go from the *most restrictive* method, to the least restrictive one.
If you need to present on a computer without prior knowledge on what will be
installed on it, please directly refer to the last sections.

> **NOTES:** in the next sections, we will assume your animations are described
in `example.py`, and you have one presentation called `BasicExample`.

## With Manim Slides installed on the target machine

If Manim Slides, Manim (or ManimGL), and their dependencies are installed, then
using `manim-slides present` allows for the best presentations, with the most
options available.

### Sharing your Python file(s)

The lightest way to share your presentation is with the Python files that
describe the slides.

If you have such files, you can recompile the animations locally, and use
`manim-slides present` for your presentation. You may want to copy / paste
you own `.manim-slides.json` config file, but it is **not recommended** if
you are sharing from one platform (e.g., Linux) to another (e.g., Windows) as
the key bindings might not be the same.

Example:

```bash
# If you use ManimGl, replace `manim` with `manimgl`
manim example.py BasicExample

# This or `manim-slides BasicExample` works since
# `present` is implied by default
manim-slides present BasicExample
```

### Sharing your animations files

If you do not want to recompile all the animations, you can simply share the
slides folder (defaults to `./slides`). Then, Manim Slides will be able to read
the animations from this folder and its subdirectories.

Example:

```bash
# Make sure that the slides directory is in the current
# working directory, or specify with `--folder <FOLDER>`
manim-slides present BasicExample
```

and the corresponding tree:

```
.
└── slides
    ├── BasicExample.json
    └── files
        └── BasicExample (files not shown)
```

## Without Manim Slides installed on the target machine

An alternative to `manim-slides present` is `manim-slides convert`.
Currently, only HTML conversion is available, but do not hesitate to propose
other formats by creating a
[Feature Request](https://github.com/jeertmans/manim-slides/issues/new/choose),
or directly proposing a
[Pull Request](https://github.com/jeertmans/manim-slides/compare).

A major advantage of HTML files is that they can be opened cross-platform,
granted one has a modern web browser (which is pretty standard).

### Sharing HTML and animation files

First, you need to create the HTML file and its assets directory.

Example:

```bash
manim-slides convert BasicExample basic_example.html
```

Then, you need to copy the HTML files and its assets directory to target location,
while keeping the relative path between the HTML and the assets the same. The
easiest solution is to compress both the file and the directory into one ZIP,
and to extract it to the desired location.

By default, the assets directory will be named after the main HTML file, using `{basename}_assets`.

Example:

```
.
├── basic_example_assets
│   ├── 1413466013_2261824125_223132457.mp4
│   ├── 1672018281_2145352439_3942561600.mp4
│   └── 1672018281_3136302242_2191168284.mp4
└── basic_example.html
```

Then, you can simply open the HTML file with any web browser application.

If you want to embed the presentation inside an HTML web page, a possibility is
to use an `iframe`:

```html
<div style="position:relative;padding-bottom:56.25%;">
    <!-- 56.25 comes from aspect ratio of 16:9, change this accordingly -->
    <iframe
        style="width:100%;height:100%;position:absolute;left:0px;top:0px;"
        frameborder="0"
        width="100%"
        height="100%"
        allowfullscreen
        allow="autoplay"
        src="basic_example.html">
    </iframe>
</div>
```

The additional code comes from
[this article](https://faq.dailymotion.com/hc/en-us/articles/360022841393-How-to-preserve-the-player-aspect-ratio-on-a-responsive-page)
and it there to preserve the original aspect ratio (16:9).


### Sharing ONE HTML file

A future feature, that will be available once
[#122](https://github.com/jeertmans/manim-slides/issues/122) is solved, will be
to include all animations as data URI encoded, within the HTML file itself.

### Over the internet

Finally, HTML conversion makes it convenient to play your presentation on a
remote server.

This is how your are able to watch all the examples on this website. If you want
to know how to share your slide with GitHub pages, see the
[workflow file](https://github.com/jeertmans/manim-slides/blob/main/.github/workflows/pages.yml).

> **WARNING:** keep in minde that playing large video files over the internet
can take some time, and *glitches* may occur between slide transitions for this
reason.