import math
import random
import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


@dataclass
class VectorPath:
    points: List[Tuple[float, float]]
    width: float = 1.0


class VectorEngine:
    MODE_HATCHING = "Hatching Sketch"
    MODE_CANNY = "Canny Contours"
    MODE_HOUGH = "Hough Lines"

    @staticmethod
    def preprocess(gray: np.ndarray, blur_sigma: float) -> np.ndarray:
        if blur_sigma <= 0:
            return gray
        kernel = max(3, int(blur_sigma * 6) | 1)
        return cv2.GaussianBlur(gray, (kernel, kernel), blur_sigma)

    @staticmethod
    def generate(
        image_bgr: np.ndarray,
        mode: str,
        blur_sigma: float,
        density: int,
        threshold: int,
        simplify: float,
        align_gradient: bool,
    ) -> List[VectorPath]:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        proc = VectorEngine.preprocess(gray, blur_sigma)
        if mode == VectorEngine.MODE_HATCHING:
            return VectorEngine._hatching(proc, density, threshold, simplify, align_gradient)
        if mode == VectorEngine.MODE_CANNY:
            return VectorEngine._canny_contours(proc, density, threshold, simplify)
        return VectorEngine._hough_lines(proc, density, threshold)

    @staticmethod
    def _streamline(
        x: float,
        y: float,
        angle_map: np.ndarray,
        length: int,
        step: float,
        width: int,
        height: int,
    ) -> List[Tuple[float, float]]:
        pts = [(x, y)]
        for direction in (1.0, -1.0):
            cx, cy = x, y
            branch = []
            for _ in range(length):
                ix, iy = int(np.clip(round(cx), 0, width - 1)), int(np.clip(round(cy), 0, height - 1))
                angle = float(angle_map[iy, ix])
                cx += direction * math.cos(angle) * step
                cy += direction * math.sin(angle) * step
                if cx < 0 or cy < 0 or cx >= width or cy >= height:
                    break
                branch.append((cx, cy))
            if direction > 0:
                pts.extend(branch)
            else:
                pts = branch[::-1] + pts
        return pts

    @staticmethod
    def _hatching(gray: np.ndarray, density: int, threshold: int, simplify: float, align_gradient: bool) -> List[VectorPath]:
        h, w = gray.shape
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_angle = np.arctan2(gy, gx) + np.pi / 2.0

        base_angles = [0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4]
        spacing = max(3, int(24 - density // 5))
        step = 1.5
        segments = max(4, int(6 + density // 20))
        darkness_threshold = threshold / 255.0
        noise = math.radians(5 + simplify * 0.08)
        rng = random.Random(7)

        paths: List[VectorPath] = []
        for y in range(spacing // 2, h, spacing):
            for x in range(spacing // 2, w, spacing):
                darkness = 1.0 - float(gray[y, x]) / 255.0
                if darkness <= darkness_threshold:
                    continue

                layers = min(5, 1 + int(darkness * 5))
                for i in range(layers):
                    if align_gradient:
                        angle_map = grad_angle + rng.uniform(-noise, noise)
                    else:
                        angle = base_angles[i % len(base_angles)] + rng.uniform(-noise, noise)
                        angle_map = np.full((h, w), angle, dtype=np.float32)

                    jitter = simplify * 0.1
                    sx = float(np.clip(x + rng.uniform(-jitter, jitter), 0, w - 1))
                    sy = float(np.clip(y + rng.uniform(-jitter, jitter), 0, h - 1))
                    pts = VectorEngine._streamline(sx, sy, angle_map, segments, step, w, h)
                    if len(pts) < 2:
                        continue

                    simplified = cv2.approxPolyDP(
                        np.array(pts, dtype=np.float32).reshape(-1, 1, 2),
                        epsilon=max(0.2, simplify * 0.03),
                        closed=False,
                    )
                    sp = [(float(p[0][0]), float(p[0][1])) for p in simplified]
                    if len(sp) > 1:
                        paths.append(VectorPath(sp, width=0.7 + darkness * 0.9))
        return paths

    @staticmethod
    def _canny_contours(gray: np.ndarray, density: int, threshold: int, simplify: float) -> List[VectorPath]:
        low = max(10, threshold)
        high = max(low + 20, threshold + density // 2)
        edges = cv2.Canny(gray, low, high)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        paths: List[VectorPath] = []
        for contour in contours:
            if len(contour) < 10:
                continue
            perimeter = cv2.arcLength(contour, closed=False)
            epsilon = max(0.3, (simplify / 120.0) * perimeter)
            approx = cv2.approxPolyDP(contour, epsilon, closed=False)
            points = [(float(p[0][0]), float(p[0][1])) for p in approx]
            if len(points) > 1:
                paths.append(VectorPath(points, width=1.0))
        return paths

    @staticmethod
    def _hough_lines(gray: np.ndarray, density: int, threshold: int) -> List[VectorPath]:
        edges = cv2.Canny(gray, 50, 160)
        detected = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=max(30, threshold),
            minLineLength=max(20, density),
            maxLineGap=max(3, threshold // 8),
        )
        paths: List[VectorPath] = []
        if detected is not None:
            for line in detected[:, 0, :]:
                x1, y1, x2, y2 = line.tolist()
                paths.append(VectorPath([(float(x1), float(y1)), (float(x2), float(y2))], width=1.1))
        return paths


class Worker(QObject):
    finished = pyqtSignal(list)

    @pyqtSlot(np.ndarray, str, float, int, int, float, bool)
    def process(self, image, mode, blur_sigma, density, threshold, simplify, align_gradient):
        self.finished.emit(VectorEngine.generate(image, mode, blur_sigma, density, threshold, simplify, align_gradient))


class ImagePanel(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.title = QLabel(title)
        self.title.setObjectName("panelTitle")
        self.label = QLabel("Load an image to begin")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.label, 1)
        self.setObjectName("panel")

    def set_pixmap(self, pixmap: QPixmap):
        scaled = pixmap.scaled(self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(scaled)


class MainWindow(QMainWindow):
    trigger_process = pyqtSignal(np.ndarray, str, float, int, int, float, bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vector Sketch Studio")
        self.resize(1400, 850)

        self.image_bgr: Optional[np.ndarray] = None
        self.vector_paths: List[VectorPath] = []

        self.worker_thread = QThread(self)
        self.worker = Worker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()
        self.trigger_process.connect(self.worker.process)
        self.worker.finished.connect(self.on_processing_finished)

        self.build_ui()
        self.apply_style()

    def slider(self, minimum: int, maximum: int, value: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(minimum, maximum)
        s.setValue(value)
        return s

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(20)

        self.original_panel = ImagePanel("Original")
        self.preview_panel = ImagePanel("Vector Preview")

        canvas_layout = QHBoxLayout()
        canvas_layout.addWidget(self.original_panel, 1)
        canvas_layout.addWidget(self.preview_panel, 1)

        canvas = QFrame()
        canvas.setObjectName("card")
        canvas.setLayout(canvas_layout)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        form = QFormLayout(sidebar)
        form.setSpacing(12)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([VectorEngine.MODE_HATCHING, VectorEngine.MODE_CANNY, VectorEngine.MODE_HOUGH])
        self.align_combo = QComboBox()
        self.align_combo.addItems(["Predefined Hatching Angles", "Align with Gradient"])

        self.blur_slider = self.slider(0, 60, 10)
        self.density_slider = self.slider(20, 220, 130)
        self.threshold_slider = self.slider(0, 255, 70)
        self.simplify_slider = self.slider(1, 100, 28)

        self.load_btn = QPushButton("Load Image")
        self.export_btn = QPushButton("Export SVG")
        self.export_btn.setEnabled(False)

        form.addRow("Mode", self.mode_combo)
        form.addRow("Blur Sigma", self.blur_slider)
        form.addRow("Density", self.density_slider)
        form.addRow("Threshold", self.threshold_slider)
        form.addRow("Simplicity", self.simplify_slider)
        form.addRow("Line Orientation", self.align_combo)
        form.addRow(self.load_btn)
        form.addRow(self.export_btn)

        for widget in [self.mode_combo, self.align_combo, self.blur_slider, self.density_slider, self.threshold_slider, self.simplify_slider]:
            if isinstance(widget, QSlider):
                widget.valueChanged.connect(self.request_processing)
            else:
                widget.currentIndexChanged.connect(self.request_processing)

        self.load_btn.clicked.connect(self.load_image)
        self.export_btn.clicked.connect(self.export_svg)

        main.addWidget(canvas, 3)
        main.addWidget(sidebar, 1)

        shadow = QGraphicsDropShadowEffect(blurRadius=30, xOffset=0, yOffset=10)
        shadow.setColor(Qt.GlobalColor.lightGray)
        canvas.setGraphicsEffect(shadow)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.load_image)
        self.addAction(open_action)

    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #F5F7FB; }
            #card, #sidebar, #panel {
                background: white;
                border-radius: 16px;
                border: 1px solid #E8ECF2;
            }
            #sidebar { padding: 18px; }
            #panel { padding: 12px; }
            #panelTitle { color: #111827; font-weight: 600; font-size: 15px; padding-bottom: 8px; }
            QLabel { color: #4B5563; font-size: 13px; }
            QPushButton {
                background: #111827; color: white; border: none; border-radius: 12px; padding: 10px 14px; font-weight: 600;
            }
            QPushButton:hover { background: #1F2937; }
            QPushButton:disabled { background: #9CA3AF; }
            QComboBox, QSlider { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 10px; padding: 6px; }
            QSlider::groove:horizontal { border: none; height: 6px; background: #E5E7EB; border-radius: 3px; }
            QSlider::handle:horizontal { background: #111827; border: none; width: 16px; margin: -5px 0; border-radius: 8px; }
        """)

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        image = cv2.imread(path)
        if image is None:
            QMessageBox.critical(self, "Error", "Unable to read image file.")
            return
        self.image_bgr = image
        self.original_panel.set_pixmap(self.cv_to_pixmap(image))
        self.request_processing()

    def request_processing(self):
        if self.image_bgr is None:
            return
        self.trigger_process.emit(
            self.image_bgr.copy(),
            self.mode_combo.currentText(),
            self.blur_slider.value() / 10.0,
            self.density_slider.value(),
            self.threshold_slider.value(),
            float(self.simplify_slider.value()),
            self.align_combo.currentIndex() == 1,
        )

    @pyqtSlot(list)
    def on_processing_finished(self, paths: List[VectorPath]):
        self.vector_paths = paths
        self.export_btn.setEnabled(bool(paths))
        if self.image_bgr is None:
            return
        preview = np.full_like(self.image_bgr, 255)
        for path in paths:
            pts = np.array(path.points, dtype=np.int32).reshape(-1, 1, 2)
            if len(pts) > 1:
                cv2.polylines(preview, [pts], isClosed=False, color=(0, 0, 0), thickness=max(1, int(round(path.width))), lineType=cv2.LINE_AA)
        self.preview_panel.set_pixmap(self.cv_to_pixmap(preview))

    def export_svg(self):
        if self.image_bgr is None or not self.vector_paths:
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Export SVG", "vector_sketch.svg", "SVG Files (*.svg)")
        if not save_path:
            return

        h, w = self.image_bgr.shape[:2]
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            '<g stroke="black" fill="none" stroke-linecap="round" stroke-linejoin="round">',
        ]
        for path in self.vector_paths:
            if len(path.points) < 2:
                continue
            d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in path.points)
            svg.append(f'<path d="{d}" stroke-width="{path.width:.2f}" fill="none" />')
        svg.append("</g></svg>")

        with open(save_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(svg))
        QMessageBox.information(self, "Export Complete", f"SVG saved to:\n{save_path}")

    @staticmethod
    def cv_to_pixmap(image_bgr: np.ndarray) -> QPixmap:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        h, w, channels = rgb.shape
        qimg = QImage(rgb.data, w, h, channels * w, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg.copy())

    def closeEvent(self, event):
        self.worker_thread.quit()
        self.worker_thread.wait(1500)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
