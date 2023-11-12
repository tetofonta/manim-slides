import json
import signal
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import click
from click import Context, Parameter
from pydantic import ValidationError
from PySide6.QtCore import Qt

from ..commons import config_path_option, folder_path_option, verbosity_option
from ..config import Config, PresentationConfig
from ..logger import logger
from ..qt_utils import qapp
from .player import Player

ASPECT_RATIO_MODES = {
    "keep": Qt.KeepAspectRatio,
    "ignore": Qt.IgnoreAspectRatio,
}


@click.command()
@folder_path_option
@click.help_option("-h", "--help")
@verbosity_option
def list_scenes(folder: Path) -> None:
    """List available scenes."""
    for i, scene in enumerate(_list_scenes(folder), start=1):
        click.secho(f"{i}: {scene}", fg="green")


def _list_scenes(folder: Path) -> List[str]:
    """List available scenes in given directory."""
    scenes = []

    for filepath in folder.glob("*.json"):
        try:
            _ = PresentationConfig.from_file(filepath)
            scenes.append(filepath.stem)
        except (
            Exception
        ) as e:  # Could not parse this file as a proper presentation config
            logger.warn(
                f"Something went wrong with parsing presentation config `{filepath}`: {e}"
            )

    logger.debug(f"Found {len(scenes)} valid scene configuration files in `{folder}`.")

    return scenes


def prompt_for_scenes(folder: Path) -> List[str]:
    """Prompt the user to select scenes within a given folder."""
    scene_choices = dict(enumerate(_list_scenes(folder), start=1))

    for i, scene in scene_choices.items():
        click.secho(f"{i}: {scene}", fg="green")

    click.echo()

    click.echo("Choose number corresponding to desired scene/arguments.")
    click.echo("(Use comma separated list for multiple entries)")

    def value_proc(value: Optional[str]) -> List[str]:
        indices = list(map(int, (value or "").strip().replace(" ", "").split(",")))

        if not all(0 < i <= len(scene_choices) for i in indices):
            raise click.UsageError("Please only enter numbers displayed on the screen.")

        return [scene_choices[i] for i in indices]

    if len(scene_choices) == 0:
        raise click.UsageError(
            "No scenes were found, are you in the correct directory?"
        )

    while True:
        try:
            scenes = click.prompt("Choice(s)", value_proc=value_proc)
            return scenes  # type: ignore
        except ValueError as e:
            raise click.UsageError(str(e)) from None


def get_scenes_presentation_config(
    scenes: List[str], folder: Path
) -> List[PresentationConfig]:
    """Return a list of presentation configurations based on the user input."""
    if len(scenes) == 0:
        scenes = prompt_for_scenes(folder)

    presentation_configs = []
    for scene in scenes:
        config_file = folder / f"{scene}.json"
        if not config_file.exists():
            raise click.UsageError(
                f"File {config_file} does not exist, check the scene name and make sure to use Slide as your scene base class"
            )
        try:
            presentation_configs.append(PresentationConfig.from_file(config_file))
        except ValidationError as e:
            raise click.UsageError(str(e)) from None

    return presentation_configs


def start_at_callback(
    ctx: Context, param: Parameter, values: str
) -> Tuple[Optional[int], ...]:
    if values == "(None, None)":
        return (None, None)

    def str_to_int_or_none(value: str) -> Optional[int]:
        if value.lower().strip() == "":
            return None
        else:
            try:
                return int(value)
            except ValueError:
                raise click.BadParameter(
                    f"start index can only be an integer or an empty string, not `{value}`",
                    ctx=ctx,
                    param=param,
                ) from None

    values_tuple = values.split(",")
    n_values = len(values_tuple)
    if n_values == 2:
        return tuple(map(str_to_int_or_none, values_tuple))

    raise click.BadParameter(
        f"exactly 2 arguments are expected but you gave {n_values}, please use commas to separate them",
        ctx=ctx,
        param=param,
    )


def get_screen(app, number: Optional[int]):
    if number is None:
        return None

    try:
        return app.screens()[number]
    except IndexError:
        logger.error(
            f"Invalid screen number {number}, "
            f"allowed values are from 0 to {len(app.screens()) - 1} (incl.)"
        )
        return None


