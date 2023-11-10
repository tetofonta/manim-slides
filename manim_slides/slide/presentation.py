__all__ = ["Presentation"]

import json
from pathlib import Path
from typing import List, Any, Type
from manim import Scene

from manim_slides.defaults import FOLDER_PATH
from manim_slides.slide import Slide


class Presentation(Scene):
    def __init__(self, *args, slides: List[Type[Slide]], output_path=FOLDER_PATH, name="presentation", **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.list = slides
        self.output_path = output_path
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def render(self, preview: bool = False):
        presentation_obj = {"root": self.output_path, "sequence": []}
        for SlideClass in self.list:
            presentation_obj["sequence"].append(SlideClass.__name__)
            SlideClass(*self.args, **self.kwargs).render(preview=preview)

        with open(Path(self.output_path, f"{self.name}.json"), "w") as out:
            out.write(json.dumps(presentation_obj))
