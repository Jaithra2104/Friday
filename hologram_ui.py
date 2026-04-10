import sys
import math
import random
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QFont, QRadialGradient
)
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QGuiApplication


class HologramUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Smaller compact size
        self.setFixedSize(240, 300)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - 260, screen.height() - 330)

        self.rotation = 0
        self.pulse = 0
        self.state = "idle"

        self.full_text = ""
        self.display_text = ""
        self.text_index = 0

        # Micro particles
        self.particles = [
            random.uniform(0, 360)
            for _ in range(40)
        ]

        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    # ---------------- ANIMATION ----------------
    def animate(self):
        self.rotation += 2.2
        self.pulse += 0.12

        # Typewriter effect
        if self.text_index < len(self.full_text):
            self.text_index += 1
            self.display_text = self.full_text[:self.text_index]

        self.update()

    # ---------------- STATE ----------------
    def set_state(self, state):
        self.state = state

    def update_status(self, text):
        self.full_text = text
        self.display_text = ""
        self.text_index = 0

    # ---------------- DRAW ----------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = self.width() / 2
        center_y = 110

        # === Soft radial glow ===
        glow = QRadialGradient(center_x, center_y, 120)
        glow.setColorAt(0, QColor(0, 255, 255, 80))
        glow.setColorAt(1, QColor(0, 255, 255, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center_x - 120, center_y - 120, 240, 240)

        # === Ring Layer 1 ===
        painter.translate(center_x, center_y)
        painter.rotate(self.rotation)

        pen1 = QPen(QColor(0, 255, 255, 160))
        pen1.setWidth(2)
        painter.setPen(pen1)

        for i in range(0, 360, 20):
            painter.drawArc(QRectF(-70, -70, 140, 140), i * 16, 8 * 16)

        painter.resetTransform()

        # === Ring Layer 2 (reverse) ===
        painter.translate(center_x, center_y)
        painter.rotate(-self.rotation * 0.8)

        pen2 = QPen(QColor(0, 150, 255, 120))
        pen2.setWidth(2)
        painter.setPen(pen2)

        for i in range(0, 360, 30):
            painter.drawArc(QRectF(-90, -90, 180, 180), i * 16, 10 * 16)

        painter.resetTransform()

        # === Micro orbit particles ===
        painter.setPen(QPen(QColor(0, 255, 255, 200), 2))
        for angle in self.particles:
            rad = math.radians(angle + self.rotation)
            x = center_x + 100 * math.cos(rad)
            y = center_y + 100 * math.sin(rad)
            painter.drawPoint(x, y)

        # === Inner breathing core ===
        core_size = 25 + math.sin(self.pulse) * 4
        painter.setBrush(QBrush(QColor(0, 200, 255, 180)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            center_x - core_size,
            center_y - core_size,
            core_size * 2,
            core_size * 2
        )

        # === Speaking shock wave ===
        if self.state == "speaking":
            shock = 80 + math.sin(self.pulse * 5) * 12
            painter.setPen(QPen(QColor(255, 0, 255, 120), 2))
            painter.drawEllipse(
                center_x - shock,
                center_y - shock,
                shock * 2,
                shock * 2
            )

        # === Text Panel (Ultra Transparent) ===
        painter.setBrush(QColor(0, 255, 255, 25))
        painter.setPen(QPen(QColor(0, 255, 255, 90)))
        painter.drawRoundedRect(20, 180, self.width() - 40, 90, 12, 12)

        painter.setPen(QPen(QColor(0, 255, 255, 200)))
        painter.setFont(QFont("Consolas", 9))

        painter.drawText(
            30,
            190,
            self.width() - 60,
            80,
            Qt.TextWordWrap,
            self.display_text
        )

    # ---------------- DRAG ----------------
    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPosition().toPoint()