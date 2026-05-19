from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPainter
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from generators.geometric import GeometricGenerator
from generators.ornamental import OrnamentalGenerator
from generators.silhouette import SilhouetteGenerator
from svg_export.exporter import export_stencil_svg
from utils.models import CanvasParams, GenerationParams, StencilType, Units
from utils.topology import ensure_connected, validate_connectivity


class SvgPreview(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.svg_item: Optional[QGraphicsSvgItem] = None

    def load_svg(self, path: str) -> None:
        """Load SVG into scene.

        Important: use file-backed QGraphicsSvgItem(path) to avoid renderer lifecycle
        issues that can crash the app when a temporary QSvgRenderer is garbage-collected.
        """
        self.scene_obj.clear()
        item = QGraphicsSvgItem(path)
        self.scene_obj.addItem(item)
        self.scene_obj.setSceneRect(item.boundingRect())
        self.svg_item = item
        self.fit_to_screen()

    def fit_to_screen(self) -> None:
        if self.scene_obj.items():
            self.fitInView(self.scene_obj.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Генератор трафаретов")
        self.resize(1350, 850)

        self.ornamental = OrnamentalGenerator()
        self.geometric = GeometricGenerator()
        self.silhouette = SilhouetteGenerator()
        self.current_geometry = None
        self.last_svg_path: Optional[Path] = None

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        create_action = QAction("Создать", self)
        create_action.triggered.connect(self.generate_stencil)
        toolbar.addAction(create_action)

        preview_action = QAction("Обновить предпросмотр", self)
        preview_action.triggered.connect(self.refresh_preview)
        toolbar.addAction(preview_action)

        export_action = QAction("Экспорт SVG", self)
        export_action.triggered.connect(self.export_svg)
        toolbar.addAction(export_action)

        clear_action = QAction("Очистить", self)
        clear_action.triggered.connect(self.clear_scene)
        toolbar.addAction(clear_action)

        toolbar.addSeparator()
        zoom_in = QAction("+", self)
        zoom_in.triggered.connect(lambda: self.preview.scale(1.2, 1.2))
        zoom_out = QAction("-", self)
        zoom_out.triggered.connect(lambda: self.preview.scale(1 / 1.2, 1 / 1.2))
        fit_action = QAction("Fit", self)
        fit_action.triggered.connect(lambda: self.preview.fit_to_screen())
        toolbar.addAction(zoom_in)
        toolbar.addAction(zoom_out)
        toolbar.addAction(fit_action)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter)

        panel = self._build_left_panel()
        panel.setMinimumWidth(360)
        self.preview = SvgPreview()

        splitter.addWidget(panel)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setStyleSheet(
            """
            QMainWindow { background: #20252b; }
            QLabel, QGroupBox { color: #e8edf2; }
            QGroupBox { border: 1px solid #4c5663; border-radius: 8px; margin-top: 10px; padding: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QFrame#LeftPanel { background: #2b313a; border-radius: 12px; }
            QToolBar { background: #303844; color: #fff; spacing: 6px; padding: 6px; }
            QComboBox, QSpinBox, QDoubleSpinBox, QPushButton { background: #3a424f; color: #fff; border: 1px solid #5d6878; border-radius: 6px; padding: 5px; }
            QPushButton:hover { background: #4a5566; }
            """
        )

    def _build_left_panel(self) -> QWidget:
        left = QFrame()
        left.setObjectName("LeftPanel")
        layout = QVBoxLayout(left)

        base_box = QGroupBox("Холст")
        base_form = QFormLayout(base_box)

        self.width_spin = QDoubleSpinBox(); self.width_spin.setRange(10, 2000); self.width_spin.setValue(200)
        self.height_spin = QDoubleSpinBox(); self.height_spin.setRange(10, 2000); self.height_spin.setValue(200)
        self.units_combo = QComboBox(); self.units_combo.addItems([Units.MM.value, Units.PX.value])
        self.line_spin = QDoubleSpinBox(); self.line_spin.setRange(0.2, 10); self.line_spin.setValue(1)
        base_form.addRow("Ширина:", self.width_spin)
        base_form.addRow("Высота:", self.height_spin)
        base_form.addRow("Единицы:", self.units_combo)
        base_form.addRow("Толщина линии:", self.line_spin)

        gen_box = QGroupBox("Генерация")
        gen_form = QFormLayout(gen_box)
        self.type_combo = QComboBox(); self.type_combo.addItems([t.value for t in StencilType])
        self.bridge_spin = QDoubleSpinBox(); self.bridge_spin.setRange(0.5, 30); self.bridge_spin.setValue(2.0)
        self.scale_spin = QDoubleSpinBox(); self.scale_spin.setRange(0.1, 10); self.scale_spin.setValue(1.0)
        self.rot_spin = QDoubleSpinBox(); self.rot_spin.setRange(-360, 360)
        self.rep_spin = QSpinBox(); self.rep_spin.setRange(1, 200); self.rep_spin.setValue(6)
        self.spacing_spin = QDoubleSpinBox(); self.spacing_spin.setRange(1, 200); self.spacing_spin.setValue(20)
        self.cell_spin = QDoubleSpinBox(); self.cell_spin.setRange(2, 200); self.cell_spin.setValue(24)
        self.density_spin = QDoubleSpinBox(); self.density_spin.setRange(0.2, 3); self.density_spin.setSingleStep(0.1); self.density_spin.setValue(0.8)

        gen_form.addRow("Тип:", self.type_combo)
        gen_form.addRow("Мин. перемычка:", self.bridge_spin)
        gen_form.addRow("Масштаб:", self.scale_spin)
        gen_form.addRow("Угол:", self.rot_spin)
        gen_form.addRow("Повторы:", self.rep_spin)
        gen_form.addRow("Расстояние:", self.spacing_spin)
        gen_form.addRow("Размер ячейки:", self.cell_spin)
        gen_form.addRow("Плотность:", self.density_spin)

        sil_box = QGroupBox("Силуэт")
        sil_layout = QVBoxLayout(sil_box)
        self.image_label = QLabel("Файл не выбран")
        self.import_btn = QPushButton("Импорт PNG/JPG")
        self.import_btn.clicked.connect(self.import_image)
        self.auto_btn = QPushButton("Автонастройка изображения")
        self.auto_btn.clicked.connect(self.auto_tune_image)
        sil_layout.addWidget(self.import_btn)
        sil_layout.addWidget(self.auto_btn)
        sil_layout.addWidget(self.image_label)

        layout.addWidget(base_box)
        layout.addWidget(gen_box)
        layout.addWidget(sil_box)
        layout.addStretch()
        return left

    def _read_params(self) -> tuple[CanvasParams, GenerationParams]:
        canvas = CanvasParams(
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            units=Units(self.units_combo.currentText()),
            line_thickness=self.line_spin.value(),
        )
        g = GenerationParams(
            stencil_type=StencilType(self.type_combo.currentText()),
            repeats=self.rep_spin.value(),
            spacing=self.spacing_spin.value(),
            rotation=self.rot_spin.value(),
            scale=self.scale_spin.value(),
            cell_size=self.cell_spin.value(),
            bridge_width=self.bridge_spin.value(),
            density=self.density_spin.value(),
        )
        return canvas, g

    def generate_stencil(self) -> None:
        try:
            canvas, p = self._read_params()
            if p.stencil_type == StencilType.ORNAMENTAL:
                geom = self.ornamental.generate(canvas, p)
            elif p.stencil_type == StencilType.GEOMETRIC:
                geom = self.geometric.generate(canvas, p)
            else:
                geom = self.silhouette.generate(canvas, p)

            geom = ensure_connected(geom, p.bridge_width)
            if not validate_connectivity(geom, p.bridge_width):
                QMessageBox.warning(self, "Предупреждение", "Не все островки удалось объединить идеально. Попробуйте увеличить ширину перемычки.")

            self.current_geometry = geom
            self.refresh_preview()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Ошибка генерации: {exc}")

    def refresh_preview(self) -> None:
        if self.current_geometry is None:
            return
        canvas, _ = self._read_params()
        self.last_svg_path = export_stencil_svg(self.current_geometry, canvas.width, canvas.height, canvas.units.value, "stencil.svg")
        self.preview.load_svg(str(self.last_svg_path))

    def export_svg(self) -> None:
        if self.current_geometry is None:
            QMessageBox.warning(self, "Внимание", "Сначала создайте трафарет.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт SVG", "stencil.svg", "SVG Files (*.svg)")
        if not path:
            return
        canvas, _ = self._read_params()
        export_stencil_svg(self.current_geometry, canvas.width, canvas.height, canvas.units.value, path)
        QMessageBox.information(self, "Готово", f"Файл сохранён: {path}")

    def clear_scene(self) -> None:
        self.current_geometry = None
        self.preview.scene_obj.clear()

    def import_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.silhouette.set_image(path)
            self.silhouette.auto_tune()
            self.image_label.setText(Path(path).name)
            QMessageBox.information(self, "Импорт", f"Изображение загружено и автонастроено: {path}")


    def auto_tune_image(self) -> None:
        try:
            self.silhouette.auto_tune()
            QMessageBox.information(self, "Автонастройка", "Параметры изображения автоматически настроены.")
        except Exception as exc:
            QMessageBox.warning(self, "Автонастройка", f"Не удалось автонастроить: {exc}")
