#!/usr/bin/env python3
"""Img Annotator — visor de imágenes con anotación y recorte.

Uso:
    img_annotator.py [archivo_o_carpeta]

Herramientas (teclas):
    V / Esc   selección: mover, doble clic en texto para editarlo, Supr borra
    A         flecha        (Shift: ángulos de 45°)
    R         rectángulo    (Shift: cuadrado)
    O         círculo/elipse (Shift: círculo)
    T         texto: clic y escribir; Esc o clic afuera termina
    C         recortar: arrastrá los bordes, Enter aplica, Esc cancela

Otros atajos:
    Flecha izq/der, RePág/AvPág   imagen anterior / siguiente de la carpeta
    Ctrl+Z / Ctrl+Shift+Z (o Ctrl+Y)   deshacer / rehacer
    Ctrl+Shift+Supr   borrar todas las anotaciones
    Ctrl+O / Ctrl+S / Ctrl+C   abrir / guardar como / copiar al portapapeles
    Rueda        zoom · botón central: desplazar · Ctrl+0 ajustar · Ctrl+1 100 %
"""
import math
import re
import sys
from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPointF, QRect, QSize, QEvent, QTimer, Signal
from PySide6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QPolygonF, QKeySequence, QAction,
    QActionGroup, QImage, QFont, QIcon, QPainterPath, QPainterPathStroker,
    QPalette, QUndoStack, QUndoCommand, QConicalGradient, QTransform,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsItem, QStyleOptionGraphicsItem, QStyle,
    QToolBar, QColorDialog, QSpinBox, QSlider, QLabel, QFileDialog,
    QMessageBox, QStatusBar, QWidget, QComboBox, QPushButton,
    QAbstractButton, QAbstractSpinBox, QSizePolicy, QHBoxLayout,
)

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

# ---------------------------------------------------------------- estilo
ACCENT = "#4c8dff"
BG = "#1e1f22"
PANEL = "#26282c"
BORDER = "#363940"
TEXT = "#e8e8ec"
MUTED = "#9aa0aa"

PRESET_COLORS = ["#ff3b30", "#ff9500", "#ffd60a", "#34c759",
                 "#0a84ff", "#bf5af2", "#ffffff", "#111111"]

DEFAULT_WIDTH = 10
MIN_CROP = 8  # lado mínimo del recorte, en píxeles de imagen

STYLESHEET = f"""
QMainWindow, QDialog, QMessageBox {{ background: {BG}; }}
QWidget {{ color: {TEXT}; }}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px 6px; }}
QToolBar {{ background: {PANEL}; border: 0; spacing: 6px; padding: 6px 8px; }}
QToolBar#tools {{ border-right: 1px solid {BORDER}; padding: 8px 6px; spacing: 4px; }}
QToolBar#options {{ border-bottom: 1px solid {BORDER}; }}
QToolBar::separator {{ background: {BORDER}; width: 1px; height: 1px; margin: 4px 8px; }}
QToolButton {{ background: transparent; border: 0; border-radius: 8px; padding: 7px; }}
QToolButton:hover {{ background: #34373d; }}
QToolButton:checked {{ background: {ACCENT}; }}
QToolButton:pressed {{ background: #2b6fe0; }}
QToolButton:disabled {{ background: transparent; }}
QLabel#cap {{ color: {MUTED}; font-size: 11px; padding: 0 2px; }}
QSpinBox, QComboBox {{
    background: {BG}; border: 1px solid #3a3d44; border-radius: 6px;
    padding: 3px 6px; min-height: 22px; selection-background-color: {ACCENT};
}}
QSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {BORDER}; selection-background-color: {ACCENT}; }}
QSlider::groove:horizontal {{ height: 4px; background: #3a3d44; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QPushButton {{ background: #34373d; border: 0; border-radius: 7px; padding: 6px 14px; }}
QPushButton:hover {{ background: #3f434a; }}
QPushButton:disabled {{ color: #5b606a; }}
QPushButton#accent {{ background: {ACCENT}; color: #ffffff; font-weight: 600; }}
QPushButton#accent:hover {{ background: #6aa0ff; }}
QStatusBar {{ background: {PANEL}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: 0; }}
QStatusBar QLabel {{ color: {MUTED}; padding: 0 8px; }}
"""


def apply_theme(app: QApplication):
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Base, QColor(BG))
    pal.setColor(QPalette.AlternateBase, QColor(PANEL))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor(PANEL))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ToolTipBase, QColor(PANEL))
    pal.setColor(QPalette.ToolTipText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("white"))
    pal.setColor(QPalette.PlaceholderText, QColor(MUTED))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor("#5b606a"))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#5b606a"))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#5b606a"))
    app.setPalette(pal)
    app.setStyleSheet(STYLESHEET)


# ---------------------------------------------------------------- iconos
def arrow_head_points(p1: QPointF, p2: QPointF, head_len: float):
    """Triángulo de la punta de flecha: (punta, base_izq, base_der, base_centro)."""
    dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return None
    ux, uy = dx / length, dy / length
    head_len = min(head_len, length)
    bx, by = p2.x() - ux * head_len, p2.y() - uy * head_len
    hw = head_len * 0.5
    left = QPointF(bx - uy * hw, by + ux * hw)
    right = QPointF(bx + uy * hw, by - ux * hw)
    return p2, left, right, QPointF(bx, by), (ux, uy)


