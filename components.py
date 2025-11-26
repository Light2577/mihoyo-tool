# components.py
from PySide6.QtWidgets import QCheckBox
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QBrush


class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None, width=50, height=28,
                 bg_color="#E5E7EB", circle_color="#FFFFFF", active_color="#3B82F6"):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 颜色配置
        self._bg_color = bg_color
        self._circle_color = circle_color
        self._active_color = active_color

        # 动画参数 (圆圈的 X 坐标)
        self._circle_position = 3
        self._anim = QPropertyAnimation(self, b"circlePosition", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBounce)  # 弹跳效果
        self._anim.setDuration(300)

        self.stateChanged.connect(self._start_anim)

    # 定义属性供动画使用
    @Property(float)
    def circlePosition(self):
        return self._circle_position

    @circlePosition.setter
    def circlePosition(self, pos):
        self._circle_position = pos
        self.update()

    def _start_anim(self, state):
        start = self._circle_position
        if state:
            end = self.width() - self.height() + 3
        else:
            end = 3
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景胶囊
        track_rect = QRectF(0, 0, self.width(), self.height())
        # 如果被选中，背景变色
        bg_color = QColor(self._active_color) if self.isChecked() else QColor(self._bg_color)

        p.setBrush(QBrush(bg_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(track_rect, self.height() / 2, self.height() / 2)

        # 绘制圆圈
        circle_radius = (self.height() - 6) / 2
        circle_y = 3
        p.setBrush(QBrush(QColor(self._circle_color)))

        # 绘制圆圈
        p.drawEllipse(QPointF(self._circle_position + circle_radius, circle_y + circle_radius),
                      circle_radius, circle_radius)
        p.end()