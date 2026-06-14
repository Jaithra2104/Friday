"""
fullscreen_ui.py — Full-screen overlay for Friday.
Activated by voice ("show me on big screen") or maximize button.
Shows AI responses in large, beautifully formatted text.
"""
import sys
import math
import threading
from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QObject
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QLinearGradient, QRadialGradient, QPainterPath,
    QGuiApplication
)
from PySide6.QtWidgets import QWidget, QApplication


class _Signals(QObject):
    show_signal = Signal(str)
    hide_signal = Signal()


class FullscreenUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self._text = ""
        self._display_text = ""
        self._text_index = 0
        self._alpha = 0.0
        self._visible = False
        self._tick = 0
        self._pulse = 0.0
        self._close_hover = False

        # Typewriter + fade timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)

        # Thread-safe signals
        self._sig = _Signals()
        self._sig.show_signal.connect(self._do_show)
        self._sig.hide_signal.connect(self._do_hide)

        self.hide()

    # ── Public API (thread-safe) ────────────────────────────────────────────

    def show_response(self, text):
        """Call from any thread to display text in fullscreen mode."""
        self._sig.show_signal.emit(text)

    def hide_overlay(self):
        """Call from any thread to hide the overlay."""
        self._sig.hide_signal.emit()

    # ── Internal slots ──────────────────────────────────────────────────────

    def _do_show(self, text):
        self._text = text
        self._display_text = ""
        self._text_index = 0
        self._alpha = 0.0
        self._visible = True
        self.show()
        self.raise_()
        self.activateWindow()

    def _do_hide(self):
        self._visible = False
        self._alpha = 0.0
        self.hide()

    # ── Animation ───────────────────────────────────────────────────────────

    def _animate(self):
        if not self._visible:
            return

        self._tick += 1
        self._pulse += 0.05

        # Fade in
        if self._alpha < 1.0:
            self._alpha = min(1.0, self._alpha + 0.05)

        # Typewriter
        if self._text_index < len(self._text):
            # Type 2 chars per frame for speed
            self._text_index = min(len(self._text), self._text_index + 2)
            self._display_text = self._text[:self._text_index]

        self.update()

    # ── Paint ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if not self._visible:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setOpacity(self._alpha)

        W = self.width()
        H = self.height()
        cx = W // 2
        cy = H // 2

        # ── Background ──
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0,   QColor(0, 5, 20, 245))
        bg.setColorAt(0.5, QColor(0, 10, 30, 240))
        bg.setColorAt(1,   QColor(0, 5, 20, 245))
        painter.setBrush(bg)
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, W, H)

        # ── Ambient glow (center) ──
        glow = QRadialGradient(cx, cy, W * 0.45)
        glow.setColorAt(0, QColor(0, 150, 255, 18))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.drawEllipse(cx - W // 2, cy - W // 2, W, W)

        # ── Animated top line ──
        line_alpha = int(120 + math.sin(self._pulse) * 60)
        painter.setPen(QPen(QColor(0, 200, 255, line_alpha), 1))
        painter.drawLine(80, 60, W - 80, 60)

        # ── FRIDAY label ──
        painter.setFont(QFont("Consolas", 11, QFont.Bold))
        painter.setPen(QColor(0, 200, 255, 180))
        painter.drawText(QRectF(0, 25, W, 30), Qt.AlignCenter, "F  R  I  D  A  Y   —   A I   A S S I S T A N T")

        # ── Corner brackets ──
        self._draw_corners(painter, W, H, QColor(0, 200, 255, 150))

        # ── Scan line ──
        scan_y = 80 + ((self._tick * 2) % (H - 160))
        scan_grad = QLinearGradient(0, scan_y, W, scan_y)
        scan_grad.setColorAt(0,   QColor(0, 200, 255, 0))
        scan_grad.setColorAt(0.4, QColor(0, 200, 255, 25))
        scan_grad.setColorAt(0.5, QColor(0, 200, 255, 40))
        scan_grad.setColorAt(0.6, QColor(0, 200, 255, 25))
        scan_grad.setColorAt(1,   QColor(0, 200, 255, 0))
        painter.setBrush(scan_grad)
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, scan_y - 1, W, 3)

        # ── Main content panel ──
        pad_x = max(100, W // 6)
        pad_y = 100
        panel_rect = QRectF(pad_x, pad_y, W - pad_x * 2, H - pad_y * 2)

        panel_bg = QLinearGradient(panel_rect.left(), panel_rect.top(),
                                   panel_rect.left(), panel_rect.bottom())
        panel_bg.setColorAt(0, QColor(0, 20, 50, 120))
        panel_bg.setColorAt(1, QColor(0, 10, 30, 80))
        painter.setBrush(panel_bg)
        painter.setPen(QPen(QColor(0, 180, 255, 60), 1))
        painter.drawRoundedRect(panel_rect, 16, 16)

        # ── Response text ──
        text_rect = panel_rect.adjusted(40, 40, -40, -60)
        painter.setFont(QFont("Segoe UI", 18))
        painter.setPen(QColor(210, 240, 255, 230))
        painter.drawText(text_rect, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
                         self._display_text)

        # ── Bottom animated bar ──
        painter.drawLine(80, H - 60, W - 80, H - 60)
        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QColor(0, 200, 255, 100))
        painter.drawText(QRectF(0, H - 50, W, 30), Qt.AlignCenter,
                         "Press  ESC  or say 'minimize'  to close")

        # ── Close (X) button ──
        self._draw_close_btn(painter, W)

        painter.end()

    def _draw_corners(self, painter, W, H, color):
        L = 30
        T = 2
        m = 50
        pen = QPen(color, T)
        painter.setPen(pen)
        corners = [(m, m, 1, 1), (W - m, m, -1, 1),
                   (m, H - m, 1, -1), (W - m, H - m, -1, -1)]
        for x, y, sx, sy in corners:
            painter.drawLine(x, y, x + L * sx, y)
            painter.drawLine(x, y, x, y + L * sy)

    def _draw_close_btn(self, painter, W):
        """Draw X button top-right."""
        bx, by, br = W - 70, 50, 16
        color = QColor(255, 100, 100, 200) if self._close_hover else QColor(0, 200, 255, 150)
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(bx - br, by - br, br * 2, br * 2)
        painter.drawLine(bx - 8, by - 8, bx + 8, by + 8)
        painter.drawLine(bx + 8, by - 8, bx - 8, by + 8)

    # ── Mouse events ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        W = self.width()
        bx, by, br = W - 70, 50, 20
        if abs(event.position().x() - bx) < br and abs(event.position().y() - by) < br:
            self.hide_overlay()

    def mouseMoveEvent(self, event):
        W = self.width()
        bx, by, br = W - 70, 50, 20
        was = self._close_hover
        self._close_hover = (abs(event.position().x() - bx) < br and
                              abs(event.position().y() - by) < br)
        if was != self._close_hover:
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide_overlay()