def make_icon(kind: str, color: str = TEXT) -> QIcon:
    """Icono de 24x24 lógicos dibujado a mano (nítido en pantallas HiDPI)."""
    ratio = 2
    pm = QPixmap(24 * ratio, 24 * ratio)
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    pen = QPen(c, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if kind == "select":
        poly = QPolygonF([QPointF(6, 3.5), QPointF(6, 19.5), QPointF(10.2, 15.6),
                          QPointF(13, 21), QPointF(15.6, 19.8), QPointF(12.9, 14.6),
                          QPointF(18.5, 14.2)])
        p.setBrush(c)
        p.setPen(QPen(c, 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolygon(poly)
    elif kind == "arrow":
        a, b = QPointF(5, 19), QPointF(19, 5)
        head = arrow_head_points(a, b, 9)
        p.drawLine(a, head[3] + QPointF(head[4][0], head[4][1]) * 2)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawPolygon(QPolygonF([head[0], head[1], head[2]]))
    elif kind == "rect":
        p.drawRoundedRect(QRectF(4.5, 6.5, 15, 11), 2, 2)
    elif kind == "ellipse":
        p.drawEllipse(QRectF(4.5, 5.5, 15, 13))
    elif kind == "text":
        f = QFont()
        f.setFamily("Sans")
        f.setBold(True)
        f.setPixelSize(19)
        p.setFont(f)
        p.drawText(QRectF(0, 0, 24, 24), Qt.AlignCenter, "T")
    elif kind == "crop":
        pen.setJoinStyle(Qt.MiterJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(7, 2.5)
        path.lineTo(7, 17)
        path.lineTo(21.5, 17)
        p.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(2.5, 7)
        path2.lineTo(17, 7)
        path2.lineTo(17, 21.5)
        p.drawPath(path2)
    elif kind in ("undo", "redo"):
        path = QPainterPath()
        path.moveTo(8, 10)
        path.lineTo(14, 10)
        path.cubicTo(19, 10, 19, 18, 14, 18)
        path.lineTo(9, 18)
        head = QPolygonF([QPointF(3, 10), QPointF(8.5, 5.5), QPointF(8.5, 14.5)])
        if kind == "redo":
            path = QTransform(-1, 0, 0, 1, 24, 0).map(path)
            head = QPolygonF([QPointF(24 - q.x(), q.y()) for q in head])
        p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawPolygon(head)
    p.end()
    return QIcon(pm)


class Swatch(QAbstractButton):
    """Botón de color redondo. El «custom» muestra un arcoíris hasta que se elige uno."""

    def __init__(self, color: str, custom: bool = False):
        super().__init__()
        self.color = QColor(color)
        self.custom = custom
        self.picked = not custom
        self.setCheckable(True)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Color personalizado…" if custom else color.upper())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        if self.custom and not self.picked:
            grad = QConicalGradient(r.center(), 90)
            for i, col in enumerate(["#ff3b30", "#ffd60a", "#34c759", "#0a84ff", "#bf5af2", "#ff3b30"]):
                grad.setColorAt(i / 5, QColor(col))
            p.setBrush(grad)
        else:
            p.setBrush(self.color)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.drawEllipse(r)
        if self.isChecked():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(ACCENT), 2))
            p.drawEllipse(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5))
        elif self.underMouse():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 90), 1.5))
            p.drawEllipse(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5))


# ---------------------------------------------------------------- utilidades
def natural_key(path: Path):
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", path.name)]


def draw_selection(painter: QPainter, rect: QRectF):
    pen = QPen(QColor(ACCENT), 1.5, Qt.DashLine)
    pen.setCosmetic(True)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(rect)


def make_pen(color: QColor, width: float) -> QPen:
    pen = QPen(color, width)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    return pen


def set_movable(item: QGraphicsItem, on: bool = True):
    item.setFlag(QGraphicsItem.ItemIsMovable, on)
    item.setFlag(QGraphicsItem.ItemIsSelectable, on)


# ---------------------------------------------------------------- items
class RectItem(QGraphicsRectItem):
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRect(self.rect())
        if self.isSelected():
            draw_selection(painter, self.boundingRect())


class EllipseItem(QGraphicsEllipseItem):
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())
        if self.isSelected():
            draw_selection(painter, self.boundingRect())


class ArrowItem(QGraphicsItem):
    """Flecha con punta rellena. La punta escala con el grosor."""

    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: float):
        super().__init__()
        self.p1 = QPointF(p1)
        self.p2 = QPointF(p2)
        self.color = QColor(color)
        self.width = width

    def set_end(self, p: QPointF):
        self.prepareGeometryChange()
        self.p2 = QPointF(p)

    def set_style(self, color=None, width=None):
        self.prepareGeometryChange()
        if color is not None:
            self.color = QColor(color)
        if width is not None:
            self.width = width
        self.update()

    def _head_len(self):
        return max(18.0, self.width * 3.2)

    def _parts(self):
        head = arrow_head_points(self.p1, self.p2, self._head_len())
        if head is None:
            return None, None
        tip, left, right, base, (ux, uy) = head
        # La línea entra un poco en la punta para que no queden huecos.
        end = QPointF(base.x() + ux * self._head_len() * 0.3, base.y() + uy * self._head_len() * 0.3)
        return end, QPolygonF([tip, left, right])

    def shape(self):
        end, poly = self._parts()
        path = QPainterPath()
        if end is None:
            return path
        line = QPainterPath(self.p1)
        line.lineTo(end)
        stroker = QPainterPathStroker()
        stroker.setWidth(max(self.width, 14))
        stroker.setCapStyle(Qt.RoundCap)
        path = stroker.createStroke(line)
        path.addPolygon(poly)
        return path

    def boundingRect(self):
        return self.shape().boundingRect().adjusted(-2, -2, 2, 2)

    def paint(self, painter, option, widget=None):
        end, poly = self._parts()
        if end is None:
            return
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(self.p1, end)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.color)
        painter.drawPolygon(poly)
        if self.isSelected():
            draw_selection(painter, self.boundingRect())


class EditableTextItem(QGraphicsTextItem):
    """Texto que entra en edición al crearse. Al perder el foco queda como un
    elemento movible; si queda vacío se elimina."""

    def __init__(self, color: QColor, px: int, on_commit, on_remove, on_edited):
        super().__init__()
        self.on_commit, self.on_remove, self.on_edited = on_commit, on_remove, on_edited
        self.committed = False
        self._before = ""
        self.setDefaultTextColor(color)
        font = QFont()
        font.setFamily("Sans")
        font.setBold(True)
        font.setPixelSize(px)
        self.setFont(font)
        self.document().setDocumentMargin(4)
        set_movable(self, False)

    def set_pixel_size(self, px: int):
        font = self.font()
        font.setPixelSize(px)
        self.setFont(font)

    def detach(self):
        self.on_commit = self.on_remove = self.on_edited = None

    def is_editing(self) -> bool:
        return self.textInteractionFlags() == Qt.TextEditorInteraction

    def start_edit(self):
        self._before = self.toPlainText()
        set_movable(self, False)
        self.setSelected(False)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        cur = self.textCursor()
        cur.movePosition(cur.MoveOperation.End)
        self.setTextCursor(cur)

    def finish_edit(self):
        cur = self.textCursor()
        cur.clearSelection()
        self.setTextCursor(cur)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        text = self.toPlainText()
        if not text.strip():
            if self.on_remove:
                self.on_remove(self)
            return
        set_movable(self, True)
        if not self.committed:
            self.committed = True
            if self.on_commit:
                self.on_commit(self)
        elif text != self._before and self.on_edited:
            self.on_edited(self, self._before, text)
        self.setSelected(True)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if event.reason() in (Qt.ActiveWindowFocusReason, Qt.PopupFocusReason):
            return  # p. ej. se abrió el selector de color: seguimos editando
        if self.is_editing():
            self.finish_edit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clearFocus()
            return
        super().keyPressEvent(event)

    def paint(self, painter, option, widget=None):
        opt = QStyleOptionGraphicsItem(option)
        opt.state &= ~(QStyle.State_Selected | QStyle.State_HasFocus)
        super().paint(painter, opt, widget)
        if self.is_editing():
            draw_selection(painter, self.boundingRect())
        elif self.isSelected():
            draw_selection(painter, self.boundingRect())


