import math
import random
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QImage, QPainter, QPen, QPixmap
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
class VectorLine:
    x1: float
    y1: float
    x2: float
    y2: float
    width: float = 1.0


class VectorEngine:
    MODE_HATCHING = "Hatching Sketch"
    MODE_CANNY = "Canny Contours"
    MODE_HOUGH = "Hough Lines"

    @staticmethod
    def preprocess(gray: np.ndarray, blur_sigma: float) -> np.ndarray:
        if blur_sigma <= 0:
            return gray
        k = max(3, int(blur_sigma * 6) | 1)
        return cv2.GaussianBlur(gray, (k, k), blur_sigma)

    @staticmethod
    def generate(
        image_bgr: np.ndarray,
        mode: str,
        blur_sigma: float,
        density: int,
        threshold: int,
        simplify: float,
        align_gradient: bool,
    ) -> List[VectorLine]:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        proc = VectorEngine.preprocess(gray, blur_sigma)

        if mode == VectorEngine.MODE_HATCHING:
            return VectorEngine._hatching(proc, density, threshold, simplify, align_gradient)
        if mode == VectorEngine.MODE_CANNY:
            return VectorEngine._canny_contours(proc, density, threshold, simplify)
        return VectorEngine._hough_lines(proc, density, threshold)

    @staticmethod
    def _hatching(
        gray: np.ndarray,
        density: int,
        threshold: int,
        simplify: float,
        align_gradient: bool,
    ) -> List[VectorLine]:
        h, w = gray.shape
        lines: List[VectorLine] = []

        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_angle = np.arctan2(gy, gx)

        base_spacing = max(4, int(26 - density // 4))
        line_len = max(6, int(12 + density // 2))
        noise_deg = 7.0

        hatch_angles = [0, 45, 90, 135]
        darkness_boost = np.clip((255 - gray).astype(np.float32) / 255.0, 0.0, 1.0)
        darkness_boost = np.power(darkness_boost, 1.2)

        rng = random.Random(12345)

        for y in range(base_spacing // 2, h, base_spacing):
            for x in range(base_spacing // 2, w, base_spacing):
                local = gray[max(0, y - 1):min(h, y + 2), max(0, x - 1):min(w, x + 2)]
                darkness = 1.0 - (float(np.mean(local)) / 255.0)
                if darkness < threshold / 255.0:
                    continue

                layers = int(np.clip(math.ceil(darkness * 4), 1, 4))
                layers += int(darkness > 0.75)
                layers = min(layers, 5)

                stroke_w = 0.8 + 0.8 * darkness
                d_mod = 0.8 + darkness_boost[y, x]

                for i in range(layers):
                    if align_gradient:
                        angle = grad_angle[y, x] + math.pi / 2.0 + math.radians(rng.uniform(-noise_deg, noise_deg))
                    else:
                        base_angle = hatch_angles[i % len(hatch_angles)]
                        angle = math.radians(base_angle + rng.uniform(-noise_deg, noise_deg))

                    local_len = line_len * (0.7 + d_mod * 0.6)
                    dx = math.cos(angle) * local_len * 0.5
                    dy = math.sin(angle) * local_len * 0.5

                    jitter = simplify * 0.15
                    jx = rng.uniform(-jitter, jitter)
                    jy = rng.uniform(-jitter, jitter)

                    x1 = np.clip(x - dx + jx, 0, w - 1)
                    y1 = np.clip(y - dy + jy, 0, h - 1)
                    x2 = np.clip(x + dx + jx, 0, w - 1)
                    y2 = np.clip(y + dy + jy, 0, h - 1)
                    lines.append(VectorLine(x1, y1, x2, y2, width=stroke_w))

        return lines

    @staticmethod
    def _canny_contours(gray: np.ndarray, density: int, threshold: int, simplify: float) -> List[VectorLine]:
        low = max(10, threshold)
        high = max(low + 10, density)
        edges = cv2.Canny(gray, low, high)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        lines: List[VectorLine] = []
        epsilon_scale = max(0.001, simplify / 100.0)

        for c in contours:
            if len(c) < 8:
                continue
            peri = cv2.arcLength(c, False)
            eps = epsilon_scale * peri
            approx = cv2.approxPolyDP(c, eps, False)
            pts = approx[:, 0, :]
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                lines.append(VectorLine(float(x1), float(y1), float(x2), float(y2), width=1.0))

        return lines

    @staticmethod
    def _hough_lines(gray: np.ndarray, density: int, threshold: int) -> List[VectorLine]:
        edges = cv2.Canny(gray, 50, 150)
        min_line_len = max(20, density)
        max_gap = max(2, threshold // 8)
        det = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=max(30, threshold),
            minLineLength=min_line_len,
            maxLineGap=max_gap,
        )

        lines: List[VectorLine] = []
        if det is not None:
            for l in det[:, 0, :]:
                x1, y1, x2, y2 = l.tolist()
                lines.append(VectorLine(float(x1), float(y1), float(x2), float(y2), width=1.1))

        return lines


class Worker(QObject):
    finished = pyqtSignal(list)

    @pyqtSlot(np.ndarray, str, float, int, int, float, bool)
    def process(self, image, mode, blur_sigma, density, threshold, simplify, align_gradient):
        lines = VectorEngine.generate(image, mode, blur_sigma, density, threshold, simplify, align_gradient)
        self.finished.emit(lines)


class ImagePanel(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.label = QLabel("Load an image to begin")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title = QLabel(title)
        self.title.setObjectName("panelTitle")

        lay = QVBoxLayout(self)
        lay.addWidget(self.title)
        lay.addWidget(self.label, 1)

        self.setObjectName("panel")

    def set_pixmap(self, pixmap: QPixmap):
        scaled = pixmap.scaled(self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        pm = self.label.pixmap()
        if pm:
            self.set_pixmap(pm)


class MainWindow(QMainWindow):
    triggerProcess = pyqtSignal(np.ndarray, str, float, int, int, float, bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vector Sketch Studio")
        self.resize(1400, 850)

        self.image_bgr: Optional[np.ndarray] = None
        self.vector_lines: List[VectorLine] = []

        self.worker_thread = QThread(self)
        self.worker = Worker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.triggerProcess.connect(self.worker.process)
        self.worker.finished.connect(self.on_processing_finished)

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(20)

        self.original_panel = ImagePanel("Original")
        self.preview_panel = ImagePanel("Vector Preview")

        left_wrap = QHBoxLayout()
        left_wrap.addWidget(self.original_panel, 1)
        left_wrap.addWidget(self.preview_panel, 1)

        canvas_card = QFrame()
        canvas_card.setObjectName("card")
        canvas_card.setLayout(left_wrap)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        form = QFormLayout(sidebar)
        form.setSpacing(12)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([VectorEngine.MODE_HATCHING, VectorEngine.MODE_CANNY, VectorEngine.MODE_HOUGH])

        self.blur_slider = self._slider(0, 60, 10)
        self.density_slider = self._slider(20, 200, 120)
        self.threshold_slider = self._slider(0, 255, 80)
        self.simplify_slider = self._slider(1, 100, 30)

        self.align_combo = QComboBox()
        self.align_combo.addItems(["Predefined Hatching Angles", "Align with Gradient"])

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

        for w in [self.mode_combo, self.blur_slider, self.density_slider, self.threshold_slider, self.simplify_slider, self.align_combo]:
            if isinstance(w, QSlider):
                w.valueChanged.connect(self.request_processing)
            else:
                w.currentIndexChanged.connect(self.request_processing)

        self.load_btn.clicked.connect(self.load_image)
        self.export_btn.clicked.connect(self.export_svg)

        main.addWidget(canvas_card, 3)
        main.addWidget(sidebar, 1)

        shadow = QGraphicsDropShadowEffect(blurRadius=30, xOffset=0, yOffset=10)
        shadow.setColor(Qt.GlobalColor.lightGray)
        canvas_card.setGraphicsEffect(shadow)

        act_open = QAction("Open", self)
        act_open.triggered.connect(self.load_image)
        self.addAction(act_open)

    def _slider(self, mi: int, ma: int, value: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(mi, ma)
        s.setValue(value)
        return s

    def _apply_style(self):
        self.setStyleSheet(
            """
            QMainWindow { background: #F5F7FB; }
            #card, #sidebar, #panel {
                background: white;
                border-radius: 16px;
                border: 1px solid #E8ECF2;
            }
            #sidebar { padding: 18px; }
            #panel { padding: 12px; }
            #panelTitle {
                color: #111827;
                font-weight: 600;
                font-size: 15px;
                padding-bottom: 8px;
            }
            QLabel { color: #4B5563; font-size: 13px; }
            QPushButton {
                background: #111827;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover { background: #1F2937; }
            QPushButton:disabled { background: #9CA3AF; }
            QComboBox, QSlider {
                background: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
                padding: 6px;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: #E5E7EB;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #111827;
                border: none;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            """
        )

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            QMessageBox.critical(self, "Error", "Unable to read image file.")
            return

        self.image_bgr = img
        self.original_panel.set_pixmap(self.cv_to_pixmap(img))
        self.request_processing()

    def request_processing(self):
        if self.image_bgr is None:
            return
        blur_sigma = self.blur_slider.value() / 10.0
        density = self.density_slider.value()
        threshold = self.threshold_slider.value()
        simplify = float(self.simplify_slider.value())
        mode = self.mode_combo.currentText()
        align_gradient = self.align_combo.currentIndex() == 1
        self.triggerProcess.emit(self.image_bgr.copy(), mode, blur_sigma, density, threshold, simplify, align_gradient)

    @pyqtSlot(list)
    def on_processing_finished(self, lines: List[VectorLine]):
        self.vector_lines = lines
        self.export_btn.setEnabled(len(lines) > 0)
        if self.image_bgr is None:
            return

        preview = np.full_like(self.image_bgr, 255)
        for ln in lines:
            cv2.line(
                preview,
                (int(ln.x1), int(ln.y1)),
                (int(ln.x2), int(ln.y2)),
                (0, 0, 0),
                thickness=max(1, int(round(ln.width))),
                lineType=cv2.LINE_AA,
            )
        self.preview_panel.set_pixmap(self.cv_to_pixmap(preview))

    def export_svg(self):
        if self.image_bgr is None or not self.vector_lines:
            return
        default_name = "vector_sketch.svg"
        path, _ = QFileDialog.getSaveFileName(self, "Export SVG", default_name, "SVG Files (*.svg)")
        if not path:
            return

        h, w = self.image_bgr.shape[:2]
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            '<g stroke="black" fill="none" stroke-linecap="round">',
        ]
        for ln in self.vector_lines:
            svg_lines.append(
                f'<line x1="{ln.x1:.2f}" y1="{ln.y1:.2f}" x2="{ln.x2:.2f}" y2="{ln.y2:.2f}" stroke-width="{ln.width:.2f}" />'
            )
        svg_lines.append("</g></svg>")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(svg_lines))

        QMessageBox.information(self, "Export Complete", f"SVG saved to:\n{path}")

    @staticmethod
    def cv_to_pixmap(img_bgr: np.ndarray) -> QPixmap:
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg.copy())

    def closeEvent(self, event):
        self.worker_thread.quit()
        self.worker_thread.wait(1500)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
