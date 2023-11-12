import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QUrl, Signal, Slot, QMargins, QPoint
from PySide6.QtGui import QCloseEvent, QIcon, QKeyEvent, QScreen, QPixmap, QPalette
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QDialog, QGridLayout, QLabel, QMainWindow, QScrollArea, QVBoxLayout, QHBoxLayout, QWidget, \
    QSizePolicy, QProgressBar, QLayout, QStatusBar, QTextEdit
from pydantic import PositiveInt, FilePath

from ..config import Config, PresentationConfig, SlideConfig
from ..logger import logger
from ..resources import *  # noqa: F403

WINDOW_NAME = "Manim Slides"


class PresentationSlide:
    def __init__(self, file: FilePath, rev_file: FilePath, thumbnail: FilePath, loop: bool = False,
                 auto_next: bool = False, notes: str = ""):
        self.thumbnail = thumbnail
        self.file = file
        self.rev_file = rev_file
        self.loop = loop
        self.auto_next = auto_next
        self.notes = notes


class SlideSequenceElement(QWidget):
    def __init__(self, scroll_parent, index, slide, selected, mp, last):
        super().__init__()
        self.mp = mp
        self.index = index
        self.slide = slide
        self.last = last
        self.__scroll_parent = scroll_parent
        self.__layout = QHBoxLayout()
        self.__index_label = QLabel()
        self.__img_label = QLabel()
        self.__loop_label = QLabel()
        self.__auto_play_label = QLabel()
        self.__progress = QProgressBar()

        self.__selected_palette = QPalette()
        self.__palette = QPalette()
        self.__selected_palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.yellow)
        self.__selected_palette.setColor(self.__index_label.foregroundRole(), Qt.GlobalColor.black)

        self.init_gui(index, slide, selected)

    def set_index(self, i):
        self.__index_label.setText(str(i))

    def set_selected(self, selected=True):
        self.setPalette(self.__selected_palette if selected else self.__palette)
        self.__progress.setVisible(selected)

        # self.mapTo(self.parent(), QPoint(0, 0))
        self.__scroll_parent.ensureWidgetVisible(self)

    def set_position(self, perchentage):
        self.__progress.setValue(perchentage)

    def init_gui(self, i, slide, s):
        self.setAutoFillBackground(True)
        self.set_index(i)

        indicators = QWidget()
        vl = QVBoxLayout()
        vl.addWidget(self.__index_label)

        if slide.auto_next:
            self.__auto_play_label.setText("A")

        if slide.loop:
            self.__auto_play_label.setText("L")

        vl.addWidget(self.__loop_label)
        vl.addWidget(self.__auto_play_label)
        indicators.setLayout(vl)

        preview = QWidget()
        l = QVBoxLayout()

        img = QPixmap(slide.thumbnail).scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
        self.__img_label.setPixmap(img)

        self.__img_label.setFixedWidth(img.width())
        self.__img_label.setFixedHeight(img.height())
        self.__progress.setVisible(False)
        self.__progress.setFixedHeight(8)
        self.__progress.setFixedWidth(img.width())
        self.__progress.setTextVisible(False)

        l.addWidget(self.__img_label)
        l.addWidget(self.__progress)
        l.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        l.setContentsMargins(QMargins(0, 0, 0, 0))
        preview.setLayout(l)

        self.__layout.addWidget(indicators, Qt.AlignmentFlag.AlignLeft)
        self.__layout.addWidget(preview, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setLayout(self.__layout)
        self.set_selected(s)
        self.__layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            play_index = (self.index + (1 if not self.last else 0)) if not self.slide.loop else self.index
            play_paused = not self.slide.loop
            self.mp.load_slide(play_index, play_paused, False, False)
            self.__progress.setValue(100)


class SlideList(QScrollArea):
    def __init__(self, *args, slides, mp, slide_index, **kwargs):
        super().__init__(*args, **kwargs)
        self.slides = slides
        self.active_slide = slide_index
        self.slide_list_elements = [SlideSequenceElement(self, i, s, i == self.active_slide, mp, i == len(self.slides) - 1) for i, s in
                                    enumerate(self.slides)]
        self.slide_list = QWidget(self)
        self.layout = QVBoxLayout(self.slide_list)
        for s in self.slide_list_elements:
            self.layout.addWidget(s)
        self.setWidget(self.slide_list)
        self.setFixedWidth(self.slide_list.width() + 24)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_active_slide(self, index):
        self.slide_list_elements[self.active_slide].set_selected(False)
        self.slide_list_elements[index].set_selected(True)
        self.active_slide = index

    def slide_play_position_updated(self, index, perchentage):
        index = max(min(index, len(self.slide_list_elements)), 0)
        self.slide_list_elements[index].set_position(perchentage)


class SlideInfo(QWidget):
    def __init__(self, slide, next_slide):
        super().__init__()

        self.__cur_slide_label = QLabel()
        self.__next_slide_label = QLabel()
        self.__cur_img = QPixmap()
        self.__next_img = QPixmap()

        self.__notes = QTextEdit()
        self.__layout = QVBoxLayout()

        self.init_gui()
        self.set_cur_slide(slide, next_slide)

    def init_gui(self):
        self.__cur_slide_label.setPixmap(self.__cur_img)
        self.__next_slide_label.setPixmap(self.__next_img)

        top_layout = QHBoxLayout()
        next_slide_layout = QVBoxLayout()
        next_slide = QWidget()
        next_slide_layout.addWidget(self.__next_slide_label)
        next_slide.setLayout(next_slide_layout)

        top_layout.addWidget(self.__cur_slide_label)
        top_layout.addWidget(next_slide)

        top = QWidget()
        top.setLayout(top_layout)
        self.__layout.addWidget(top)

        self.__notes.setReadOnly(True)
        self.__layout.addWidget(self.__notes)
        self.setLayout(self.__layout)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.__notes.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_cur_slide(self, slide, next_slide):
        self.__cur_img = QPixmap(slide.thumbnail).scaledToWidth(600, Qt.TransformationMode.SmoothTransformation)
        self.__cur_slide_label.setPixmap(self.__cur_img)
        self.__cur_slide_label.setFixedWidth(self.__cur_img.width())
        self.__cur_slide_label.setFixedHeight(self.__cur_img.height())
        self.__notes.setMarkdown(slide.notes)

        if next_slide is None:
            self.__next_img = QPixmap()
            self.__next_slide_label.setPixmap(self.__next_img)
            return

        self.__next_img = QPixmap(next_slide.thumbnail).scaledToWidth(380, Qt.TransformationMode.SmoothTransformation)
        self.__next_slide_label.setPixmap(self.__next_img)
        self.__next_slide_label.setFixedWidth(self.__next_img.width())
        self.__next_slide_label.setFixedHeight(self.__next_img.height())


class Info(QMainWindow):  # type: ignore[misc]
    def __init__(self, *args: Any, presenter_screen, slides, slide_load_signal, start_slide, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.slides = slides
        self.slide_load_signal = slide_load_signal
        self.slide_list_widget = SlideList(self, slides=self.slides, mp=self.parent().media_player, slide_index=start_slide)
        self.slide_info = SlideInfo(self.slides[start_slide], self.slides[start_slide + 1] if start_slide < len(self.slides) - 1 else None)

        w = QWidget()
        self.__layout = QGridLayout(self)
        self.__layout.addWidget(self.slide_list_widget, 0, 0)
        self.__layout.addWidget(self.slide_info, 0, 1)
        w.setLayout(self.__layout)
        self.setCentralWidget(w)

        self.slide_counter = QLabel()
        self.slide_counter.setText(f"0 of {len(self.slides)}")

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"Slides: {start_slide} of {len(self.slides)}")

        if presenter_screen is not None:
            self.setScreen(presenter_screen)
            self.move(presenter_screen.geometry().center())

        self.slide_load_signal.connect(self.on_slide_changed)
        self.parent().media_player.positionChanged.connect(self.position_changed)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setWindowTitle(f"{WINDOW_NAME} - Presenter View")
        self.show()

    @Slot()
    def position_changed(self, position):
        mp = self.parent().media_player
        index = mp.slide_index + (1 if not mp.playingForward else 0)
        perch = int((position / mp.duration())*100)
        self.slide_list_widget.slide_play_position_updated(index, 100 - perch if not mp.playingForward else perch)

    @Slot()
    def on_slide_changed(self):
        mp = self.parent().media_player
        cur_index = mp.slide_index
        if mp.position() == 0 and not mp.isPlaying():
            cur_index -= 1

        cur_index = max(cur_index, 0)

        self.status_bar.showMessage(f"Slides: {cur_index} of {len(self.slides)}")
        self.slide_list_widget.set_active_slide(cur_index)
        self.slide_info.set_cur_slide(self.slides[cur_index], self.slides[cur_index + 1] if cur_index < len(self.slides) - 1 else None)

    def keyPressEvent(self, arg__1):
        self.parent().keyPressEvent(arg__1)

    def closeEvent(self, arg__1):
        self.parent().close()


class PresentationPlayer(QMediaPlayer):
    def __init__(self, parent, aspect_ratio_mode, playback_rate, slides: List[PresentationSlide], slide_load_signal,
                 start_slide=0, start_paused=False, exit_after_last_slide=False):
        super().__init__(parent)
        self.video_player = QVideoWidget()
        self.video_player.setAspectRatioMode(aspect_ratio_mode)

        self.setVideoOutput(self.video_player)
        self.setPlaybackRate(playback_rate)
        self.slides = slides
        self.slide_index = start_slide
        self.slide_load_signal = slide_load_signal
        self.playingForward = True
        self.load_slide(self.slide_index, start_paused, False)
        self.mediaStatusChanged.connect(self.media_finished)
        self.exit_after_last_slide = exit_after_last_slide

    @Slot()
    def media_finished(self, status):
        """Executed when a transition is finished."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            print("Transition finished")

            # If we do not need to loop then ensure no looping on the player
            if not self.slides[self.slide_index].loop or not self.playingForward:
                self.setLoops(1)  # do not loop anymore

            # If the slide is set on auto_loop, then execute next callback if we weren't playing it in reverse.
            if self.slides[self.slide_index].auto_next and self.playingForward:
                return self.next()

            if self.slide_index == len(self.slides) - 1 and self.exit_after_last_slide:
                exit(0)

            if not self.playingForward and self.slides[self.slide_index].loop:
                return self.load_slide(self.slide_index, True, False)
            self.load_slide(self.slide_index + 1, True, False)

    def load_slide(self, index, paused=False, reversed=False, end=False):
        """Loads the i-th slide and updates the internal reference index"""
        if index >= len(self.slides):
            print("No more slides!")
            return
        if index < 0:
            print("No previous slides!")
            return

        slide = self.slides[index]
        self.slide_index = index
        self.playingForward = not reversed
        print(
            f"Slide {index} loaded, PAUSED={paused}, REVERSE={reversed}, LOOP={slide.loop}, AUTO_NEXT={slide.auto_next}")

        # Load the resource
        url = QUrl.fromLocalFile(slide.file if not reversed else slide.rev_file)
        self.setSource(url)

        # If the slide requires looping then set the looping method
        self.setLoops(-1 if slide.loop and not reversed else 1)

        if end:
            self.setPosition(self.duration())

        # If we need to prepare a slide in paused state then pause the player
        if paused:
            self.pause()
        else:
            self.play()
        self.slide_load_signal.emit()

    def next(self):
        if self.isPlayingForward() and not self.isLooping():
            # If we are going forward but not in a looping slide we jump to the end of the animation
            self.pause()
            self.setPosition(self.duration())
            return

        if self.isLooping():
            # If we are looping we can go to the next transition without pause
            return self.load_slide(self.slide_index + 1, False, False)

        if self.isPlayingBackward():
            # We are going from index+1 to index (index has already been decremented) so we can reset to index+1
            return self.load_slide(self.slide_index + 1, True, False)

        # We are not playing
        if self.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            # Media has finished, start directly the next transition because no one has prepared it paused
            return self.load_slide(self.slide_index + 1, False, False)

        # We are not playing but the media is not finished.
        if self.position() == 0:
            # Someone has already prepared the slide for us
            return self.load_slide(self.slide_index, False, False)

        if self.position() == self.duration():
            # No one loaded the slide for us, just do it.
            return self.load_slide(self.slide_index + 1, False, False)
        # Just keep playing
        self.play()

    def previous(self):
        if self.isPlaying():
            # If we are playing in a looping slide we will play the reverse of it from the current duration
            if self.slides[self.slide_index].loop:
                self.pause()
                rev_position = self.duration() - self.position()
                self.load_slide(self.slide_index, False, True)
                self.setPosition(rev_position)
                return

            # Every time we are playing something we are preparing this slide going forward paused.
            #  If we were going forward not looping, reset the transition to the beginning
            #  If we were looping reset the slide
            #  If we were already going backwards, skip transition and get ready for start
            return self.load_slide(self.slide_index, True, False)

        if self.slide_index > 0:
            # We are not playing
            if self.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
                # No one has preloaded the next transition so we are free to play the reverse and decrement
                # (if possible)
                self.load_slide(self.slide_index, False, True)
                self.slide_index -= 1
                return

            # Someone has already prepared the next slide and is not started. we are in reality to slide index - 1
            self.load_slide(self.slide_index - 1, False, True)
            self.slide_index -= 1
        else:
            print("no previous slide")

    def get_video_player(self):
        return self.video_player

    def isLooping(self):
        return self.isPlaying() and self.slides[self.slide_index].loop

    def isPlayingForward(self):
        return self.isPlaying() and self.playingForward

    def isPlayingBackward(self):
        return self.isPlaying() and not self.playingForward


def load_presentation(presentation_configs: List[PresentationConfig]):
    slides = []
    resolution = (0, 0)
    for p in presentation_configs:
        resolution = (max(p.resolution[0], resolution[0]), max(p.resolution[1], resolution[1]))
        for s in p.slides:
            slides.append(PresentationSlide(s.file, s.rev_file, s.thumbnail, s.loop, s.auto_next, s.notes))
    return slides, resolution


class Player(QMainWindow):
    slide_load_signal = Signal()

    def __init__(
            self,
            config: Config,
            presentation_configs: List[PresentationConfig],
            *,
            start_paused: bool = False,
            full_screen: bool = False,
            exit_after_last_slide: bool = False,
            hide_mouse: bool = False,
            aspect_ratio_mode: Qt.AspectRatioMode = Qt.KeepAspectRatio,
            slide_index: int = 0,
            screen: Optional[QScreen] = None,
            presenter_screen: Optional[QScreen] = None,
            presenter_window: bool = False,
            playback_rate: float = 1.0,
    ):
        super().__init__()

        # Wizard's config
        self.config = config

        self.slides, self.resolution = load_presentation(presentation_configs)
        self.setup_window(screen, full_screen, hide_mouse)
        self.media_player = PresentationPlayer(self, aspect_ratio_mode, playback_rate, self.slides,
                                               self.slide_load_signal,
                                               slide_index, start_paused, exit_after_last_slide)
        self.setCentralWidget(self.media_player.get_video_player())

        self.config.keys.NEXT.connect(self.next)
        self.config.keys.PREVIOUS.connect(self.prev)
        self.config.keys.FULL_SCREEN.connect(self.toggle_full_screen)
        self.config.keys.HIDE_MOUSE.connect(self.toggle_mouse)
        self.config.keys.PLAY_PAUSE.connect(self.toggle_play)
        self.dispatch = self.config.keys.dispatch_key_function()

        if presenter_window:
            self.info = Info(parent=self, presenter_screen=presenter_screen, slides=self.slides,
                             slide_load_signal=self.slide_load_signal, start_slide=slide_index)

    @Slot()
    def next(self):
        self.raise_()
        self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        self.activateWindow()
        self.media_player.next()

    @Slot()
    def prev(self):
        self.raise_()
        self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        self.activateWindow()
        self.media_player.previous()

    @Slot()
    def toggle_full_screen(self):
        if self.windowState() == Qt.WindowState.WindowFullScreen:
            self.setWindowState(Qt.WindowState.WindowNoState)
        else:
            self.setWindowState(Qt.WindowState.WindowFullScreen)

    @Slot()
    def toggle_mouse(self):
        if self.cursor() == Qt.CursorShape.BlankCursor:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.BlankCursor)

    def toggle_play(self):
        if self.media_player.isPlaying():
            self.media_player.pause()
        else:
            self.media_player.play()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        self.dispatch(key)
        event.accept()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.close()

    def setup_window(self, screen, full_screen, hide_mouse):
        if screen:
            self.setScreen(screen)
            self.move(screen.geometry().topLeft())

        w, h = self.resolution
        geometry = self.geometry()
        geometry.setWidth(w)
        geometry.setHeight(h)
        self.setGeometry(geometry)
        if full_screen:
            self.toggle_full_screen()

        if hide_mouse:
            self.toggle_mouse()

        self.setWindowTitle(WINDOW_NAME)
        self.setWindowIcon(QIcon(":/icon.png"))