class CropOverlay(QGraphicsItem):
    """Oscurece lo que queda fuera del recorte y dibuja el marco, los tercios
    y los tiradores. El estado vive en Canvas.crop_rect."""

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setZValue(10_000)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        return self.canvas.scene_.sceneRect()

    def paint(self, painter, option, widget=None):
        c = self.canvas
        r = c.crop_rect
        if r is None:
            return
        s = 1.0 / max(c.transform().m11(), 1e-6)  # unidades de escena por píxel de pantalla
        full = c.scene_.sceneRect()
        dim = QPainterPath()
        dim.addRect(full)
        inner = QPainterPath()
        inner.addRect(r)
        painter.fillPath(dim.subtracted(inner), QColor(0, 0, 0, 160))

        painter.setRenderHint(QPainter.Antialiasing, False)
        grid = QPen(QColor(255, 255, 255, 80), 1)
        grid.setCosmetic(True)
        painter.setPen(grid)
        for i in (1, 2):
            x = r.left() + r.width() * i / 3
            y = r.top() + r.height() * i / 3
            painter.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            painter.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        border = QPen(QColor("white"), 1.5)
        border.setCosmetic(True)
        painter.setPen(border)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(r)

        half = 5 * s
        hp = QPen(QColor(ACCENT), 1.5)
        hp.setCosmetic(True)
        painter.setPen(hp)
        painter.setBrush(QColor("white"))
        for pt in Canvas.handle_points(r).values():
            painter.drawRect(QRectF(pt.x() - half, pt.y() - half, half * 2, half * 2))

        # etiqueta con el tamaño
        painter.setRenderHint(QPainter.Antialiasing, True)
        label = f"{round(r.width())} × {round(r.height())}"
        font = QFont()
        font.setPixelSize(max(1, round(12 * s)))
        font.setBold(True)
        painter.setFont(font)
        w = painter.fontMetrics().horizontalAdvance(label) + 14 * s
        h = 22 * s
        x = r.center().x() - w / 2
        y = r.top() - h - 8 * s
        if y < full.top() + 2 * s:
            y = r.top() + 8 * s
        pill = QRectF(x, y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(20, 21, 24, 220))
        painter.drawRoundedRect(pill, 6 * s, 6 * s)
        painter.setPen(QColor("white"))
        painter.drawText(pill, Qt.AlignCenter, label)


# ---------------------------------------------------------------- comandos (deshacer)
class AddCmd(QUndoCommand):
    def __init__(self, canvas, item, text="Añadir"):
        super().__init__(text)
        self.canvas, self.item, self._first = canvas, item, True  # el item ya está en la escena

    def redo(self):
        if self._first:
            self._first = False
            return
        self.canvas.scene_.addItem(self.item)

    def undo(self):
        self.canvas.scene_.removeItem(self.item)


class DeleteCmd(QUndoCommand):
    def __init__(self, canvas, items, text="Borrar"):
        super().__init__(text)
        self.canvas, self.items = canvas, list(items)

    def redo(self):
        for it in self.items:
            if it.scene() is self.canvas.scene_:
                self.canvas.scene_.removeItem(it)

    def undo(self):
        for it in self.items:
            self.canvas.scene_.addItem(it)


class MoveCmd(QUndoCommand):
    def __init__(self, moves):
        super().__init__("Mover")
        self.moves, self._first = moves, True  # lista de (item, pos_vieja, pos_nueva)

    def redo(self):
        if self._first:
            self._first = False
            return
        for it, _, new in self.moves:
            it.setPos(new)

    def undo(self):
        for it, old, _ in self.moves:
            it.setPos(old)


class EditTextCmd(QUndoCommand):
    def __init__(self, item, before, after):
        super().__init__("Editar texto")
        self.item, self.before, self.after, self._first = item, before, after, True

    def redo(self):
        if self._first:
            self._first = False
            return
        self.item.setPlainText(self.after)

    def undo(self):
        self.item.setPlainText(self.before)


class CropCmd(QUndoCommand):
    """Recorta la imagen base y desplaza las anotaciones para que sigan en su sitio."""

    def __init__(self, canvas, rect: QRect):
        super().__init__("Recortar")
        self.canvas, self.rect = canvas, rect
        self.old_pixmap = canvas.pixmap_item.pixmap()

    def _apply(self, pixmap: QPixmap, delta: QPointF):
        cv = self.canvas
        cv.pixmap_item.setPixmap(pixmap)
        for it in cv.annotation_items():
            it.moveBy(delta.x(), delta.y())
        cv.scene_.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
        cv.crop_rect = None
        cv.view_changed()

    def redo(self):
        self._apply(self.old_pixmap.copy(self.rect), QPointF(-self.rect.x(), -self.rect.y()))

    def undo(self):
        self._apply(self.old_pixmap, QPointF(self.rect.x(), self.rect.y()))


