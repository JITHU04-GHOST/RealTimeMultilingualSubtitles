import sys, os, time, subprocess, threading
from PyQt5 import QtCore, QtGui, QtWidgets
import vlc

from resources import TEMP_AUDIO
from translator import translate
from asr_worker import ASRWorker


class VideoPlayer(QtWidgets.QWidget):
    caption = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.lang = "en"
        self.asr = None

        self.setWindowTitle("Real-Time Multilingual Subtitles")
        self.resize(1280, 720)

        self.vlc = vlc.Instance("--quiet")
        self.player = self.vlc.media_player_new()

        self.apply_theme()
        self.build_ui()

        if sys.platform.startswith("win"):
            self.player.set_hwnd(self.video_frame.winId())

        self.caption.connect(self.update_caption)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_seek)
        self.timer.start(100)

    # ------------------ UI THEME ---------------------

    def apply_theme(self):
        self.setStyleSheet("""
            QWidget { background-color: #101018; color: #e6e6e6; }
            QComboBox {
                background-color: #1c1c29;
                padding: 6px 10px;
                color: white;
                border: 1px solid #333344;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #2b2b3d;
                border-radius: 6px;
                padding: 6px 12px;
                color: white;
                border: 1px solid #3b3b4f;
            }
            QPushButton:hover { background-color: #3a3a52; }
            QSlider::groove:horizontal {
                height: 8px;
                background: #222233;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #00aaff;
                width: 16px;
                border-radius: 8px;
                margin: -4px 0;
            }
            QFrame#VideoPanel {
                background: black;
                border: 1px solid #2a2a3a;
                border-radius: 10px;
            }
        """)

    # ------------------ UI BUILD ---------------------

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Top bar
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Language:"))

        self.lang_box = QtWidgets.QComboBox()
        self.lang_box.addItems(["English", "Hindi", "Malayalam"])
        self.lang_box.currentIndexChanged.connect(
            lambda i: setattr(self, "lang", ["en", "hi", "ml"][i])
        )
        top.addWidget(self.lang_box)
        top.addStretch(1)
        layout.addLayout(top)

        # Video panel (stacked layout)
        self.video_container = QtWidgets.QFrame()
        self.video_container.setObjectName("VideoPanel")
        self.video_container.setMinimumHeight(500)

        self.stack = QtWidgets.QStackedLayout(self.video_container)

        # Video area
        self.video_frame = QtWidgets.QFrame()
        self.video_frame.setStyleSheet("background:black; border-radius:10px;")
        self.stack.addWidget(self.video_frame)

        # Subtitle overlay (floating)
        self.subtitle = QtWidgets.QLabel("", self.video_container)
        self.subtitle.setAlignment(QtCore.Qt.AlignCenter)
        self.subtitle.setStyleSheet("""
            background-color: rgba(0,0,0,150);
            color:white;
            padding: 10px 18px;
            font-size: 26px;
            border-radius: 8px;
        """)
        self.subtitle.setWordWrap(True)
        self.subtitle.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.subtitle.raise_()

        layout.addWidget(self.video_container, 1)

        # Controls
        controls = QtWidgets.QHBoxLayout()

        self.btn_play = QtWidgets.QPushButton("▶")
        self.btn_play.clicked.connect(self.toggle_play)
        controls.addWidget(self.btn_play)

        self.btn_restart = QtWidgets.QPushButton("↻")
        self.btn_restart.clicked.connect(self.restart_video)
        controls.addWidget(self.btn_restart)

        self.seek = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.seek.setRange(0, 1000)
        self.seek.sliderMoved.connect(self.seek_to)
        controls.addWidget(self.seek, 1)

        self.volume = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(60)
        self.volume.valueChanged.connect(lambda v: self.player.audio_set_volume(v))
        controls.addWidget(self.volume)

        btn_open = QtWidgets.QPushButton("OPEN VIDEO")
        btn_open.clicked.connect(self.open_video)
        controls.addWidget(btn_open)

        layout.addLayout(controls)

    # ------------------ CONTROL FUNCTIONS ---------------------

    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("⏸")

    def restart_video(self):
        self.player.stop()
        self.player.play()

    def seek_to(self, val):
        length = self.player.get_length()
        if length > 0:
            self.player.set_time(int((val/1000) * length))

    def update_seek(self):
        if self.player.is_playing():
            length = self.player.get_length()
            if length > 0:
                self.seek.setValue(int(self.player.get_time() / length * 1000))

        # Always reposition subtitle at bottom
        self.position_subtitle()

    def position_subtitle(self):
        w = self.video_container.width()
        h = self.video_container.height()
        sw, sh = self.subtitle.sizeHint().width(), self.subtitle.sizeHint().height()

        self.subtitle.setGeometry(
            int((w - sw) / 2),
            int(h - sh - 25),
            sw + 20,
            sh + 10
        )

    # ------------------ VIDEO + ASR ---------------------

    def open_video(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose Video", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.m4v)"
        )
        if not file:
            return

        print("Selected:", file)

        # Stop previous ASR
        if self.asr:
            self.asr.stop_flag = True
            self.asr = None

        # clean audio
        if os.path.exists(TEMP_AUDIO):
            try:
                os.remove(TEMP_AUDIO)
            except:
                print("Temp audio locked.")

        subprocess.run([
            "ffmpeg", "-i", file, "-vn", "-ac", "1", "-ar", "16000",
            "-y", TEMP_AUDIO
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        media = self.vlc.media_new(file)
        self.player.set_media(media)
        self.player.play()
        time.sleep(0.4)

        # Start ASR
        self.asr = ASRWorker(
            lambda: self.player.get_time()/1000,
            self.caption.emit,
            TEMP_AUDIO
        )
        self.asr.start()

    # ------------------ SUBTITLE UPDATE ---------------------

    def update_caption(self, cap):
        text = cap.get("text", "")
        if not text:
            return

        if self.lang == "en":
            self.subtitle.setText(text)
        else:
            def worker():
                translated = translate(text, self.lang)
                self.subtitle.setText(translated)
            threading.Thread(target=worker, daemon=True).start()
