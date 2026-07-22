from __future__ import annotations

from io import BytesIO

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


class ImageView(QWidget):
    def __init__(self, title: str, placeholder: str) -> None:
        super().__init__()
        self._image: Image.Image | None = None

        self.title_label = QLabel(title)
        self.title_label.setObjectName("viewTitle")

        self.image_label = QLabel(placeholder)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(280, 280)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.image_label.setObjectName("imageCanvas")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(self.image_label, 1)

    def set_image(self, image: Image.Image | None) -> None:
        self._image = image.copy() if image is not None else None
        self._refresh_pixmap()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._image is None:
            return

        buffer = BytesIO()
        self._image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")

        available = self.image_label.size()
        scaled = pixmap.scaled(
            available,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.image_label.setPixmap(scaled)