# ---------------------------------------------------------------- lienzo
class Canvas(QGraphicsView):
    zoomChanged = Signal(float, bool)  # factor, ajustado a ventana

    CURSORS = {
        (-1, -1): Qt.SizeFDiagCursor, (1, 1): Qt.SizeFDiagCursor,
        (1, -1): Qt.SizeBDiagCursor, (-1, 1): Qt.SizeBDiagCursor,
        (0, -1): Qt.SizeVerCursor, (0, 1): Qt.SizeVerCursor,
        (-1, 0): Qt.SizeHorCursor, (1, 0): Qt.SizeHorCursor,
    }

    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window
        self.scene_ = QGraphicsScene(self)
        self.setScene(self.scene_)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor("#17181b"))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setAcceptDrops(True)

        self.pixmap_item = None
        self.overlay = None
        self.tool = "select"
        self.color = QColor(PRESET_COLORS[0])
        self.width_px = DEFAULT_WIDTH
        self.text_px = 40
        self.fit_mode = True
        self.crop_rect: QRectF | None = None
        self.crop_ratio: float | None = None
        self._crop_drag = None
        self._drawing_item = None
        self._start_pos = None
        self._move_snapshot = None
        self._panning = False
        self._pan_last = None
        # PySide no mantiene viva la referencia Python de un item recién agregado a la
        # escena: si se suelta, pierde sus métodos propios (is_editing, paint…).
        self._keep: list[QGraphicsItem] = []

    # ----- escena -----
    def add_item(self, item: QGraphicsItem):
        self.scene_.addItem(item)
        self._keep.append(item)
        return item

    def annotation_items(self):
        return [it for it in self.scene_.items()
                if it.parentItem() is None and it is not self.pixmap_item and it is not self.overlay]

    def load_pixmap(self, pixmap: QPixmap):
        for it in self.scene_.items():
            if isinstance(it, EditableTextItem):
                it.detach()
        self.scene_.clear()
        self._keep.clear()
        self.crop_rect = None
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.scene_.addItem(self.pixmap_item)
        self.overlay = CropOverlay(self)
        self.overlay.setVisible(self.tool == "crop")
        self.scene_.addItem(self.overlay)
        self.scene_.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
        if self.tool == "crop":
            self.crop_rect = QRectF(self.scene_.sceneRect())
        self.fit_mode = True
        self.fit()

    def set_tool(self, tool: str):
        if tool != "text":
            self.scene_.setFocusItem(None)  # cierra un texto en edición
        self.tool = tool
        self.setDragMode(QGraphicsView.RubberBandDrag if tool == "select" else QGraphicsView.NoDrag)
        if tool != "select":
            self.scene_.clearSelection()
        if self.overlay is not None:
            self.overlay.setVisible(tool == "crop")
        self.crop_rect = QRectF(self.scene_.sceneRect()) if (tool == "crop" and self.pixmap_item) else None
        self._crop_drag = None
        cursor = {"select": Qt.ArrowCursor, "text": Qt.IBeamCursor}.get(tool, Qt.CrossCursor)
        self.viewport().setCursor(cursor)
        self.scene_.update()

    def view_changed(self):
        if self.fit_mode and self.pixmap_item:
            self.fitInView(self.scene_.sceneRect(), Qt.KeepAspectRatio)
        self.zoomChanged.emit(self.transform().m11(), self.fit_mode)
        self.scene_.update()

    def fit(self):
        self.fit_mode = True
        self.view_changed()

    def set_zoom(self, factor: float):
        factor = min(max(factor, 0.02), 32.0)
        self.fit_mode = False
        self.resetTransform()
        self.scale(factor, factor)
        self.zoomChanged.emit(factor, False)
        self.scene_.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_mode and self.pixmap_item:
            self.view_changed()

    def wheelEvent(self, event):
        if not self.pixmap_item:
            return
        step = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        factor = min(max(self.transform().m11() * step, 0.02), 32.0)
        self.fit_mode = False
        self.scale(factor / self.transform().m11(), factor / self.transform().m11())
        self.zoomChanged.emit(self.transform().m11(), False)
        self.scene_.update()

    def apply_style(self, color=None, width=None, size=None):
        """Aplica color/grosor/tamaño a lo seleccionado (y al texto en edición)."""
        items = list(self.scene_.selectedItems())
        focus = self.scene_.focusItem()
        if isinstance(focus, EditableTextItem) and focus not in items:
            items.append(focus)
        changed = False
        for it in items:
            if isinstance(it, EditableTextItem):
                if color is not None:
                    it.setDefaultTextColor(color)
                    changed = True
                if size is not None:
                    it.set_pixel_size(size)
                    changed = True
            elif isinstance(it, ArrowItem):
                it.set_style(color, width)
                changed = changed or color is not None or width is not None
            elif isinstance(it, (RectItem, EllipseItem)):
                pen = it.pen()
                if color is not None:
                    pen.setColor(color)
                if width is not None:
                    pen.setWidthF(width)
                it.setPen(pen)
                it.update()
                changed = changed or color is not None or width is not None
        if changed:
            self.win.style_dirty = True
            self.win.refresh_title()

    # ----- recorte -----
    @staticmethod
    def handle_points(r: QRectF):
        c = r.center()
        return {
            (-1, -1): r.topLeft(), (0, -1): QPointF(c.x(), r.top()), (1, -1): r.topRight(),
            (-1, 0): QPointF(r.left(), c.y()), (1, 0): QPointF(r.right(), c.y()),
            (-1, 1): r.bottomLeft(), (0, 1): QPointF(c.x(), r.bottom()), (1, 1): r.bottomRight(),
        }

    def _px(self) -> float:
        return 1.0 / max(self.transform().m11(), 1e-6)

    def _clamp(self, p: QPointF) -> QPointF:
        b = self.scene_.sceneRect()
        return QPointF(min(max(p.x(), b.left()), b.right()), min(max(p.y(), b.top()), b.bottom()))

    def _crop_hit(self, pos: QPointF):
        r = self.crop_rect
        if r is None:
            return None
        tol = 9 * self._px()
        best = None  # las esquinas ganan sobre los puntos medios de los bordes
        for key, pt in self.handle_points(r).items():
            if abs(pos.x() - pt.x()) <= tol and abs(pos.y() - pt.y()) <= tol:
                if best is None or (key[0] != 0 and key[1] != 0):
                    best = key
        if best is not None:
            return ("handle", best)
        if r.contains(pos):
            return ("move", None)
        return None

    def _corner_rect(self, ax, ay, hx, hy, w, h):
        b = self.scene_.sceneRect()
        maxw = (b.right() - ax) if hx > 0 else (ax - b.left())
        maxh = (b.bottom() - ay) if hy > 0 else (ay - b.top())
        ratio = self.crop_ratio
        if ratio:
            w = min(max(w, h * ratio), maxw, maxh * ratio)
            h = w / ratio
        else:
            w, h = min(w, maxw), min(h, maxh)
        x0 = ax if hx > 0 else ax - w
        y0 = ay if hy > 0 else ay - h
        return QRectF(x0, y0, w, h)

    def _crop_resize(self, orig: QRectF, hx: int, hy: int, pos: QPointF):
        b = self.scene_.sceneRect()
        ratio = self.crop_ratio
        if hx and hy:
            ax = orig.left() if hx > 0 else orig.right()
            ay = orig.top() if hy > 0 else orig.bottom()
            return self._corner_rect(ax, ay, hx, hy,
                                     max(abs(pos.x() - ax), MIN_CROP), max(abs(pos.y() - ay), MIN_CROP))
        if hx:  # borde izquierdo / derecho
            ax = orig.left() if hx > 0 else orig.right()
            maxw = (b.right() - ax) if hx > 0 else (ax - b.left())
            w = min(max(abs(pos.x() - ax), MIN_CROP), maxw)
            cy = orig.center().y()
            h = orig.height()
            if ratio:
                h = w / ratio
                maxh = 2 * min(cy - b.top(), b.bottom() - cy)
                if h > maxh:
                    h = maxh
                    w = h * ratio
            return QRectF(ax if hx > 0 else ax - w, cy - h / 2, w, h)
        ay = orig.top() if hy > 0 else orig.bottom()  # borde superior / inferior
        maxh = (b.bottom() - ay) if hy > 0 else (ay - b.top())
        h = min(max(abs(pos.y() - ay), MIN_CROP), maxh)
        cx = orig.center().x()
        w = orig.width()
        if ratio:
            w = h * ratio
            maxw = 2 * min(cx - b.left(), b.right() - cx)
            if w > maxw:
                w = maxw
                h = w / ratio
        return QRectF(cx - w / 2, ay if hy > 0 else ay - h, w, h)

    def set_crop_ratio(self, ratio: float | None):
        self.crop_ratio = ratio
        r = self.crop_rect
        if ratio and r is not None:
            w, h = r.width(), r.height()
            if w / h > ratio:
                w = h * ratio
            else:
                h = w / ratio
            self.crop_rect = QRectF(r.center().x() - w / 2, r.center().y() - h / 2, w, h)
            self.scene_.update()

    def _crop_press(self, pos: QPointF):
        hit = self._crop_hit(pos)
        r = self.crop_rect
        if hit and hit[0] == "move" and r == self.scene_.sceneRect():
            hit = None  # con todo seleccionado no hay nada que mover: se arma un recorte nuevo
        if hit is None:
            a = self._clamp(pos)
            self._crop_drag = {"mode": "new", "anchor": a, "prev": QRectF(r) if r else None}
        elif hit[0] == "move":
            self._crop_drag = {"mode": "move", "start": pos, "orig": QRectF(r)}
        else:
            self._crop_drag = {"mode": "resize", "h": hit[1], "orig": QRectF(r)}

    def _crop_move(self, pos: QPointF):
        d = self._crop_drag
        b = self.scene_.sceneRect()
        if d["mode"] == "new":
            p = self._clamp(pos)
            a = d["anchor"]
            hx = 1 if p.x() >= a.x() else -1
            hy = 1 if p.y() >= a.y() else -1
            self.crop_rect = self._corner_rect(a.x(), a.y(), hx, hy, abs(p.x() - a.x()), abs(p.y() - a.y()))
        elif d["mode"] == "move":
            o = d["orig"]
            dx, dy = pos.x() - d["start"].x(), pos.y() - d["start"].y()
            x = min(max(o.x() + dx, b.left()), b.right() - o.width())
            y = min(max(o.y() + dy, b.top()), b.bottom() - o.height())
            self.crop_rect = QRectF(x, y, o.width(), o.height())
        else:
            hx, hy = d["h"]
            self.crop_rect = self._crop_resize(d["orig"], hx, hy, self._clamp(pos))
        self.scene_.update()

    def _crop_hover_cursor(self, pos: QPointF):
        hit = self._crop_hit(pos)
        if hit is None:
            cur = Qt.CrossCursor
        elif hit[0] == "move":
            cur = Qt.SizeAllCursor if self.crop_rect != self.scene_.sceneRect() else Qt.CrossCursor
        else:
            cur = self.CURSORS[hit[1]]
        self.viewport().setCursor(cur)

    def apply_crop(self):
        r = self.crop_rect
        if r is None or not self.pixmap_item:
            return
        full = QRect(0, 0, self.pixmap_item.pixmap().width(), self.pixmap_item.pixmap().height())
        ir = r.toRect().intersected(full)
        if ir.width() < MIN_CROP or ir.height() < MIN_CROP or ir == full:
            return
        self.win.undo_stack.push(CropCmd(self, ir))
        self.win.set_tool("select")

    # ----- ratón -----
    def _constrain(self, start: QPointF, pos: QPointF, shift: bool) -> QPointF:
        if not shift:
            return pos
        dx, dy = pos.x() - start.x(), pos.y() - start.y()
        if self.tool == "arrow":
            ang = round(math.atan2(dy, dx) / (math.pi / 4)) * (math.pi / 4)
            dist = math.hypot(dx, dy)
            return QPointF(start.x() + dist * math.cos(ang), start.y() + dist * math.sin(ang))
        side = max(abs(dx), abs(dy))
        return QPointF(start.x() + math.copysign(side, dx or 1), start.y() + math.copysign(side, dy or 1))

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_last = event.position()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            return
        if event.button() != Qt.LeftButton:
            return
        pos = self.mapToScene(event.position().toPoint())
        if self.tool == "select":
            super().mousePressEvent(event)
            self._move_snapshot = {it: QPointF(it.pos()) for it in self.scene_.selectedItems()}
            return
        self.scene_.setFocusItem(None)  # clic afuera cierra un texto en edición
        if not self.pixmap_item:
            return
        if self.tool == "crop":
            self._crop_press(pos)
            return
        if self.tool == "text":
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, EditableTextItem):
                item.start_edit()
                return
            item = EditableTextItem(self.color, self.text_px, self.win.on_text_commit,
                                    self.win.on_text_empty, self.win.on_text_edited)
            self.add_item(item)
            item.setPos(pos.x(), pos.y() - item.boundingRect().height() / 2)
            item.start_edit()
            return
        self._start_pos = pos
        if self.tool == "rect":
            item = RectItem(QRectF(pos, pos))
            item.setPen(make_pen(self.color, self.width_px))
        elif self.tool == "ellipse":
            item = EllipseItem(QRectF(pos, pos))
            item.setPen(make_pen(self.color, self.width_px))
        else:
            item = ArrowItem(pos, pos, self.color, self.width_px)
        self._drawing_item = item
        self.add_item(item)

    def mouseMoveEvent(self, event):
        if self._panning:
            d = event.position() - self._pan_last
            self._pan_last = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
            return
        pos = self.mapToScene(event.position().toPoint())
        if self.tool == "crop":
            if self._crop_drag is not None:
                self._crop_move(pos)
            else:
                self._crop_hover_cursor(pos)
            return
        if self._drawing_item is None:
            super().mouseMoveEvent(event)
            return
        pos = self._constrain(self._start_pos, pos, bool(event.modifiers() & Qt.ShiftModifier))
        if self.tool == "arrow":
            self._drawing_item.set_end(pos)
        else:
            self._drawing_item.setRect(QRectF(self._start_pos, pos).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.set_tool(self.tool)  # restaura el cursor de la herramienta
            return
        if self.tool == "crop":
            d, self._crop_drag = self._crop_drag, None
            if d and d["mode"] == "new" and (self.crop_rect is None or
                                             self.crop_rect.width() < 4 or self.crop_rect.height() < 4):
                self.crop_rect = d["prev"]  # fue un clic suelto: se conserva el recorte anterior
                self.scene_.update()
            return
        if self._drawing_item is None:
            super().mouseReleaseEvent(event)
            if self.tool == "select" and self._move_snapshot:
                moves = [(it, old, QPointF(it.pos())) for it, old in self._move_snapshot.items()
                         if it.scene() is self.scene_ and it.pos() != old]
                if moves:
                    self.win.undo_stack.push(MoveCmd(moves))
            self._move_snapshot = None
            return
        item, self._drawing_item = self._drawing_item, None
        end = self._constrain(self._start_pos, self.mapToScene(event.position().toPoint()),
                              bool(event.modifiers() & Qt.ShiftModifier))
        if (end - self._start_pos).manhattanLength() < 4:
            self.scene_.removeItem(item)
            return
        set_movable(item)
        self.win.undo_stack.push(AddCmd(self, item, "Añadir " + self.tool))

    def mouseDoubleClickEvent(self, event):
        if self.tool == "crop":
            self.apply_crop()
            return
        if self.tool in ("select", "text"):
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, EditableTextItem) and item.committed:
                item.start_edit()
                return
        super().mouseDoubleClickEvent(event)

    def event(self, e):
        # Mientras se escribe un texto, las teclas son del texto y no de los atajos (V, A, R…).
        if e.type() == QEvent.ShortcutOverride:
            f = self.scene_.focusItem()
            if isinstance(f, EditableTextItem) and f.is_editing():
                e.accept()
                return True
        return super().event(e)

    def keyPressEvent(self, event):
        if isinstance(self.scene_.focusItem(), EditableTextItem):
            super().keyPressEvent(event)
            return
        if self.tool == "crop" and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.apply_crop()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.win.delete_selected()
            return
        super().keyPressEvent(event)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if not self.pixmap_item:
            return
        s = self._px()
        base = self.scene_.sceneRect()
        painter.setPen(Qt.NoPen)
        for i in range(8, 0, -1):  # sombra suave alrededor de la imagen
            painter.setBrush(QColor(0, 0, 0, 12))
            painter.drawRoundedRect(base.adjusted(-i * s, -i * s + 3 * s, i * s, i * s + 3 * s), 3 * s, 3 * s)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if self.pixmap_item:
            return
        painter.resetTransform()
        painter.setPen(QColor(MUTED))
        font = QFont()
        font.setPixelSize(16)
        painter.setFont(font)
        painter.drawText(self.viewport().rect(), Qt.AlignCenter,
                         "Arrastrá una imagen o carpeta acá\no usá Ctrl+O para abrir")


