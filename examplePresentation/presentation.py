from examplePresentation.example import ConvertExample, ThreeDExample, BasicExample
from manim_slides.slide.presentation import Presentation


class MyPresentation(Presentation):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, **kwargs,
            slides=[
                ConvertExample,
                ThreeDExample,
                BasicExample,
            ],
            output_path="./slides"
        )

