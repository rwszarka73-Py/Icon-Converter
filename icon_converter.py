import os
import platform
import subprocess
import sys

from PIL import Image, ImageFilter
from PyQt5.QtCore import QEvent, QStandardPaths, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

from icon_converter_ui import Ui_MainWindow

# The folder this program is in (also when published): files that ship with it are found from here
APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
APP_ICON = os.path.join(APP_DIR, "converter_icon.ico")

# Converted icons go to ~/Pictures/Icon Converter: always writable, also when installed in /opt
ICONS_DIR = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or os.path.expanduser("~/Pictures"),
    "Icon Converter")

IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".bmp")
ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


class IconConverter(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Window icon from the file next to the program (the form's Icon in PyStudio says the same)
        if os.path.exists(APP_ICON):
            self.setWindowIcon(QIcon(APP_ICON))

        # Track image path
        self.image_path = None

        # Enable drag and drop on the label
        self.imageLabel.setAcceptDrops(True)
        self.imageLabel.installEventFilter(self)

        # Connect Convert button
        self.convertButton.clicked.connect(self.convert_to_icon)

        # Output folder
        self.icons_dir = ICONS_DIR
        os.makedirs(self.icons_dir, exist_ok=True)

        # Menu items event trigger
        self.actionOpen_Icon_Folder.triggered.connect(self.open_icon_folder)
        self.actionExit.triggered.connect(self.close)
        self.statusbar.showMessage("Drop an image on the box to start.")

    def eventFilter(self, source, event):
        if source == self.imageLabel:
            if event.type() == QEvent.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                    return True
            elif event.type() == QEvent.Drop:
                if event.mimeData().hasUrls():
                    file_path = event.mimeData().urls()[0].toLocalFile()
                    if file_path.lower().endswith(IMAGE_TYPES):
                        self.image_path = file_path
                        pixmap = QPixmap(file_path)
                        # fit inside the drop box, keeping the image's proportions
                        self.imageLabel.setPixmap(pixmap.scaled(
                            self.imageLabel.width() - 24, self.imageLabel.height() - 24,
                            Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        self.statusbar.showMessage(
                            f"{os.path.basename(file_path)}  ·  {pixmap.width()} × {pixmap.height()}")
                    else:
                        self.statusbar.showMessage("That isn't a PNG, JPG or BMP image.", 5000)
                return True
        return super().eventFilter(source, event)

    def convert_to_icon(self):
        if not self.image_path:
            QMessageBox.warning(self, "Warning", "No image to convert.")
            return

        try:
            # Load image
            original_img = Image.open(self.image_path)

            # Convert to RGBA if needed (for transparency)
            if original_img.mode != 'RGBA':
                original_img = original_img.convert('RGBA')

            # Make image square by padding with transparency
            width, height = original_img.size
            if width != height:
                side = max(width, height)
                squared_img = Image.new('RGBA', (side, side), (0, 0, 0, 0))
                squared_img.paste(original_img, ((side - width) // 2, (side - height) // 2))
                original_img = squared_img

            # Sharpen original image for clarity
            original_img = original_img.filter(ImageFilter.SHARPEN)

            base_filename = os.path.splitext(os.path.basename(self.image_path))[0]

            if self.combineCheckbox.isChecked():
                # Save a single multi-size ICO with PNG compression (for better Linux + Windows previews)
                output_path = os.path.join(self.icons_dir, f"{base_filename}_multi.ico")
                original_img.save(
                    output_path,
                    format='ICO',
                    sizes=ICON_SIZES,
                    bitmap_format='png'  # This is the key for compatibility!
                )
                QMessageBox.information(self, "Success", f"✅ Multi-size high-quality icon saved:\n{output_path}")

            else:
                # Save individual ICO files per size, with sharpening
                for size in ICON_SIZES:
                    resized_img = original_img.resize(size, Image.LANCZOS)
                    resized_img = resized_img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
                    size_str = f"{size[0]}x{size[1]}"
                    output_path = os.path.join(self.icons_dir, f"{base_filename}_{size_str}.ico")
                    resized_img.save(output_path, format='ICO', sizes=[size])

                QMessageBox.information(self, "Success", f"✅ Individual icons saved:\n{self.icons_dir}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Conversion failed:\n{e}")

    def open_icon_folder(self):
        folder_path = self.icons_dir  # folder you want to open

        system = platform.system()

        try:
            if system == "Windows":
                os.startfile(folder_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux and other
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            print(f"❌ Could not open folder: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.exists(APP_ICON):
        app.setWindowIcon(QIcon(APP_ICON))
    window = IconConverter()
    window.show()
    sys.exit(app.exec_())