# ---------------------------------------------------------------- ventana
RATIOS = [("Libre", None), ("1:1", 1.0), ("4:3", 4 / 3), ("3:2", 3 / 2),
          ("16:9", 16 / 9), ("9:16", 9 / 16), ("3:4", 3 / 4)]

TOOLS = [
    ("select", "Seleccionar", "V", "Mover, editar y borrar anotaciones"),
    ("arrow", "Flecha", "A", "Arrastrá para dibujar · Shift: ángulos de 45°"),
    ("rect", "Rectángulo", "R", "Arrastrá para dibujar · Shift: cuadrado"),
    ("ellipse", "Círculo", "O", "Arrastrá para dibujar · Shift: círculo perfecto"),
    ("text", "Texto", "T", "Clic y escribí · Esc o clic afuera para terminar"),
    ("crop", "Recortar", "C", "Arrastrá los bordes · Enter aplica · Esc cancela"),
]


class MainWindow(QMainWindow):
    def __init__(self, start_path: Path | None):
        super().__init__()
        self.setWindowTitle("Img Annotator")
        self.resize(1200, 820)
        self.setAcceptDrops(True)

        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)

        self.images: list[Path] = []
        self.index = -1
        self.style_dirty = False
        self._text_size_user = False
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(lambda _: self.refresh_title())
        self.undo_stack.indexChanged.connect(self._update_dims)

        self._build_toolbars()
        self._build_status()
        self.canvas.zoomChanged.connect(self._on_zoom)
        self.set_tool("select")

        if start_path:
            self.open_path(start_path)
        else:
            QTimer.singleShot(0, self.action_open)

    # ---------- construcción ----------
    def _cap(self, text):
        lab = QLabel(text)
        lab.setObjectName("cap")
        return lab

    def _build_toolbars(self):
        tools = QToolBar("Herramientas")
        tools.setObjectName("tools")
        tools.setMovable(False)
        tools.setOrientation(Qt.Vertical)
        tools.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.LeftToolBarArea, tools)

        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_hints = {}
        for key, name, shortcut, hint in TOOLS:
            act = QAction(make_icon(key), name, self)
            act.setToolTip(f"{name} ({shortcut})")
            act.setShortcut(shortcut)
            act.setCheckable(True)
            act.setData(key)
            self.tool_group.addAction(act)
            tools.addAction(act)
            self.tool_hints[key] = hint
            if key == "text":
                tools.addSeparator()
        self.tool_group.triggered.connect(lambda a: self.set_tool(a.data()))

        esc = QAction(self)
        esc.setShortcut("Esc")
        esc.triggered.connect(lambda: self.set_tool("select"))
        self.addAction(esc)

        opts = QToolBar("Opciones")
        opts.setObjectName("options")
        opts.setMovable(False)
        opts.setFloatable(False)
        self.addToolBar(Qt.TopToolBarArea, opts)
        self.opt_actions = {}

        # color
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.swatches = []
        for col in PRESET_COLORS:
            sw = Swatch(col)
            sw.clicked.connect(partial(self.on_swatch, sw))
            lay.addWidget(sw)
            self.swatches.append(sw)
        self.custom_swatch = Swatch("#ff3b30", custom=True)
        self.custom_swatch.clicked.connect(partial(self.on_swatch, self.custom_swatch))
        lay.addWidget(self.custom_swatch)
        self.swatches.append(self.custom_swatch)
        self.opt_actions["color"] = opts.addWidget(box)
        self.swatches[0].setChecked(True)

        # grosor
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._cap("Grosor"))
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 60)
        self.width_slider.setFixedWidth(110)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 60)
        self.width_spin.setSuffix(" px")
        self.width_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.width_spin.setFixedWidth(64)
        self.width_slider.setValue(DEFAULT_WIDTH)
        self.width_spin.setValue(DEFAULT_WIDTH)
        self.width_slider.valueChanged.connect(self.set_width)
        self.width_spin.valueChanged.connect(self.set_width)
        lay.addWidget(self.width_slider)
        lay.addWidget(self.width_spin)
        self.opt_actions["width"] = opts.addWidget(box)

        # tamaño de texto
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._cap("Texto"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 600)
        self.size_spin.setSuffix(" px")
        self.size_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.size_spin.setFixedWidth(64)
        self.size_spin.setToolTip("Tamaño del texto (rueda del ratón para ajustar)")
        self.size_spin.setValue(self.canvas.text_px)
        self.size_spin.valueChanged.connect(self.on_text_size)
        lay.addWidget(self.size_spin)
        self.opt_actions["size"] = opts.addWidget(box)

        # recorte
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self._cap("Proporción"))
        self.ratio_combo = QComboBox()
        for name, _ in RATIOS:
            self.ratio_combo.addItem(name)
        self.ratio_combo.currentIndexChanged.connect(lambda i: self.canvas.set_crop_ratio(RATIOS[i][1]))
        lay.addWidget(self.ratio_combo)
        apply_btn = QPushButton("Aplicar recorte")
        apply_btn.setObjectName("accent")
        apply_btn.clicked.connect(self.canvas.apply_crop)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(lambda: self.set_tool("select"))
        lay.addWidget(apply_btn)
        lay.addWidget(cancel_btn)
        self.opt_actions["crop"] = opts.addWidget(box)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        opts.addWidget(spacer)

        # historial y archivo
        self.undo_act = QAction(make_icon("undo"), "Deshacer", self)
        self.undo_act.setShortcut(QKeySequence.Undo)
        self.undo_act.setToolTip("Deshacer (Ctrl+Z)")
        self.undo_act.triggered.connect(self.undo_stack.undo)
        self.redo_act = QAction(make_icon("redo"), "Rehacer", self)
        self.redo_act.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        self.redo_act.setToolTip("Rehacer (Ctrl+Shift+Z)")
        self.redo_act.triggered.connect(self.undo_stack.redo)
        self.undo_stack.canUndoChanged.connect(self.undo_act.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.redo_act.setEnabled)
        self.undo_act.setEnabled(False)
        self.redo_act.setEnabled(False)
        opts.addAction(self.undo_act)
        opts.addAction(self.redo_act)

        clear_act = QAction("Borrar todo", self)
        clear_act.setShortcut("Ctrl+Shift+Delete")
        clear_act.triggered.connect(self.clear_annotations)
        self.addAction(clear_act)

        opts.addSeparator()
        for text, slot, name in (("Abrir", self.action_open, None), ("Copiar", self.copy_image, None)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            opts.addWidget(b)
        save_btn = QPushButton("Guardar como…")
        save_btn.setObjectName("accent")
        save_btn.clicked.connect(self.save_as)
        opts.addWidget(save_btn)

        for text, key, slot in (("Abrir", QKeySequence.Open, self.action_open),
                                ("Guardar", QKeySequence.Save, self.save_as),
                                ("Copiar", QKeySequence.Copy, self.copy_image),
                                ("Anterior", "Left", self.go_prev), ("Anterior", "PgUp", self.go_prev),
                                ("Siguiente", "Right", self.go_next), ("Siguiente", "PgDown", self.go_next),
                                ("Ajustar", "Ctrl+0", self.canvas.fit),
                                ("100%", "Ctrl+1", lambda: self.canvas.set_zoom(1.0)),
                                ("Acercar", "Ctrl++", lambda: self.canvas.set_zoom(self.canvas.transform().m11() * 1.25)),
                                ("Alejar", "Ctrl+-", lambda: self.canvas.set_zoom(self.canvas.transform().m11() / 1.25))):
            a = QAction(text, self)
            a.setShortcut(key)
            a.triggered.connect(slot)
            self.addAction(a)

    def _build_status(self):
        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        self.setStatusBar(self.status)
        self.hint_label = QLabel("")
        self.status.addWidget(self.hint_label, 1)
        self.info_label = QLabel("")
        self.dim_label = QLabel("")
        self.zoom_label = QLabel("")
        for w in (self.info_label, self.dim_label, self.zoom_label):
            self.status.addPermanentWidget(w)

    # ---------- herramientas y estilo ----------
    def set_tool(self, tool: str):
        for a in self.tool_group.actions():
            if a.data() == tool:
                a.setChecked(True)
        self.canvas.set_tool(tool)
        show = {
            "color": tool != "crop",
            "width": tool in ("select", "arrow", "rect", "ellipse"),
            "size": tool in ("select", "text"),
            "crop": tool == "crop",
        }
        for k, v in show.items():
            self.opt_actions[k].setVisible(v)
        self.hint_label.setText(self.tool_hints.get(tool, ""))

    def set_color(self, color: QColor):
        self.canvas.color = QColor(color)
        for sw in self.swatches:
            sw.setChecked(sw.picked and sw.color == color)
        self.canvas.apply_style(color=QColor(color))

    def on_swatch(self, sw: Swatch):
        if sw.custom:
            col = QColorDialog.getColor(self.canvas.color, self, "Color de anotación")
            if not col.isValid():
                for s in self.swatches:
                    s.setChecked(s.picked and s.color == self.canvas.color)
                return
            sw.color, sw.picked = col, True
            sw.update()
            self.set_color(col)
        else:
            self.set_color(sw.color)

    def set_width(self, v: int):
        self.canvas.width_px = v
        for w in (self.width_slider, self.width_spin):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)
        self.canvas.apply_style(width=v)

    def on_text_size(self, v: int):
        self._text_size_user = True
        self.canvas.text_px = v
        self.canvas.apply_style(size=v)

    # ---------- texto ----------
    def on_text_commit(self, item):
        self.undo_stack.push(AddCmd(self.canvas, item, "Añadir texto"))

    def on_text_empty(self, item):
        def remove():
            try:
                if item.scene() is self.canvas.scene_:
                    if item.committed:
                        self.undo_stack.push(DeleteCmd(self.canvas, [item], "Borrar texto"))
                    else:
                        self.canvas.scene_.removeItem(item)
            except RuntimeError:
                pass  # el item ya no existe (se cargó otra imagen)
        QTimer.singleShot(0, remove)

    def on_text_edited(self, item, before, after):
        self.undo_stack.push(EditTextCmd(item, before, after))

    # ---------- deshacer ----------
    def delete_selected(self):
        items = [it for it in self.canvas.scene_.selectedItems()
                 if it is not self.canvas.pixmap_item and it is not self.canvas.overlay]
        if items:
            self.undo_stack.push(DeleteCmd(self.canvas, items))

    def clear_annotations(self):
        items = self.canvas.annotation_items()
        if items:
            self.undo_stack.push(DeleteCmd(self.canvas, items, "Borrar todo"))

    @property
    def dirty(self) -> bool:
        return (not self.undo_stack.isClean()) or self.style_dirty

    def mark_clean(self):
        self.undo_stack.setClean()
        self.style_dirty = False
        self.refresh_title()

    def refresh_title(self):
        name = self.images[self.index].name if 0 <= self.index < len(self.images) else ""
        dot = "● " if self.dirty else ""
        self.setWindowTitle(f"{dot}{name} — Img Annotator" if name else "Img Annotator")

    # ---------- navegación de archivos ----------
    def open_path(self, path: Path):
        path = path.resolve()
        if path.is_dir():
            folder, target = path, None
        else:
            folder, target = path.parent, path
        images = sorted((p for p in folder.iterdir() if p.suffix.lower() in IMG_EXTS), key=natural_key)
        if not images:
            QMessageBox.warning(self, "Img Annotator", "No hay imágenes en esa carpeta.")
            return
        if not self._confirm_discard():
            return
        self.images = images
        self.index = images.index(target) if target in images else 0
        self.load_current()

    def load_current(self):
        path = self.images[self.index]
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            QMessageBox.warning(self, "Img Annotator", f"No se pudo abrir {path.name}")
            return
        self.undo_stack.clear()
        self.canvas.load_pixmap(pixmap)
        if not self._text_size_user:  # tamaño de texto proporcional a la imagen
            px = min(max(round(pixmap.height() / 28), 18), 140)
            self.canvas.text_px = px
            self.size_spin.blockSignals(True)
            self.size_spin.setValue(px)
            self.size_spin.blockSignals(False)
        self.mark_clean()
        self.info_label.setText(f"{self.index + 1} / {len(self.images)}  ·  {path.name}")
        self._update_dims()

    def _update_dims(self, *_):
        if self.canvas.pixmap_item:
            pm = self.canvas.pixmap_item.pixmap()
            self.dim_label.setText(f"{pm.width()} × {pm.height()} px")

    def _on_zoom(self, factor: float, fit: bool):
        self.zoom_label.setText(f"{'Ajustado · ' if fit else ''}{round(factor * 100)} %")

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        res = QMessageBox.question(
            self, "Cambios sin guardar",
            "Esta imagen tiene cambios sin guardar. ¿Descartar y continuar?",
            QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel,
        )
        return res == QMessageBox.Discard

    def go_next(self):
        if self.index + 1 >= len(self.images) or not self._confirm_discard():
            return
        self.index += 1
        self.load_current()

    def go_prev(self):
        if self.index - 1 < 0 or not self._confirm_discard():
            return
        self.index -= 1
        self.load_current()

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.open_path(Path(urls[0].toLocalFile()))

    # ---------- abrir / guardar / copiar ----------
    def action_open(self):
        start_dir = str(self.images[self.index].parent) if self.images else str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Abrir imagen", start_dir,
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff)",
        )
        if file_path:
            self.open_path(Path(file_path))

    def render_image(self, opaque: bool = False) -> QImage:
        cv = self.canvas
        cv.scene_.clearSelection()
        cv.scene_.setFocusItem(None)
        was_visible = cv.overlay.isVisible()
        cv.overlay.setVisible(False)
        rect = cv.scene_.sceneRect()
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format_ARGB32)
        image.fill(Qt.white if opaque else Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        cv.scene_.render(painter, QRectF(image.rect()), rect)
        painter.end()
        cv.overlay.setVisible(was_visible)
        return image

    def copy_image(self):
        if not self.canvas.pixmap_item:
            return
        QApplication.clipboard().setImage(self.render_image())
        self.status.showMessage("Copiada al portapapeles", 3000)

    def save_as(self):
        if not self.images or not self.canvas.pixmap_item:
            return
        current = self.images[self.index]
        suggested = current.with_name(f"{current.stem}_edit{current.suffix}")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar como", str(suggested),
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;Todos (*)",
        )
        if not file_path:
            return
        opaque = Path(file_path).suffix.lower() in (".jpg", ".jpeg")
        if self.render_image(opaque).save(file_path):
            self.mark_clean()
            self.status.showMessage(f"Guardado: {file_path}", 5000)
        else:
            QMessageBox.warning(self, "Img Annotator", "No se pudo guardar el archivo.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Img Annotator")
    app.setDesktopFileName("img-annotator")
    apply_theme(app)
    here = Path(__file__).resolve().parent
    app.setWindowIcon(QIcon.fromTheme("img-annotator", QIcon(str(here / "img-annotator.svg"))))
    start_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    win = MainWindow(start_path)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
