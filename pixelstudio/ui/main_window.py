from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pixelstudio.core.renderer import PixelArtRenderer, RenderSettings
from pixelstudio.ui.image_view import ImageView


PRESETS: dict[str, dict[str, int | float | str]] = {
    "Detailed": {
        "width": 128,
        "colors": 48,
        "dither": "Floyd–Steinberg",
        "resize": "Balanced",
        "detail": 125,
        "contrast": 108,
        "saturation": 105,
        "cleanup": 1,
        "edges": 0,
    },
    "Retro Game": {
        "width": 64,
        "colors": 16,
        "dither": "Floyd–Steinberg",
        "resize": "Sharp",
        "detail": 150,
        "contrast": 120,
        "saturation": 110,
        "cleanup": 1,
        "edges": 25,
    },
    "Clean Sprite": {
        "width": 48,
        "colors": 12,
        "dither": "None",
        "resize": "Sharp",
        "detail": 145,
        "contrast": 112,
        "saturation": 105,
        "cleanup": 2,
        "edges": 15,
    },
    "Neon": {
        "width": 96,
        "colors": 24,
        "dither": "Floyd–Steinberg",
        "resize": "Balanced",
        "detail": 135,
        "contrast": 132,
        "saturation": 165,
        "cleanup": 1,
        "edges": 15,
    },
    "Horror": {
        "width": 72,
        "colors": 14,
        "dither": "Floyd–Steinberg",
        "resize": "Balanced",
        "detail": 130,
        "contrast": 145,
        "saturation": 55,
        "cleanup": 1,
        "edges": 35,
    },
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pixel Art Studio 0.1")
        self.resize(1280, 760)
        self.setMinimumSize(960, 620)
        self.setAcceptDrops(True)

        self._settings_store = QSettings("Brianski", "PixelArtStudio")
        self._renderer = PixelArtRenderer()
        self._source: Image.Image | None = None
        self._result: Image.Image | None = None
        self._source_path: Path | None = None
        self._updating_controls = False

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(180)
        self._render_timer.timeout.connect(self.render_image)

        self._build_toolbar()
        self._build_ui()
        self._apply_style()
        self._restore_window_state()
        self._update_enabled_state()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_action = QAction("Open Image", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_image_dialog)
        toolbar.addAction(open_action)

        self.save_action = QAction("Export PNG", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.export_image_dialog)
        toolbar.addAction(self.save_action)

        toolbar.addSeparator()

        reset_action = QAction("Reset Preset", self)
        reset_action.triggered.connect(lambda: self.apply_preset("Detailed"))
        toolbar.addAction(reset_action)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(14)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)

        preview_container = QWidget()
        preview_layout = QHBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(12)

        self.original_view = ImageView(
            "Original",
            "Drop an image here\nor press Ctrl+O",
        )
        self.result_view = ImageView(
            "Pixel Art",
            "Your rendered image will appear here",
        )
        preview_layout.addWidget(self.original_view, 1)
        preview_layout.addWidget(self.result_view, 1)
        splitter.addWidget(preview_container)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        controls_scroll.setMinimumWidth(300)
        controls_scroll.setMaximumWidth(360)

        controls = QWidget()
        controls_scroll.setWidget(controls)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(8, 0, 4, 8)
        controls_layout.setSpacing(14)

        controls_layout.addWidget(self._heading("Style"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESETS.keys())
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        controls_layout.addWidget(self.preset_combo)

        controls_layout.addWidget(self._heading("Pixel Canvas"))
        size_form = QFormLayout()
        size_form.setSpacing(10)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(8, 1024)
        self.width_spin.setValue(128)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self._width_changed)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(8, 1024)
        self.height_spin.setValue(128)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self._control_changed)

        self.lock_aspect = QCheckBox("Lock source aspect ratio")
        self.lock_aspect.setChecked(True)
        self.lock_aspect.toggled.connect(self._aspect_lock_changed)

        self.colors_spin = QSpinBox()
        self.colors_spin.setRange(2, 256)
        self.colors_spin.setValue(48)
        self.colors_spin.valueChanged.connect(self._control_changed)

        self.export_scale_combo = QComboBox()
        self.export_scale_combo.addItems(["1×", "2×", "4×", "8×", "16×"])
        self.export_scale_combo.setCurrentText("4×")
        self.export_scale_combo.currentTextChanged.connect(self._update_output_label)

        size_form.addRow("Width", self.width_spin)
        size_form.addRow("Height", self.height_spin)
        size_form.addRow("Colors", self.colors_spin)
        size_form.addRow("Export scale", self.export_scale_combo)
        controls_layout.addLayout(size_form)
        controls_layout.addWidget(self.lock_aspect)

        controls_layout.addWidget(self._heading("Renderer"))
        renderer_form = QFormLayout()
        renderer_form.setSpacing(10)

        self.dither_combo = QComboBox()
        self.dither_combo.addItems(["Floyd–Steinberg", "None"])
        self.dither_combo.currentTextChanged.connect(self._control_changed)

        self.resize_combo = QComboBox()
        self.resize_combo.addItems(["Balanced", "Sharp", "Smooth"])
        self.resize_combo.currentTextChanged.connect(self._control_changed)

        self.cleanup_spin = QSpinBox()
        self.cleanup_spin.setRange(0, 4)
        self.cleanup_spin.setValue(1)
        self.cleanup_spin.valueChanged.connect(self._control_changed)

        renderer_form.addRow("Dithering", self.dither_combo)
        renderer_form.addRow("Downscale", self.resize_combo)
        renderer_form.addRow("Cleanup passes", self.cleanup_spin)
        controls_layout.addLayout(renderer_form)

        self.detail_slider, self.detail_value = self._add_slider(
            controls_layout, "Detail", 0, 300, 125, "%"
        )
        self.contrast_slider, self.contrast_value = self._add_slider(
            controls_layout, "Contrast", 10, 300, 108, "%"
        )
        self.saturation_slider, self.saturation_value = self._add_slider(
            controls_layout, "Saturation", 0, 300, 105, "%"
        )
        self.edge_slider, self.edge_value = self._add_slider(
            controls_layout, "Edge ink", 0, 100, 0, "%"
        )

        self.generate_button = QPushButton("Generate Pixel Art")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.clicked.connect(self.render_image)
        controls_layout.addWidget(self.generate_button)

        self.output_label = QLabel("Output: —")
        self.output_label.setObjectName("mutedText")
        controls_layout.addWidget(self.output_label)
        controls_layout.addStretch(1)

        splitter.addWidget(controls_scroll)
        splitter.setSizes([920, 330])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

    @staticmethod
    def _heading(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionHeading")
        return label

    def _add_slider(
        self,
        parent_layout: QVBoxLayout,
        label_text: str,
        minimum: int,
        maximum: int,
        value: int,
        suffix: str,
    ) -> tuple[QSlider, QLabel]:
        row = QHBoxLayout()
        label = QLabel(label_text)
        value_label = QLabel(f"{value}{suffix}")
        value_label.setMinimumWidth(48)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(value_label)
        parent_layout.addLayout(row)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(
            lambda current, target=value_label, unit=suffix: self._slider_changed(
                target, current, unit
            )
        )
        parent_layout.addWidget(slider)
        return slider, value_label

    def _slider_changed(self, label: QLabel, value: int, suffix: str) -> None:
        label.setText(f"{value}{suffix}")
        self._control_changed()

    def _control_changed(self, *_args) -> None:
        if self._updating_controls:
            return
        self.preset_combo.setCurrentIndex(-1)
        self._update_output_label()
        if self._source is not None:
            self._render_timer.start()

    def _width_changed(self, *_args) -> None:
        if self._updating_controls:
            return
        if self.lock_aspect.isChecked() and self._source is not None:
            ratio = self._source.height / self._source.width
            height = max(8, min(1024, round(self.width_spin.value() * ratio)))
            self._updating_controls = True
            self.height_spin.setValue(height)
            self._updating_controls = False
        self._control_changed()

    def _aspect_lock_changed(self, checked: bool) -> None:
        self.height_spin.setEnabled(not checked)
        if checked:
            self._width_changed()

    def apply_preset(self, name: str) -> None:
        preset = PRESETS.get(name)
        if not preset:
            return

        self._updating_controls = True
        try:
            self.width_spin.setValue(int(preset["width"]))
            self.colors_spin.setValue(int(preset["colors"]))
            self.dither_combo.setCurrentText(str(preset["dither"]))
            self.resize_combo.setCurrentText(str(preset["resize"]))
            self.detail_slider.setValue(int(preset["detail"]))
            self.contrast_slider.setValue(int(preset["contrast"]))
            self.saturation_slider.setValue(int(preset["saturation"]))
            self.cleanup_spin.setValue(int(preset["cleanup"]))
            self.edge_slider.setValue(int(preset["edges"]))
        finally:
            self._updating_controls = False

        if self.lock_aspect.isChecked() and self._source is not None:
            ratio = self._source.height / self._source.width
            self.height_spin.setValue(
                max(8, min(1024, round(self.width_spin.value() * ratio)))
            )
        self._update_output_label()
        if self._source is not None:
            self._render_timer.start()

    def open_image_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All files (*.*)",
        )
        if path:
            self.load_image(Path(path))

    def load_image(self, path: Path) -> None:
        try:
            with Image.open(path) as opened:
                source = opened.convert("RGBA")
        except (OSError, UnidentifiedImageError) as error:
            QMessageBox.critical(self, "Could not open image", str(error))
            return

        self._source_path = path
        self._source = source
        self.original_view.set_image(source)
        self.setWindowTitle(f"Pixel Art Studio 0.1 — {path.name}")

        if self.lock_aspect.isChecked():
            ratio = source.height / source.width
            self._updating_controls = True
            self.height_spin.setValue(
                max(8, min(1024, round(self.width_spin.value() * ratio)))
            )
            self._updating_controls = False

        self._update_enabled_state()
        self.render_image()

    def render_image(self) -> None:
        if self._source is None:
            return

        settings = RenderSettings(
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            colors=self.colors_spin.value(),
            dither=(
                "floyd-steinberg"
                if self.dither_combo.currentText() == "Floyd–Steinberg"
                else "none"
            ),
            resize_mode=self.resize_combo.currentText().lower(),
            detail=self.detail_slider.value() / 100.0,
            contrast=self.contrast_slider.value() / 100.0,
            saturation=self.saturation_slider.value() / 100.0,
            cleanup_passes=self.cleanup_spin.value(),
            edge_strength=self.edge_slider.value() / 100.0,
        )

        try:
            self._result = self._renderer.render(self._source, settings)
        except Exception as error:  # Keep the GUI alive and report unexpected image errors.
            QMessageBox.critical(self, "Render failed", str(error))
            return

        preview_scale = max(1, min(12, 768 // max(self._result.size)))
        self.result_view.set_image(self._renderer.upscale(self._result, preview_scale))
        self._update_output_label()
        self._update_enabled_state()

    def export_image_dialog(self) -> None:
        if self._result is None:
            return

        default_name = "pixel-art.png"
        if self._source_path is not None:
            default_name = f"{self._source_path.stem}-pixel.png"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export pixel art",
            default_name,
            "PNG image (*.png)",
        )
        if not path:
            return

        export_path = Path(path)
        if export_path.suffix.lower() != ".png":
            export_path = export_path.with_suffix(".png")

        scale = self._export_scale()
        exported = self._renderer.upscale(self._result, scale)
        try:
            exported.save(export_path, format="PNG")
        except OSError as error:
            QMessageBox.critical(self, "Could not export image", str(error))
            return

        self.statusBar().showMessage(f"Saved {export_path}", 5000)

    def _export_scale(self) -> int:
        return int(self.export_scale_combo.currentText().replace("×", ""))

    def _update_output_label(self, *_args) -> None:
        if self._result is None:
            self.output_label.setText("Output: —")
            return
        scale = self._export_scale()
        self.output_label.setText(
            f"Pixel canvas: {self._result.width} × {self._result.height}\n"
            f"Export: {self._result.width * scale} × {self._result.height * scale} PNG"
        )

    def _update_enabled_state(self) -> None:
        has_source = self._source is not None
        self.generate_button.setEnabled(has_source)
        self.save_action.setEnabled(self._result is not None)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            suffix = Path(urls[0].toLocalFile()).suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls:
            self.load_image(Path(urls[0].toLocalFile()))
            event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._settings_store.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    def _restore_window_state(self) -> None:
        geometry = self._settings_store.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #111318;
                color: #e8eaf0;
                font-family: "Segoe UI";
                font-size: 10pt;
            }
            QToolBar {
                background: #171a21;
                border: none;
                border-bottom: 1px solid #2a2f3a;
                spacing: 6px;
                padding: 6px;
            }
            QToolButton, QPushButton {
                background: #252a35;
                border: 1px solid #353c4a;
                border-radius: 7px;
                padding: 8px 12px;
            }
            QToolButton:hover, QPushButton:hover {
                background: #303746;
            }
            QPushButton#primaryButton {
                background: #6657e8;
                border-color: #7c70f0;
                font-weight: 700;
                padding: 11px;
            }
            QPushButton#primaryButton:hover {
                background: #7568ee;
            }
            QLabel#viewTitle, QLabel#sectionHeading {
                font-size: 11pt;
                font-weight: 700;
            }
            QLabel#imageCanvas {
                background: #171a20;
                border: 1px solid #2b303a;
                border-radius: 10px;
                color: #7f8797;
            }
            QLabel#mutedText {
                color: #9299a8;
            }
            QComboBox, QSpinBox {
                background: #1b1f27;
                border: 1px solid #343a46;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QSlider::groove:horizontal {
                height: 5px;
                background: #2d3340;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8175f2;
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QScrollArea {
                background: transparent;
            }
            QSplitter::handle {
                background: #20242c;
                width: 2px;
            }
            """
        )
