import sys
from PyQt5 import QtWidgets

print("Loading mBART-50 translation model (Hindi + Malayalam)…")
from translator import translate
print("Translator loaded!")

# Whisper is auto-loaded from asr_worker.py now

from player import VideoPlayer


def main():
    app = QtWidgets.QApplication(sys.argv)

    window = VideoPlayer()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
