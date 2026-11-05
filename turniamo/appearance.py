"""Explicit checkbox rendering, independent of the operating system palette."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle


class TurniamoStyle(QProxyStyle):
    def __init__(self):
        super().__init__("Fusion")

    def drawPrimitive(self, element, option, painter, widget=None):
        indicators = (QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                      QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck)
        if element not in indicators:
            return super().drawPrimitive(element, option, painter, widget)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        checked = bool(option.state & QStyle.StateFlag.State_On)
        mixed = bool(option.state & QStyle.StateFlag.State_NoChange)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        bounds = QRectF(option.rect).adjusted(1, 1, -1, -1)
        side = min(bounds.width(), bounds.height())
        box = QRectF(bounds.center().x() - side / 2, bounds.center().y() - side / 2, side, side)
        selected = checked or mixed
        fill = "#176b72" if selected else "#ffffff"
        border = "#176b72" if selected or hover else "#94a3b8"
        if not enabled:
            fill = "#94a3b8" if selected else "#f1f5f9"
            border = "#94a3b8" if selected else "#cbd5e1"
        painter.setPen(QPen(QColor(border), 1.4))
        painter.setBrush(QColor(fill))
        painter.drawRoundedRect(box, 3, 3)
        if selected:
            path = QPainterPath()
            if mixed:
                path.moveTo(box.left() + side * .25, box.center().y())
                path.lineTo(box.left() + side * .75, box.center().y())
            else:
                path.moveTo(box.left() + side * .22, box.top() + side * .52)
                path.lineTo(box.left() + side * .43, box.top() + side * .73)
                path.lineTo(box.left() + side * .79, box.top() + side * .28)
            painter.setPen(QPen(QColor("white"), 1.9, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
        painter.restore()

    def pixelMetric(self, metric, option=None, widget=None):
        if metric in (QStyle.PixelMetric.PM_IndicatorWidth, QStyle.PixelMetric.PM_IndicatorHeight):
            return 18
        return super().pixelMetric(metric, option, widget)
