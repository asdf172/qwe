from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QAction
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Генератор трафаретов")
        self.resize(1200, 760)

        self.ornamental = OrnamentalGenerator()
        self.geometric = GeometricGenerator()
        self.silhouette = SilhouetteGenerator()
        self.current_geometry = None
        self.last_svg_path: Optional[Path] = None

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Main")
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

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems([t.value for t in StencilType])
        form.addRow("Тип:", self.type_combo)

        self.width_spin = QDoubleSpinBox(); self.width_spin.setRange(10, 2000); self.width_spin.setValue(200)
        self.height_spin = QDoubleSpinBox(); self.height_spin.setRange(10, 2000); self.height_spin.setValue(200)
        self.units_combo = QComboBox(); self.units_combo.addItems([Units.MM.value, Units.PX.value])
        self.bridge_spin = QDoubleSpinBox(); self.bridge_spin.setRange(0.5, 30); self.bridge_spin.setValue(2.0)
        self.scale_spin = QDoubleSpinBox(); self.scale_spin.setRange(0.1, 10); self.scale_spin.setValue(1.0)
        self.rot_spin = QDoubleSpinBox(); self.rot_spin.setRange(-360, 360)
        self.rep_spin = QSpinBox(); self.rep_spin.setRange(1, 100); self.rep_spin.setValue(6)
        self.spacing_spin = QDoubleSpinBox(); self.spacing_spin.setRange(1, 200); self.spacing_spin.setValue(20)
        self.cell_spin = QDoubleSpinBox(); self.cell_spin.setRange(2, 200); self.cell_spin.setValue(24)
        self.density_spin = QDoubleSpinBox(); self.density_spin.setRange(0.2, 3); self.density_spin.setSingleStep(0.1); self.density_spin.setValue(0.8)
        self.line_spin = QDoubleSpinBox(); self.line_spin.setRange(0.2, 10); self.line_spin.setValue(1)

        form.addRow("Ширина:", self.width_spin)
        form.addRow("Высота:", self.height_spin)
        form.addRow("Единицы:", self.units_combo)
        form.addRow("Мин. перемычка:", self.bridge_spin)
        form.addRow("Масштаб:", self.scale_spin)
        form.addRow("Угол:", self.rot_spin)
        form.addRow("Повторы:", self.rep_spin)
        form.addRow("Расстояние:", self.spacing_spin)
        form.addRow("Размер ячейки:", self.cell_spin)
        form.addRow("Плотность:", self.density_spin)
        form.addRow("Толщина линий:", self.line_spin)

        self.import_btn = QPushButton("Импорт PNG/JPG")
        self.import_btn.clicked.connect(self.import_image)
        left_layout.addLayout(form)
        left_layout.addWidget(self.import_btn)
        left_layout.addStretch()

        self.preview = QSvgWidget()
        self.preview.setMinimumWidth(700)

        layout.addWidget(left, 1)
        layout.addWidget(self.preview, 2)

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
            connected = validate_connectivity(geom, p.bridge_width)
            if not connected:
                QMessageBox.warning(self, "Предупреждение", "Часть островков не удалось полностью связать, результат будет экспортирован как есть.")

            self.current_geometry = geom
            self.refresh_preview()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Ошибка генерации: {exc}")

    def refresh_preview(self) -> None:
        if self.current_geometry is None:
            return
        canvas, _ = self._read_params()
        self.last_svg_path = export_stencil_svg(self.current_geometry, canvas.width, canvas.height, canvas.units.value, "stencil.svg")
        self.preview.load(str(self.last_svg_path))

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
        self.preview.load(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>")

    def import_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.silhouette.set_image(path)
            QMessageBox.information(self, "Импорт", f"Изображение загружено: {path}")