@click.command()
@click.argument("scenes", nargs=-1)
@config_path_option
@folder_path_option
@click.option("--start-paused", is_flag=True, help="Start paused.")
@click.option(
    "-F",
    "--full-screen",
    "--fullscreen",
    "full_screen",
    is_flag=True,
    help="Toggle full screen mode.",
)
@click.option(
    "--exit-after-last-slide",
    is_flag=True,
    help="At the end of last slide, the application will be exited.",
)
@click.option(
    "-H",
    "--hide-mouse",
    is_flag=True,
    help="Hide mouse cursor.",
)
@click.option(
    "--aspect-ratio",
    type=click.Choice(["keep", "ignore"], case_sensitive=False),
    default="keep",
    help="Set the aspect ratio mode to be used when rescaling the video.",
    show_default=True,
)
@click.option(
    "--sa",
    "--start-at",
    "start_at",
    metavar="<SCENE,SLIDE>",
    type=str,
    callback=start_at_callback,
    default=(None, None),
    help="Start presenting at (x, y), equivalent to --sacn x --sasn y, "
    "and overrides values if not None.",
)
@click.option(
    "--sacn",
    "--start-at-scene-number",
    "start_at_scene_number",
    metavar="INDEX",
    type=int,
    default=0,
    help="Start presenting at a given scene number (0 is first, -1 is last).",
)
@click.option(
    "--sasn",
    "--start-at-slide-number",
    "start_at_slide_number",
    metavar="INDEX",
    type=int,
    default=0,
    help="Start presenting at a given slide number (0 is first, -1 is last).",
)
@click.option(
    "-S",
    "--screen",
    "screen_number",
    metavar="NUMBER",
    type=int,
    default=None,
    help="Present content on the given screen (a.k.a. display).",
)
@click.option(
    "-s",
    "--presenter-screen",
    "presenter_screen_number",
    metavar="NUMBER",
    type=int,
    default=None,
    help="Screen where to display the presenter window",
)
@click.option(
    "-p",
    "--presenter-window",
    "presenter_window",
    is_flag=True,
    help="Display presenter window",
)
@click.option(
    "--playback-rate",
    metavar="RATE",
    type=float,
    default=1.0,
    help="Playback rate of the video slides, see PySide6 docs for details.",
)
@click.option(
    "--presentation-file",
    "-P",
    "presentation_file",
    metavar="FILE",
    default=None,
    help="If set the the slide order will be read from the presentation file passed",
)
@click.help_option("-h", "--help")
@verbosity_option
def present(
    scenes: List[str],
    config_path: Path,
    folder: Path,
    start_paused: bool,
    full_screen: bool,
    exit_after_last_slide: bool,
    hide_mouse: bool,
    aspect_ratio: str,
    start_at: Tuple[Optional[int], Optional[int], Optional[int]],
    start_at_scene_number: int,
    start_at_slide_number: int,
    screen_number: Optional[int],
    playback_rate: float,
    presentation_file: str,
    presenter_screen_number: Optional[int],
    presenter_window: bool
) -> None:
    """
    Present SCENE(s), one at a time, in order.

    Each SCENE parameter must be the name of a Manim scene,
    with existing SCENE.json config file.

    You can present the same SCENE multiple times by repeating the parameter.

    Use ``manim-slide list-scenes`` to list all available
    scenes in a given folder.
    """

    if presentation_file:
        with open(presentation_file) as p:
            presentation = json.loads(p.read())
            folder = Path(presentation.get("root", "./slides"))
            scenes = presentation.get("sequence", [])

    presentation_configs = get_scenes_presentation_config(scenes, folder)

    if config_path.exists():
        try:
            config = Config.from_file(config_path)
        except ValidationError as e:
            raise click.UsageError(str(e)) from None
    else:
        logger.debug("No configuration file found, using default configuration.")
        config = Config()

    if start_at[0]:
        start_at_scene_number = start_at[0]

    if start_at[1]:
        start_at_slide_number = start_at[1]

    slide_index = start_at_slide_number + sum([len(x.slides) for x in presentation_configs[:start_at_scene_number]])
    if slide_index < 0:
        logger.error("First slide is number 0")
        exit(2)

    app = qapp()
    app.setApplicationName("Manim Slides")

    screen = get_screen(app, screen_number)
    presenter_screen = get_screen(app, presenter_screen_number)

    player = Player(
        config,
        presentation_configs,
        start_paused=start_paused,
        full_screen=full_screen,
        exit_after_last_slide=exit_after_last_slide,
        hide_mouse=hide_mouse,
        aspect_ratio_mode=ASPECT_RATIO_MODES[aspect_ratio],
        slide_index=slide_index,
        screen=screen,
        presenter_screen=presenter_screen,
        playback_rate=playback_rate,
        presenter_window=presenter_window
    )

    player.show()

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(app.exec())
