import sys
import math
import random
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QFont, QRadialGradient, QLinearGradient,
    QPainterPath, QFontMetrics
)
from PySide6.QtWidgets import QWidget, QApplication
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
        self.setFixedSize(280, 380)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - 300, screen.height() - 410)

        # --- state ---
        self.state = "idle"          # idle | listening | speaking
        self.full_text = "FRIDAY ONLINE"
        self.display_text = "FRIDAY ONLINE"
        self.text_index = len("FRIDAY ONLINE")

        # --- maximize button ---
        self.maximize_callback = None   # set from friday.pyw
        self._max_btn_hover = False

        # --- animation vars ---
        self.tick = 0
        self.rotation = 0.0
        self.pulse = 0.0
        self.wave_bars = [random.uniform(0.1, 0.5) for _ in range(18)]
        self.wave_targets = [random.uniform(0.1, 0.5) for _ in range(18)]
        self.scan_y = 0.0

        # --- particles ---
        self.particles = [
            {"angle": random.uniform(0, 360),
             "radius": random.uniform(85, 115),
             "speed": random.uniform(0.4, 1.2),
             "size": random.uniform(1.5, 3.5),
             "alpha": random.randint(100, 220)}
            for _ in range(55)
        ]

        # --- hex grid dots (decorative) ---
        self.hex_dots = self._make_hex_dots()

        self.timer = QTimer()
        self.timer.timeout.connect(self._animate)
        self.timer.start(16)   # ~60 fps

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_hex_dots(self):
        dots = []
        cx, cy = 140, 125
        for ring in range(1, 5):
            r = ring * 22
            count = ring * 6
            for i in range(count):
                a = math.radians(360 / count * i)
                dots.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return dots

    def _state_colors(self):
        if self.state == "listening":
            return QColor(0, 255, 140), QColor(0, 180, 100)   # green
        elif self.state == "speaking":
            return QColor(255, 80, 220), QColor(180, 40, 160)  # magenta
        else:
            return QColor(0, 220, 255), QColor(0, 140, 220)    # cyan

    # ── public API ──────────────────────────────────────────────────────────

    def set_state(self, state):
        self.state = state

    def update_status(self, text):
        self.full_text = text
        self.display_text = ""
        self.text_index = 0

    # ── animation tick ──────────────────────────────────────────────────────

    def _animate(self):
        self.tick += 1
        self.rotation += 1.8
        self.pulse += 0.08
        self.scan_y = (self.scan_y + 1.5) % 250

        # typewriter
        if self.text_index < len(self.full_text):
            self.text_index += 1
            self.display_text = self.full_text[:self.text_index]

        # wave bars
        for i in range(len(self.wave_bars)):
            diff = self.wave_targets[i] - self.wave_bars[i]
            self.wave_bars[i] += diff * 0.15
            if abs(diff) < 0.02:
                if self.state == "speaking":
                    self.wave_targets[i] = random.uniform(0.25, 1.0)
                elif self.state == "listening":
                    self.wave_targets[i] = random.uniform(0.1, 0.6)
                else:
                    self.wave_targets[i] = random.uniform(0.05, 0.2)

        # orbit particles
        for p in self.particles:
            p["angle"] += p["speed"]

        self.update()

    # ── paint ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        primary, secondary = self._state_colors()
        cx, cy = 140, 125

        # ══ 1. outer soft glow ══
        glow = QRadialGradient(cx, cy, 160)
        glow.setColorAt(0, QColor(primary.red(), primary.green(), primary.blue(), 30))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - 160, cy - 160, 320, 320)

        # ══ 2. HUD corner brackets ══
        self._draw_corners(painter, primary)

        # ══ 3. hex grid dots ══
        dot_pen = QPen(QColor(primary.red(), primary.green(), primary.blue(), 35))
        dot_pen.setWidth(1)
        painter.setPen(dot_pen)
        painter.setBrush(QColor(primary.red(), primary.green(), primary.blue(), 18))
        for (dx, dy) in self.hex_dots:
            painter.drawEllipse(QPointF(dx, dy), 2, 2)

        # ══ 4. rotating rings ══
        self._draw_rings(painter, cx, cy, primary, secondary)

        # ══ 5. orbit particles ══
        for p in self.particles:
            rad = math.radians(p["angle"])
            px = cx + p["radius"] * math.cos(rad)
            py = cy + p["radius"] * math.sin(rad)
            c = QColor(primary.red(), primary.green(), primary.blue(), p["alpha"])
            painter.setPen(Qt.NoPen)
            painter.setBrush(c)
            painter.drawEllipse(QPointF(px, py), p["size"] / 2, p["size"] / 2)

        # ══ 6. arc reactor core ══
        self._draw_core(painter, cx, cy, primary, secondary)

        # ══ 7. scan line ══
        scan_color = QColor(primary.red(), primary.green(), primary.blue(), 18)
        painter.setPen(QPen(scan_color, 1))
        scan_abs_y = cy - 115 + self.scan_y
        if cy - 115 < scan_abs_y < cy + 115:
            painter.drawLine(cx - 115, int(scan_abs_y), cx + 115, int(scan_abs_y))

        # ══ 8. wave bars ══
        self._draw_wave(painter, cx, primary)

        # ══ 9. status panel ══
        self._draw_panel(painter, primary, secondary)

        # ══ 10. Maximize button ══
        self._draw_maximize_btn(painter)

        painter.end()

    def _draw_corners(self, painter, color):
        """HUD-style corner brackets."""
        L = 18   # bracket length
        T = 2    # line width
        margin = 8
        pen = QPen(QColor(color.red(), color.green(), color.blue(), 180), T)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        w, h = self.width(), self.height()
        corners = [
            (margin, margin, 1, 1),
            (w - margin, margin, -1, 1),
            (margin, h - margin, 1, -1),
            (w - margin, h - margin, -1, -1),
        ]
        for (x, y, sx, sy) in corners:
            painter.drawLine(x, y, x + L * sx, y)
            painter.drawLine(x, y, x, y + L * sy)

    def _draw_rings(self, painter, cx, cy, primary, secondary):
        """Three rotating segmented rings."""
        painter.save()
        painter.translate(cx, cy)

        # Ring 1 — outer, slow
        painter.rotate(self.rotation * 0.5)
        pen = QPen(QColor(primary.red(), primary.green(), primary.blue(), 130), 2)
        painter.setPen(pen)
        for i in range(0, 360, 24):
            painter.drawArc(QRectF(-108, -108, 216, 216), i * 16, 14 * 16)
        painter.rotate(-self.rotation * 0.5)

        # Ring 2 — mid, medium, reverse
        painter.rotate(-self.rotation * 0.9)
        pen2 = QPen(QColor(secondary.red(), secondary.green(), secondary.blue(), 100), 1)
        painter.setPen(pen2)
        for i in range(0, 360, 18):
            painter.drawArc(QRectF(-85, -85, 170, 170), i * 16, 10 * 16)
        painter.rotate(self.rotation * 0.9)

        # Ring 3 — inner, fast
        painter.rotate(self.rotation * 1.6)
        pen3 = QPen(QColor(primary.red(), primary.green(), primary.blue(), 80), 1)
        painter.setPen(pen3)
        for i in range(0, 360, 30):
            painter.drawArc(QRectF(-65, -65, 130, 130), i * 16, 16 * 16)

        painter.restore()

    def _draw_core(self, painter, cx, cy, primary, secondary):
        """Arc reactor core — layered glowing circles."""
        # Outer glow ring
        glow_r = 48 + math.sin(self.pulse) * 3
        g = QRadialGradient(cx, cy, glow_r)
        g.setColorAt(0, QColor(primary.red(), primary.green(), primary.blue(), 160))
        g.setColorAt(0.5, QColor(primary.red(), primary.green(), primary.blue(), 60))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(g)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # Mid ring border
        pen = QPen(QColor(primary.red(), primary.green(), primary.blue(), 200), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), 34, 34)

        # Inner solid core
        core_r = 22 + math.sin(self.pulse * 1.5) * 2
        core_grad = QRadialGradient(cx - 6, cy - 6, core_r * 1.5)
        core_grad.setColorAt(0, QColor(255, 255, 255, 230))
        core_grad.setColorAt(0.4, QColor(primary.red(), primary.green(), primary.blue(), 210))
        core_grad.setColorAt(1, QColor(secondary.red(), secondary.green(), secondary.blue(), 140))
        painter.setBrush(core_grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # Speaking shockwave
        if self.state == "speaking":
            shock_r = 58 + math.sin(self.pulse * 4) * 14
            painter.setPen(QPen(QColor(255, 80, 220, 90), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), shock_r, shock_r)

        # Listening pulse ring
        if self.state == "listening":
            t = (self.tick % 40) / 40
            listen_r = 50 + t * 35
            alpha = int(180 * (1 - t))
            painter.setPen(QPen(QColor(0, 255, 140, alpha), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), listen_r, listen_r)

    def _draw_wave(self, painter, cx, primary):
        """Audio wave bars below the core."""
        bar_count = len(self.wave_bars)
        bar_w = 6
        gap = 3
        total_w = bar_count * (bar_w + gap) - gap
        start_x = cx - total_w // 2
        base_y = 252
        max_h = 28

        for i, val in enumerate(self.wave_bars):
            h = max(3, int(val * max_h))
            x = start_x + i * (bar_w + gap)
            alpha = 160 + int(val * 95)
            color = QColor(primary.red(), primary.green(), primary.blue(), alpha)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            rect = QRectF(x, base_y - h, bar_w, h)
            painter.drawRoundedRect(rect, 2, 2)

    def _draw_panel(self, painter, primary, secondary):
        """Bottom status text panel with glassmorphism style."""
        panel_x, panel_y = 14, 270
        panel_w, panel_h = 252, 95
        r = 12

        # Glassmorphism background
        bg = QLinearGradient(panel_x, panel_y, panel_x, panel_y + panel_h)
        bg.setColorAt(0, QColor(primary.red(), primary.green(), primary.blue(), 22))
        bg.setColorAt(1, QColor(0, 0, 0, 40))
        painter.setBrush(bg)
        pen = QPen(QColor(primary.red(), primary.green(), primary.blue(), 80), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(QRectF(panel_x, panel_y, panel_w, panel_h), r, r)

        # State label (top-right of panel)
        state_labels = {"idle": "STANDBY", "listening": "LISTENING", "speaking": "SPEAKING"}
        label = state_labels.get(self.state, "STANDBY")
        painter.setFont(QFont("Consolas", 7, QFont.Bold))
        painter.setPen(QPen(QColor(primary.red(), primary.green(), primary.blue(), 140)))
        painter.drawText(QRectF(panel_x + 8, panel_y + 7, panel_w - 16, 14),
                         Qt.AlignRight, label)

        # Divider line
        div_pen = QPen(QColor(primary.red(), primary.green(), primary.blue(), 50), 1)
        painter.setPen(div_pen)
        painter.drawLine(panel_x + 10, panel_y + 24,
                         panel_x + panel_w - 10, panel_y + 24)

        # Main status text
        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QPen(QColor(primary.red(), primary.green(), primary.blue(), 220)))
        painter.drawText(
            QRectF(panel_x + 10, panel_y + 28, panel_w - 20, panel_h - 32),
            Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
            self.display_text
        )

    # ── drag to move ────────────────────────────────────────────────────────
    def _draw_maximize_btn(self, painter):
        """Small expand icon at top-right of widget."""
        bx, by, br = self.width() - 18, 18, 10
        primary, _ = self._state_colors()
        color = QColor(255, 220, 0, 220) if self._max_btn_hover else \
                QColor(primary.red(), primary.green(), primary.blue(), 160)
        pen = QPen(color, 1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        # Draw expand arrows (two small L-shapes)
        s = 5
        painter.drawLine(bx - s, by - s, bx - 1, by - s)
        painter.drawLine(bx - s, by - s, bx - s, by - 1)
        painter.drawLine(bx + 1, by + s, bx + s, by + s)
        painter.drawLine(bx + s, by + 1, bx + s, by + s)

    # ---------------- DRAG ----------------
    def mousePressEvent(self, event):
        bx, by, br = self.width() - 18, 18, 12
        px, py = event.position().x(), event.position().y()
        if abs(px - bx) < br and abs(py - by) < br:
            if self.maximize_callback:
                self.maximize_callback()
            return
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        bx, by, br = self.width() - 18, 18, 12
        px, py = event.position().x(), event.position().y()
        was = self._max_btn_hover
        self._max_btn_hover = abs(px - bx) < br and abs(py - by) < br
        if was != self._max_btn_hover:
            self.update()
        if hasattr(self, 'old_pos'):
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()


# ── standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import time, threading
    app = QApplication(sys.argv)
    ui = HologramUI()
    ui.show()

    def cycle():
        states = [
            ("idle",      "FRIDAY ONLINE"),
            ("listening", "Listening..."),
            ("speaking",  "Yes sir, RCB made it to the finals of IPL 2026!"),
        ]
        while True:
            for s, t in states:
                ui.set_state(s)
                ui.update_status(t)
                time.sleep(3)

    threading.Thread(target=cycle, daemon=True).start()
    sys.exit(app.exec())