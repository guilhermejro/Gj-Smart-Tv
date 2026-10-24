"""Lista de cards de canais (virtualizada) e cache assíncrono de logotipos."""
from PySide6.QtCore import QObject, QRect, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QListView, QListWidget, QListWidgetItem, QStyle, QStyledItemDelegate

from app.utils.url import host_is_private

CARD_W, CARD_H = 150, 128


class LogoCache(QObject):
    loaded = Signal()
    MAX_ITEMS, MAX_BYTES, MAX_PENDING = 400, 2_000_000, 6

    def __init__(self):
        super().__init__()
        self._nam = QNetworkAccessManager(self)
        self._cache, self._pending, self._failed = {}, set(), set()

    def get(self, url: str):
        if url in self._cache:
            return self._cache[url]
        if url in self._pending or url in self._failed:
            return None
        if not url.lower().startswith(("http://", "https://")) or host_is_private(QUrl(url).host()):
            self._failed.add(url)  # logos nunca consultam localhost/rede local (evita varredura via playlist)
            return None
        if len(self._pending) >= self.MAX_PENDING:
            return None
        self._pending.add(url)
        req = QNetworkRequest(QUrl(url))
        req.setTransferTimeout(8000)
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        reply = self._nam.get(req)
        reply.finished.connect(lambda r=reply, u=url: self._done(r, u))
        return None

    def _done(self, reply: QNetworkReply, url: str):
        self._pending.discard(url)
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        data = bytes(reply.readAll()) if ok else b""
        reply.deleteLater()
        img = QImage()
        if data and len(data) <= self.MAX_BYTES and img.loadFromData(data) and not img.isNull():
            if len(self._cache) >= self.MAX_ITEMS:
                self._cache.pop(next(iter(self._cache)))
            self._cache[url] = QPixmap.fromImage(
                img.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self._failed.add(url)
        self.loaded.emit()


LOGOS = None


def logo_cache() -> LogoCache:
    global LOGOS
    if LOGOS is None:
        LOGOS = LogoCache()
    return LOGOS


class CardDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(CARD_W, CARD_H)

    def paint(self, p: QPainter, option, index):
        ch = index.data(Qt.UserRole)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = option.rect.adjusted(4, 4, -4, -4)
        active = bool(option.state & (QStyle.State_Selected | QStyle.State_MouseOver))
        path = QPainterPath()
        path.addRoundedRect(QRectF(r), 14, 14)
        p.fillPath(path, QColor("#252A40" if active else "#1A1D29"))
        if option.state & QStyle.State_Selected:
            p.setPen(QPen(QColor("#4C7DFF"), 2))
            p.drawPath(path)
        box = QRect(r.left() + (r.width() - 64) // 2, r.top() + 12, 64, 64)
        pm = logo_cache().get(ch.logo) if ch.logo else None
        if pm:
            scaled = pm.scaled(box.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(box.left() + (64 - scaled.width()) // 2, box.top() + (64 - scaled.height()) // 2, scaled)
        else:
            grad = QLinearGradient(box.topLeft(), box.bottomRight())
            grad.setColorAt(0, QColor("#4C7DFF"))
            grad.setColorAt(1, QColor("#8B5CF6"))
            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawEllipse(box)
            f = QFont(p.font())
            f.setBold(True)
            f.setPointSize(16)
            p.setFont(f)
            p.setPen(QColor("white"))
            p.drawText(box, Qt.AlignCenter, ch.initials)
        p.setPen(QColor("#E8EAF2"))
        f = QFont(p.font())
        f.setBold(False)
        f.setPointSize(10)
        p.setFont(f)
        text_rect = QRect(r.left() + 8, r.top() + 84, r.width() - 16, 34)
        elided = p.fontMetrics().elidedText(ch.name, Qt.ElideRight, text_rect.width() * 2)
        p.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, elided)
        p.restore()


class ChannelList(QListWidget):
    channelActivated = Signal(object)

    def __init__(self, horizontal: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("channels")
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        self.setItemDelegate(CardDelegate(self))
        self.setMouseTracking(True)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setHorizontalScrollMode(QListWidget.ScrollPerPixel)
        if horizontal:
            self.setFlow(QListView.LeftToRight)
            self.setWrapping(False)
            self.setFixedHeight(CARD_H + 26)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        logo_cache().loaded.connect(self.viewport().update)
        self.itemActivated.connect(lambda it: self.channelActivated.emit(it.data(Qt.UserRole)))
        self.itemClicked.connect(lambda it: self.channelActivated.emit(it.data(Qt.UserRole)))

    def set_channels(self, channels):
        self.setUpdatesEnabled(False)
        self.clear()
        for ch in channels:
            it = QListWidgetItem()
            it.setData(Qt.UserRole, ch)
            it.setSizeHint(QSize(CARD_W, CARD_H))
            it.setToolTip(ch.name)
            self.addItem(it)
        self.setUpdatesEnabled(True)
        if self.count():
            self.setCurrentRow(0)
