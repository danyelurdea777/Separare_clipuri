"""Separare Clipuri: muti clipurile transcodate in foldere pe categorii, din miniaturi, ca in Adobe Bridge."""
import sys, os, json, shutil, subprocess, hashlib, time, errno
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import (Qt, QAbstractListModel, QModelIndex, QSize, QRect, QTimer, QUrl, QMimeData,
                            QRunnable, QThreadPool, QObject, Signal, QEvent, QItemSelectionModel, QItemSelection, QByteArray, QFile)
from PySide6.QtGui import (QPainter, QColor, QPen, QPixmap, QPixmapCache, QFont, QKeySequence, QShortcut,
                           QIcon, QDesktopServices, QFontMetrics, QPainterPath)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListView,
                               QLabel, QFileDialog, QInputDialog, QSlider, QCheckBox, QComboBox, QMessageBox,
                               QAbstractItemView, QSplitter, QLineEdit, QStyledItemDelegate, QStyle, QMenu, QToolButton,
                               QProgressBar, QSpinBox, QScrollArea, QColorDialog, QProgressDialog, QDialog, QTextBrowser,
                               QSizePolicy, QFrame)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

MAC = sys.platform == 'darwin'
WIN = os.name == 'nt'
if getattr(sys, 'frozen', False):
    # aplicatie impachetata (.exe): resursele sunt in pachet, datele in profilul utilizatorului
    APP_DIR = Path(sys._MEIPASS)
    _user = os.environ.get('LOCALAPPDATA') or Path.home() / 'Library' / 'Application Support'
    _default_data = Path(_user) / 'SeparareClipuri'
else:
    APP_DIR = Path(__file__).resolve().parent
    _default_data = APP_DIR / 'data'
DATA = Path(os.environ.get('SEPARARE_DATA', _default_data))  # alt folder doar pentru teste
THUMBS = DATA / 'thumbs'
VERSION = (APP_DIR / 'VERSIUNE').read_text().strip() if (APP_DIR / 'VERSIUNE').exists() else ''
SETTINGS_FILE = DATA / 'setari.json'
META_FILE = DATA / 'metadate.json'
JOURNAL_FILE = DATA / 'jurnal.jsonl'

EXT = {'.mp4', '.mov', '.m4v', '.mxf', '.mkv', '.avi', '.mts', '.m2ts', '.insv'}
# fisiere insotitoare cu acelasi nume (DJI .LRF/.SRT, Sony .XML, GoPro .THM), mutate impreuna cu clipul
SIDECAR = {'.xml', '.lrf', '.srt', '.thm', '.lrv', '.xmp'}
FRAMES = 8      # cadre per clip pentru derularea la trecerea mouse-ului
POSTER = 1      # cadrul afisat implicit
THUMB_W = 320
COLORS = ['#3b82c4', '#2f9e74', '#c9822b', '#a855c7', '#c94f4f', '#3fa7b8', '#8a9a2f', '#c46a9b', '#6b7bd6', '#9a7b4f', '#5aa05a', '#b5654f']
TEMPLATES = {
    'Botez (arhiva mea)': ['Acasa', 'Biserica', 'Restaurant', 'Sedinta Video', 'Interviuri', 'dji mini pro 4'],
    'Nunta': ['Pregatiri', 'Juraminte', 'Biserica', 'Cununie civila', 'Sedinta Video', 'Restaurant',
              'Trash the dress', 'Save the date', 'Interviuri', 'dji mini pro 4'],
}
DEFAULT_TEMPLATE = 'Botez (arhiva mea)'


NO_WINDOW = subprocess.CREATE_NO_WINDOW if WIN else 0  # fara ferestre de consola pe Windows


def find_tool(name):
    # intai ffmpeg-ul livrat cu aplicatia, apoi PATH, apoi locurile uzuale pe Mac (din .app PATH-ul e scurt)
    exe = name + '.exe' if WIN else name
    for folder in (APP_DIR / 'ffmpeg', APP_DIR):
        if (folder / exe).is_file():
            return str(folder / exe)
    found = shutil.which(name)
    if found:
        return found
    for folder in ('/opt/local/bin', '/usr/local/bin', '/opt/homebrew/bin'):
        if os.access(f'{folder}/{name}', os.X_OK):
            return f'{folder}/{name}'
    return None


def ui(text):
    """Textele interfetei pentru platforma curenta: pe Windows Cmd devine Ctrl si Finder devine Explorer."""
    if MAC:
        return text
    return (text.replace('Cmd', 'Ctrl').replace('Finder', 'Explorer').replace('Cosul macOS', 'Cosul de reciclare')
            .replace(ui('in IINA'), 'in player').replace(ui('IINA'), 'player'))


def open_path(path, reveal=False):
    """Deschide un fisier/folder cu aplicatia implicita, sau il arata selectat in Finder / Explorer."""
    path = str(path)
    if MAC:
        subprocess.Popen(['open', '-R', path] if reveal else ['open', path])
    elif WIN:
        if reveal:
            subprocess.Popen(['explorer', '/select,', path])
        else:
            os.startfile(path)
    else:
        subprocess.Popen(['xdg-open', os.path.dirname(path) if reveal else path])


FFMPEG, FFPROBE = find_tool('ffmpeg'), find_tool('ffprobe')


def human_size(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024 or unit == 'TB':
            return f'{n:.1f} {unit}'.replace('.', ',') if unit in ('GB', 'TB') else f'{n:.0f} {unit}'
        n /= 1024


def human_dur(seconds):
    s = int(round(seconds))
    return f'{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}' if s >= 3600 else f'{s // 60}:{s % 60:02d}'


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def save_json(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)


def clean_name(text):
    return ' '.join(text.replace('/', '-').replace(':', '-').split()).strip(' .')


@dataclass
class Clip:
    path: Path
    size: int
    mtime: float
    key: str
    duration: float = 0.0
    created: float = 0.0
    codec: str = ''
    width: int = 0
    height: int = 0
    fps: float = 0.0
    audio: str = ''
    group: int = 0

    @property
    def name(self):
        return self.path.name

    def badge(self):
        res = '8K' if self.width >= 7000 else '6K' if self.width >= 5500 else '4K' if self.width >= 3800 else \
            '2.7K' if self.width >= 2700 else '1080' if self.width >= 1900 else f'{self.height}p' if self.height else ''
        fps = f' {self.fps:g}p' if self.fps else ''
        return (res + fps).strip()


def probe(path):
    """Durata, codec, rezolutie si ora filmarii, citite cu ffprobe."""
    meta = {'duration': 0.0, 'created': 0.0, 'codec': '', 'width': 0, 'height': 0, 'fps': 0.0, 'audio': ''}
    if not FFPROBE:
        return meta
    try:
        out = subprocess.run([FFPROBE, '-v', 'error', '-show_entries',
                              'format=duration:format_tags=creation_time:stream=codec_type,codec_name,width,height,r_frame_rate',
                              '-of', 'json', str(path)], capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW).stdout
        data = json.loads(out or '{}')
    except (OSError, subprocess.SubprocessError, ValueError):
        return meta
    fmt = data.get('format', {})
    meta['duration'] = float(fmt.get('duration') or 0)
    stamp = (fmt.get('tags') or {}).get('creation_time')
    if stamp:
        try:
            meta['created'] = datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp()
        except ValueError:
            pass
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'video' and not meta['codec']:
            meta['codec'] = stream.get('codec_name', '')
            meta['width'], meta['height'] = stream.get('width', 0), stream.get('height', 0)
            num, _, den = (stream.get('r_frame_rate') or '0/1').partition('/')
            try:
                meta['fps'] = round(float(num) / float(den or 1), 2)
            except (ValueError, ZeroDivisionError):
                pass
        elif stream.get('codec_type') == 'audio' and not meta['audio']:
            meta['audio'] = stream.get('codec_name', '')
    return meta


def clip_key(name, size, mtime):
    # cheia nu depinde de folder, ca miniaturile sa ramana valabile dupa mutare
    return hashlib.md5(f'{name}|{size}|{int(mtime)}'.encode()).hexdigest()[:16]


def list_clips(folder):
    clips = []
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return clips
    for entry in entries:
        if entry.name.startswith('.') or Path(entry.name).suffix.lower() not in EXT:
            continue
        try:
            if not entry.is_file():
                continue
            st = entry.stat()
        except OSError:
            continue
        clips.append(Clip(Path(entry.path), st.st_size, st.st_mtime, clip_key(entry.name, st.st_size, st.st_mtime)))
    return clips


def count_videos(folder):
    try:
        return sum(1 for e in os.scandir(folder) if not e.name.startswith('.') and Path(e.name).suffix.lower() in EXT)
    except OSError:
        return 0


def sidecars(path):
    stem = path.stem.lower()
    try:
        return [Path(e.path) for e in os.scandir(path.parent)
                if Path(e.name).stem.lower() == stem and Path(e.name).suffix.lower() in SIDECAR and e.name != path.name]
    except OSError:
        return []


def frame_file(key, index):
    return THUMBS / f'{key}_{index}.jpg'


def assign_groups(clips, gap_minutes):
    """Grupuri de filmare: un grup nou incepe dupa o pauza mai mare decat gap_minutes."""
    ordered = sorted(clips, key=lambda c: (c.created, c.name))
    group, last_end = 0, None
    for clip in ordered:
        if last_end is not None and clip.created - last_end > gap_minutes * 60:
            group += 1
        clip.group = group + 1
        last_end = max(last_end or 0, clip.created + clip.duration)


def group_color(group):
    return QColor.fromHsv((group * 67 + 200) % 360, 150, 215)


# ---------------------------------------------------------------- lucru in fundal

class Signals(QObject):
    frame_done = Signal(str, int)
    frame_failed = Signal(str, int)
    move_progress = Signal(int, int, int, str)
    move_done = Signal(int, list)


class FrameJob(QRunnable):
    def __init__(self, key, index, path, seconds, signals):
        super().__init__()
        self.key, self.index, self.path, self.seconds, self.signals = key, index, path, seconds, signals

    def run(self):
        target = frame_file(self.key, self.index)
        try:
            if not target.exists():
                tmp = target.with_name(target.stem + '.part.jpg')
                subprocess.run([FFMPEG, '-v', 'error', '-nostdin', '-ss', f'{self.seconds:.2f}', '-i', str(self.path),
                                '-frames:v', '1', '-vf', f'scale={THUMB_W}:-2', '-q:v', '5', '-y', str(tmp)],
                               capture_output=True, timeout=90, creationflags=NO_WINDOW)
                if tmp.exists() and tmp.stat().st_size:
                    tmp.replace(target)
        except (OSError, subprocess.SubprocessError):
            pass
        if target.exists():
            self.signals.frame_done.emit(self.key, self.index)
        else:
            self.signals.frame_failed.emit(self.key, self.index)


def rename_retry(src, dst):
    # pe Windows un fisier deschis (previzualizare, miniatura in lucru) nu poate fi mutat cateva clipe
    for attempt in range(20):
        try:
            return os.rename(src, dst)
        except PermissionError:
            if not WIN or attempt == 19:
                raise
            time.sleep(0.3)


class MoveJob(QRunnable):
    """Muta o lista de fisiere; pe acelasi disc e redenumire instantanee, intre discuri copiere + stergere."""
    def __init__(self, batch_id, pairs, label, signals):
        super().__init__()
        self.batch_id, self.pairs, self.label, self.signals = batch_id, pairs, label, signals

    def run(self):
        errors = []
        for done, (src, dst) in enumerate(self.pairs, 1):
            try:
                if os.path.exists(dst):
                    raise FileExistsError(f'exista deja: {dst}')
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                try:
                    rename_retry(src, dst)
                except OSError as exc:
                    if exc.errno != errno.EXDEV and getattr(exc, 'winerror', None) != 17:  # alt disc
                        raise
                    shutil.copy2(src, dst + '.partial')
                    if os.path.getsize(dst + '.partial') != os.path.getsize(src):
                        raise OSError('copia are alta marime decat originalul')
                    os.rename(dst + '.partial', dst)
                    os.remove(src)
            except OSError as exc:
                errors.append(f'{os.path.basename(src)}: {exc}')
            self.signals.move_progress.emit(self.batch_id, done, len(self.pairs), self.label)
        self.signals.move_done.emit(self.batch_id, errors)


# ---------------------------------------------------------------- grila de miniaturi

class ClipModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.clips = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.clips)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        clip = self.clips[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return clip.name
        if role == Qt.ItemDataRole.UserRole:
            return clip
        if role == Qt.ItemDataRole.ToolTipRole:
            when = datetime.fromtimestamp(clip.created).strftime('%d.%m.%Y %H:%M:%S') if clip.created else '?'
            return (f'{clip.name}\n{human_dur(clip.duration)} · {human_size(clip.size)} · {clip.codec} {clip.width}x{clip.height} '
                    f'{clip.fps:g} fps\nFilmat: {when} · Grup {clip.group}')
        return None

    def flags(self, index):
        base = super().flags(index)
        return base | Qt.ItemFlag.ItemIsDragEnabled if index.isValid() else base

    def mimeTypes(self):
        return ['text/uri-list']

    def mimeData(self, indexes):
        # tragere in DaVinci Resolve sau Finder (copiere), sau pe un buton de folder (mutare)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.clips[i.row()].path)) for i in indexes if i.isValid()])
        return mime

    def supportedDragActions(self):
        return Qt.DropAction.CopyAction

    def set_clips(self, clips):
        self.beginResetModel()
        self.clips = list(clips)
        self.endResetModel()

    def remove_paths(self, paths):
        for row in range(len(self.clips) - 1, -1, -1):
            if self.clips[row].path in paths:
                self.beginRemoveRows(QModelIndex(), row, row)
                del self.clips[row]
                self.endRemoveRows()

    def refresh_key(self, key):
        for row, clip in enumerate(self.clips):
            if clip.key == key:
                idx = self.index(row)
                self.dataChanged.emit(idx, idx)


class Grid(QListView):
    """Grila cu selectie multipla (click, Cmd, Shift, dreptunghi) si derulare la trecerea mouse-ului."""
    def __init__(self):
        super().__init__()
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionRectVisible(True)
        self.setUniformItemSizes(True)
        self.setMouseTracking(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setSpacing(4)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(24)
        self.hover_row, self.hover_frac = -1, 0.0

    def _update_row(self, row):
        if 0 <= row < self.model().rowCount():
            self.viewport().update(self.visualRect(self.model().index(row)))

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        old = self.hover_row
        if index.isValid():
            rect = self.visualRect(index)
            self.hover_row = index.row()
            self.hover_frac = min(0.999, max(0.0, (pos.x() - rect.x()) / max(1, rect.width())))
        else:
            self.hover_row = -1
        self._update_row(old)
        self._update_row(self.hover_row)

    def leaveEvent(self, event):
        old, self.hover_row = self.hover_row, -1
        self._update_row(old)
        super().leaveEvent(event)


class ClipDelegate(QStyledItemDelegate):
    def __init__(self, window):
        super().__init__()
        self.win = window

    def sizeHint(self, option, index):
        w = self.win.thumb_w
        return QSize(w + 8, int(w * 9 / 16) + 52)

    def paint(self, painter, option, index):
        clip = index.data(Qt.ItemDataRole.UserRole)
        grid = self.win.grid
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        r = option.rect.adjusted(4, 4, -4, -4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#2a4d63' if selected else '#1c232c'))
        painter.drawRoundedRect(r, 6, 6)
        img = QRect(r.x(), r.y(), r.width(), int(r.width() * 9 / 16))
        hovering = grid.hover_row == index.row()
        frame = min(FRAMES - 1, int(grid.hover_frac * FRAMES)) if hovering else POSTER
        pix = self.win.frame_pixmap(clip, frame)
        painter.setBrush(QColor('#0b0e12'))
        painter.drawRect(img)
        if pix:
            scaled = pix.scaled(img.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(img.x() + (img.width() - scaled.width()) // 2, img.y() + (img.height() - scaled.height()) // 2, scaled)
        else:
            painter.setPen(QColor('#5d6b7a'))
            painter.drawText(img, Qt.AlignmentFlag.AlignCenter, 'se pregateste...')
        if hovering:
            painter.fillRect(QRect(img.x(), img.bottom() - 3, int(img.width() * grid.hover_frac), 4), QColor('#ffd166'))
        # banda colorata a grupului de filmare
        painter.fillRect(QRect(r.x(), r.y(), r.width(), 5), group_color(clip.group))
        small = QFont(painter.font())
        small.setPointSize(10)
        painter.setFont(small)
        badge = f'G{clip.group}  {clip.badge()}'
        fm = QFontMetrics(small)
        bw = fm.horizontalAdvance(badge) + 10
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 170))
        painter.drawRoundedRect(QRect(img.x() + 4, img.y() + 9, bw, fm.height() + 2), 4, 4)
        painter.setPen(group_color(clip.group).lighter(130))
        painter.drawText(QRect(img.x() + 9, img.y() + 10, bw, fm.height()), Qt.AlignmentFlag.AlignLeft, badge)
        text_top = img.bottom() + 4
        bold = QFont(painter.font())
        bold.setPointSize(12)
        bold.setBold(True)
        painter.setFont(bold)
        painter.setPen(QColor('#e9edf2'))
        dur = human_dur(clip.duration)
        dur_w = QFontMetrics(bold).horizontalAdvance(dur) + 6
        name_rect = QRect(r.x() + 6, text_top, r.width() - dur_w - 12, 20)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         QFontMetrics(bold).elidedText(clip.name, Qt.TextElideMode.ElideMiddle, name_rect.width()))
        painter.setPen(QColor('#ffd166'))
        painter.drawText(QRect(r.right() - dur_w - 4, text_top, dur_w, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, dur)
        painter.setFont(small)
        painter.setPen(QColor('#9aa8b6'))
        when = datetime.fromtimestamp(clip.created).strftime('%H:%M:%S') if clip.created else ''
        painter.drawText(QRect(r.x() + 6, text_top + 20, r.width() - 12, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f'{when}   {human_size(clip.size)}')
        if selected:
            painter.setPen(QPen(QColor('#74e1ff'), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 6, 6)
        painter.restore()


# ---------------------------------------------------------------- butoanele de folder

class FolderButton(QPushButton):
    """Click = muta selectia aici; accepta si clipuri trase din grila."""
    dropped = Signal()

    def __init__(self, grid):
        super().__init__()
        self.grid = grid
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42)

    def dragEnterEvent(self, event):
        if event.source() is self.grid:
            event.acceptProposedAction()
            self.setDown(True)

    def dragLeaveEvent(self, event):
        self.setDown(False)

    def dropEvent(self, event):
        self.setDown(False)
        event.acceptProposedAction()
        self.dropped.emit()


class PreviewVideo(QVideoWidget):
    clicked = Signal()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------- fereastra principala

class Separator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'Separare Clipuri {VERSION}'.strip())
        for folder in (DATA, THUMBS):
            folder.mkdir(parents=True, exist_ok=True)
        self.settings = load_json(SETTINGS_FILE, {})
        self.settings.setdefault('sabloane', TEMPLATES)
        self.settings.setdefault('proiecte', {})
        self.meta = load_json(META_FILE, {})
        self.thumb_w = int(self.settings.get('marime', 260))
        self.source = None          # folderul cu clipuri nesortate
        self.view_dir = None        # folderul afisat acum (sursa sau o categorie)
        self.dest_root = None
        self.cats = []
        self.all_clips = []
        self.frames = {}            # cheie -> cadre gata
        self.pending = set()
        self.undo_stack = []
        self.batches = {}
        self.next_batch = 1
        self.moving = 0
        self.loaded_preview = None

        self.signals = Signals()
        self.signals.frame_done.connect(self.frame_ready)
        self.signals.frame_failed.connect(lambda k, i: self.pending.discard((k, i)))
        self.signals.move_progress.connect(self.move_progress)
        self.signals.move_done.connect(self.move_done)
        self.thumb_pool = QThreadPool(self)
        self.thumb_pool.setMaxThreadCount(max(2, min(4, (os.cpu_count() or 4) // 2)))
        self.move_pool = QThreadPool(self)
        self.move_pool.setMaxThreadCount(1)   # mutarile ruleaza in ordine, una dupa alta
        QPixmapCache.setCacheLimit(300 * 1024)

        self.build_ui()
        self.setAcceptDrops(True)
        geometry = self.settings.get('geometrie')
        if geometry:
            self.restoreGeometry(QByteArray.fromHex(geometry.encode()))
        else:
            self.resize(1500, 920)
        last = self.settings.get('ultima_sursa')
        if last and Path(last).is_dir():
            QTimer.singleShot(0, lambda: self.open_source(last))

    # ---------- interfata

    def build_ui(self):
        host = QWidget()
        self.setCentralWidget(host)
        outer = QVBoxLayout(host)
        outer.setContentsMargins(10, 8, 10, 6)

        bar = QHBoxLayout()
        outer.addLayout(bar)
        self.btn(bar, 'Deschide folder clipuri', self.choose_source).setToolTip(ui('Cmd+O · sau trage un folder din Finder peste fereastra'))
        self.recent = QComboBox()
        self.recent.setMinimumWidth(200)
        self.recent.setToolTip('Folderele deschise recent')
        self.recent.activated.connect(lambda i: self.open_source(self.recent.itemData(i)))
        bar.addWidget(self.recent, 2)
        self.dest_btn = self.btn(bar, 'Destinatie: -', self.choose_dest)
        self.dest_btn.setToolTip('Folderul in care se creeaza folderele categoriilor')
        bar.addSpacing(10)
        bar.addWidget(QLabel('Ordine'))
        self.sort_box = QComboBox()
        self.sort_box.addItems(['Ora filmarii', 'Nume', 'Durata', 'Marime'])
        self.sort_box.setCurrentIndex(int(self.settings.get('sortare', 0)))
        self.sort_box.currentIndexChanged.connect(self.apply_filter)
        bar.addWidget(self.sort_box)
        bar.addWidget(QLabel('Grup nou dupa'))
        self.gap = QSpinBox()
        self.gap.setRange(1, 240)
        self.gap.setSuffix(' min pauza')
        self.gap.setValue(int(self.settings.get('pauza_grup', 8)))
        self.gap.setToolTip('Clipurile filmate fara pauza mai mare de atat formeaza un grup (G = selecteaza grupul)')
        self.gap.valueChanged.connect(self.regroup)
        bar.addWidget(self.gap)
        bar.addStretch()
        help_btn = self.btn(bar, 'Ajutor', self.show_help)
        help_btn.setFlat(True)
        help_btn.setStyleSheet('color:#7dc6e8; text-decoration:underline;')

        progress_row = QHBoxLayout()
        outer.addLayout(progress_row)
        self.view_label = QLabel('Deschide folderul cu clipurile transcodate')
        self.view_label.setStyleSheet('font-size:15px; font-weight:bold;')
        progress_row.addWidget(self.view_label)
        self.back_btn = self.btn(progress_row, 'Inapoi la nesortate', lambda: self.show_folder(self.source))
        self.back_btn.hide()
        progress_row.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText(ui('Cauta in nume (Cmd+F)'))
        self.search.textChanged.connect(self.apply_filter)
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(220)
        progress_row.addWidget(self.search)
        self.btn(progress_row, 'Selecteaza scurte', self.select_short).setToolTip('Selecteaza clipurile mai scurte decat limita: teste, expunere, porniri din greseala')
        self.short_limit = QSpinBox()
        self.short_limit.setRange(1, 60)
        self.short_limit.setPrefix('sub ')
        self.short_limit.setSuffix(' s')
        self.short_limit.setValue(int(self.settings.get('limita_scurte', 2)))
        progress_row.addWidget(self.short_limit)
        progress_row.addWidget(QLabel('Marime'))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(150, 520)
        self.size_slider.setValue(self.thumb_w)
        self.size_slider.setFixedWidth(120)
        self.size_slider.valueChanged.connect(self.set_thumb_size)
        progress_row.addWidget(self.size_slider)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(320)
        self.progress.setFormat('Sortate %v din %m')
        progress_row.addWidget(self.progress)
        self.undo_btn = self.btn(progress_row, 'Anuleaza ultima mutare', self.undo)
        self.undo_btn.setToolTip(ui('Cmd+Z · muta inapoi ultimul lot, chiar si dupa redeschiderea aplicatiei'))
        self.undo_btn.setEnabled(False)

        split = QSplitter()
        outer.addWidget(split, 1)
        self.split = split

        # stanga: folderele destinatie
        left = QWidget()
        left.setMinimumWidth(240)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)
        head = QLabel('MUTA IN FOLDER')
        head.setStyleSheet('color:#9aa8b6; font-weight:bold;')
        ll.addWidget(head)
        hint = QLabel('Selectezi clipurile, apoi click pe folder, tasta lui sau tragi clipurile peste el.')
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#7d8a98; font-size:11px;')
        ll.addWidget(hint)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cat_host = QWidget()
        self.cat_layout = QVBoxLayout(self.cat_host)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(5)
        scroll.setWidget(self.cat_host)
        ll.addWidget(scroll, 1)
        row = QHBoxLayout()
        ll.addLayout(row)
        self.btn(row, '+ Eticheta', lambda: self.add_category(False)).setToolTip('Adauga o eticheta; folderul se creeaza la prima mutare')
        self.btn(row, '+ Folder nou', lambda: self.add_category(True)).setToolTip(ui('Cmd+N · creeaza imediat folderul pe disc'))
        self.template_btn = QPushButton('Sabloane de foldere')
        self.template_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.template_btn.clicked.connect(self.template_menu)
        ll.addWidget(self.template_btn)
        trash = self.btn(ll, ui('Sterge in Cos  (Cmd+Backspace)'), self.trash_selection)
        trash.setStyleSheet('QPushButton {color:#ffb4b4; background:#4b252b;} QPushButton:hover {background:#6b2f37;}')
        trash.setToolTip(ui('Muta selectia in Cosul macOS (teste, expunere, clipuri pornite din greseala).\nCmd+Z le readuce cat timp nu golesti Cosul.'))
        self.free_label = QLabel('')
        self.free_label.setStyleSheet('color:#7d8a98; font-size:11px;')
        self.free_label.setWordWrap(True)
        ll.addWidget(self.free_label)
        split.addWidget(left)

        # centru: grila
        self.model = ClipModel()
        self.grid = Grid()
        self.grid.setModel(self.model)
        self.grid.setItemDelegate(ClipDelegate(self))
        self.grid.installEventFilter(self)
        self.grid.selectionModel().selectionChanged.connect(self.selection_changed)
        self.grid.selectionModel().currentChanged.connect(self.current_changed)
        self.grid.doubleClicked.connect(lambda _: self.open_external())
        self.grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self.grid_menu)
        split.addWidget(self.grid)

        # dreapta: previzualizare
        right = QWidget()
        right.setMinimumWidth(300)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 0, 0, 0)
        self.video = PreviewVideo()
        self.video.setMinimumHeight(200)
        self.video.clicked.connect(self.toggle_play)
        rl.addWidget(self.video, 3)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.6)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.errorOccurred.connect(lambda e, s: self.statusBar().showMessage('Previzualizare: ' + s, 6000))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.sliderMoved.connect(self.player.setPosition)
        self.player.durationChanged.connect(lambda n: self.slider.setRange(0, n))
        self.player.positionChanged.connect(self.position_changed)
        rl.addWidget(self.slider)
        controls = QHBoxLayout()
        rl.addLayout(controls)
        self.play_btn = self.btn(controls, 'Reda / Pauza', self.toggle_play)
        self.play_btn.setToolTip('Spatiu')
        self.time_label = QLabel('0:00 / 0:00')
        controls.addWidget(self.time_label)
        controls.addStretch()
        self.mute = QCheckBox('Fara sunet')
        self.mute.setChecked(bool(self.settings.get('fara_sunet', False)))
        self.mute.toggled.connect(self.audio.setMuted)
        self.audio.setMuted(self.mute.isChecked())
        controls.addWidget(self.mute)
        speeds = QHBoxLayout()
        rl.addLayout(speeds)
        speeds.addWidget(QLabel('Viteza'))
        self.speed_btns = {}
        for text, rate in (('1x', 1.0), ('2x', 2.0), ('4x', 4.0)):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, r=rate: self.set_rate(r))
            speeds.addWidget(b)
            self.speed_btns[rate] = b
        self.set_rate(float(self.settings.get('viteza', 1.0)))
        self.autoplay = QCheckBox('Reda automat clipul selectat')
        self.autoplay.setChecked(bool(self.settings.get('autoredare', False)))
        rl.addWidget(self.autoplay)
        self.info = QLabel('')
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info.setStyleSheet('background:#1c232c; border-radius:6px; padding:8px;')
        self.info.setAlignment(Qt.AlignmentFlag.AlignTop)
        rl.addWidget(self.info, 1)
        ext = QHBoxLayout()
        rl.addLayout(ext)
        self.btn(ext, ui('Deschide in IINA'), self.open_external).setToolTip('Enter sau dublu click')
        self.btn(ext, ui('Arata in Finder'), self.reveal).setToolTip('R')
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        state = self.settings.get('impartire')
        if state:
            split.restoreState(QByteArray.fromHex(state.encode()))
        else:
            split.setSizes([260, 900, 380])

        for keys, fn in (('Ctrl+Z', self.undo), ('Ctrl+O', self.choose_source), ('Ctrl+N', lambda: self.add_category(True)),
                         ('Ctrl+F', self.search.setFocus), ('F1', self.show_help), ('Ctrl+=', lambda: self.bump_size(40)),
                         ('Ctrl+-', lambda: self.bump_size(-40)), ('Ctrl+G', self.select_group), ('Ctrl+Backspace', self.trash_selection)) + ((('Del', self.trash_selection),) if WIN else ()):
            QShortcut(QKeySequence(keys), self).activated.connect(fn)
        self.statusBar().showMessage('Gata')

    def btn(self, layout, text, fn):
        b = QPushButton(text)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # tastele raman la grila
        b.clicked.connect(lambda _=False: fn())
        layout.addWidget(b)
        return b

    # ---------- proiect si foldere

    def choose_source(self):
        start = self.source.parent if self.source else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, 'Folderul cu clipurile de sortat', str(start))
        if folder:
            self.open_source(folder)

    def open_source(self, folder):
        if not folder or not Path(folder).is_dir():
            return
        self.source = Path(folder)
        projects = self.settings['proiecte']
        project = projects.get(str(self.source))
        if not project:
            dest = self.source.parent
            existing = sorted(e.name for e in os.scandir(dest) if e.is_dir() and not e.name.startswith('.')
                              and Path(e.path) != self.source and count_videos(e.path))
            names = existing or self.settings['sabloane'].get(self.settings.get('sablon', DEFAULT_TEMPLATE), [])
            project = {'destinatie': str(dest), 'categorii': [{'nume': n, 'culoare': COLORS[i % len(COLORS)]} for i, n in enumerate(names)]}
            projects[str(self.source)] = project
        self.dest_root = Path(project['destinatie'])
        self.cats = project['categorii']
        recents = [str(self.source)] + [p for p in self.settings.get('recente', []) if p != str(self.source)]
        self.settings['recente'] = recents[:12]
        self.settings['ultima_sursa'] = str(self.source)
        self.recent.blockSignals(True)
        self.recent.clear()
        for path in self.settings['recente']:
            p = Path(path)
            self.recent.addItem(f'{p.parent.name} / {p.name}', path)
        self.recent.blockSignals(False)
        self.load_undo_stack()
        self.save_settings()
        self.show_folder(self.source)

    def project(self):
        return self.settings['proiecte'][str(self.source)]

    def choose_dest(self):
        if not self.source:
            return
        folder = QFileDialog.getExistingDirectory(self, 'Unde se creeaza folderele categoriilor', str(self.dest_root))
        if folder:
            self.dest_root = Path(folder)
            self.project()['destinatie'] = folder
            self.save_settings()
            self.rebuild_categories()

    def cat_dir(self, cat):
        return self.dest_root / cat['nume']

    def show_folder(self, folder):
        if not folder:
            return
        self.view_dir = Path(folder)
        clips = list_clips(self.view_dir)
        missing = [c for c in clips if c.key not in self.meta]
        if missing:
            dialog = QProgressDialog('Citesc durata si ora filmarii...', None, 0, len(missing), self)
            dialog.setWindowModality(Qt.WindowModality.WindowModal)
            dialog.setMinimumDuration(400)
            with ThreadPoolExecutor(6) as pool:
                futures = {pool.submit(probe, c.path): c for c in missing}
                for n, future in enumerate(as_completed(futures), 1):
                    self.meta[futures[future].key] = future.result()
                    dialog.setValue(n)
                    QApplication.processEvents()
            dialog.close()
            save_json(META_FILE, self.meta)
        for clip in clips:
            m = self.meta.get(clip.key, {})
            for field in ('duration', 'codec', 'width', 'height', 'fps', 'audio'):
                setattr(clip, field, m.get(field, getattr(clip, field)))
            clip.created = m.get('created') or clip.mtime
            self.frames.setdefault(clip.key, {i for i in range(FRAMES) if frame_file(clip.key, i).exists()})
        self.all_clips = clips
        assign_groups(self.all_clips, self.gap.value())
        in_source = self.view_dir == self.source
        self.view_label.setText(f'Nesortate: {self.source.name}' if in_source else f'Continut folder: {self.view_dir.name}')
        self.back_btn.setVisible(not in_source)
        self.apply_filter()
        self.queue_frames()
        self.rebuild_categories()
        if self.model.rowCount():
            self.grid.setCurrentIndex(self.model.index(0))
        self.grid.setFocus()

    def regroup(self):
        assign_groups(self.all_clips, self.gap.value())
        self.apply_filter()

    def apply_filter(self):
        text = self.search.text().strip().lower()
        clips = [c for c in self.all_clips if text in c.name.lower()]
        order = self.sort_box.currentIndex()
        keys = [lambda c: (c.created, c.name), lambda c: c.name.lower(), lambda c: -c.duration, lambda c: -c.size]
        clips.sort(key=keys[order])
        selected = {c.path for c in self.selected_clips()}
        self.model.set_clips(clips)
        self.restore_selection(selected)
        self.update_counts()

    def restore_selection(self, paths):
        sel = QItemSelection()
        first = None
        for row, clip in enumerate(self.model.clips):
            if clip.path in paths:
                idx = self.model.index(row)
                sel.select(idx, idx)
                first = first or idx
        if first:
            self.grid.selectionModel().setCurrentIndex(first, QItemSelectionModel.SelectionFlag.NoUpdate)
            self.grid.selectionModel().select(sel, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            self.grid.scrollTo(first)

    def update_counts(self):
        if not self.source:
            return
        left = len(list_clips(self.source)) if self.view_dir != self.source else len(self.all_clips)
        sorted_count = sum(count_videos(self.cat_dir(c)) for c in self.cats)
        self.progress.setMaximum(max(1, left + sorted_count))
        self.progress.setValue(sorted_count)
        try:
            usage = shutil.disk_usage(self.dest_root)
            self.free_label.setText(f'Destinatie: {self.dest_root}\nLiber pe disc: {human_size(usage.free)}')
        except OSError:
            self.free_label.setText(f'Destinatie indisponibila: {self.dest_root}')
        self.dest_btn.setText(f'Destinatie: {self.dest_root.name}')

    # ---------- categorii

    def rebuild_categories(self):
        while self.cat_layout.count():
            item = self.cat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, cat in enumerate(self.cats):
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(3)
            b = FolderButton(self.grid)
            key = str((i + 1) % 10) if i < 10 else ' '
            n = count_videos(self.cat_dir(cat))
            exists = self.cat_dir(cat).is_dir()
            b.setText(f'{key}   {cat["nume"]}' + (f'   ({n})' if n else '' if exists else '   (nou)'))
            color = QColor(cat.get('culoare', COLORS[0]))
            current = self.view_dir == self.cat_dir(cat)
            b.setStyleSheet(f'QPushButton {{text-align:left; padding:10px 12px; font-size:14px; font-weight:bold;'
                            f' background:{color.darker(190).name()}; border-left:6px solid {color.name()};'
                            f' {"border:2px solid #74e1ff;" if current else ""}}}'
                            f' QPushButton:hover, QPushButton:pressed {{background:{color.darker(120).name()};}}')
            b.setToolTip(f'Muta selectia in {self.cat_dir(cat)}\nClick dreapta: redenumire, culoare, ordine, vezi continutul')
            b.clicked.connect(lambda _=False, c=i: self.move_selection(c))
            b.dropped.connect(lambda c=i: self.move_selection(c))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _p, c=i, w=b: self.category_menu(c, w))
            hl.addWidget(b, 1)
            eye = QToolButton()
            eye.setText('Vezi')
            eye.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            eye.setToolTip('Arata clipurile deja mutate aici (le poti muta mai departe)')
            eye.setEnabled(exists)
            eye.clicked.connect(lambda _=False, c=cat: self.show_folder(self.cat_dir(c)))
            eye.setMinimumHeight(42)
            hl.addWidget(eye)
            self.cat_layout.addWidget(row)
        self.cat_layout.addStretch()
        self.update_counts()

    def add_category(self, create_now, move_after=False):
        if not self.source:
            return QMessageBox.information(self, 'Separare Clipuri', 'Deschide intai folderul cu clipuri.')
        title = 'Folder nou' if create_now else 'Eticheta noua'
        name, ok = QInputDialog.getText(self, title, f'Numele folderului (se creeaza in {self.dest_root}):')
        name = clean_name(name or '')
        if not ok or not name:
            return
        if any(c['nume'].lower() == name.lower() for c in self.cats):
            index = next(i for i, c in enumerate(self.cats) if c['nume'].lower() == name.lower())
        else:
            used = {c.get('culoare') for c in self.cats}
            color = next((c for c in COLORS if c not in used), COLORS[len(self.cats) % len(COLORS)])
            self.cats.append({'nume': name, 'culoare': color})
            index = len(self.cats) - 1
        if create_now:
            try:
                self.cat_dir(self.cats[index]).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                QMessageBox.warning(self, title, f'Nu pot crea folderul:\n{exc}')
        self.save_settings()
        self.rebuild_categories()
        if move_after:
            self.move_selection(index)

    def category_menu(self, index, widget):
        cat = self.cats[index]
        menu = QMenu(self)
        menu.addAction('Vezi continutul', lambda: self.show_folder(self.cat_dir(cat))).setEnabled(self.cat_dir(cat).is_dir())
        menu.addAction(ui('Deschide in Finder'), lambda: self.open_in_finder(self.cat_dir(cat)))
        menu.addSeparator()
        menu.addAction('Redenumeste...', lambda: self.rename_category(index))
        menu.addAction('Schimba culoarea...', lambda: self.recolor_category(index))
        menu.addAction('Muta mai sus', lambda: self.shift_category(index, -1)).setEnabled(index > 0)
        menu.addAction('Muta mai jos', lambda: self.shift_category(index, 1)).setEnabled(index < len(self.cats) - 1)
        menu.addSeparator()
        menu.addAction('Scoate din lista (folderul ramane)', lambda: self.remove_category(index))
        menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))

    def rename_category(self, index):
        cat = self.cats[index]
        name, ok = QInputDialog.getText(self, 'Redenumeste', 'Nume nou:', text=cat['nume'])
        name = clean_name(name or '')
        if not ok or not name or name == cat['nume']:
            return
        old, new = self.cat_dir(cat), self.dest_root / name
        if old.is_dir():
            if self.moving:
                return QMessageBox.information(self, 'Redenumeste', 'Asteapta sa se termine mutarile in curs.')
            if new.exists():
                return QMessageBox.warning(self, 'Redenumeste', f'Exista deja folderul {new}.')
            os.rename(old, new)
        cat['nume'] = name
        self.save_settings()
        if self.view_dir == old:
            self.show_folder(new)
        else:
            self.rebuild_categories()

    def recolor_category(self, index):
        color = QColorDialog.getColor(QColor(self.cats[index]['culoare']), self, 'Culoarea etichetei')
        if color.isValid():
            self.cats[index]['culoare'] = color.name()
            self.save_settings()
            self.rebuild_categories()

    def shift_category(self, index, step):
        j = index + step
        self.cats[index], self.cats[j] = self.cats[j], self.cats[index]
        self.save_settings()
        self.rebuild_categories()

    def remove_category(self, index):
        del self.cats[index]
        self.save_settings()
        self.rebuild_categories()

    def template_menu(self):
        if not self.source:
            return
        menu = QMenu(self)
        for name, folders in self.settings['sabloane'].items():
            menu.addAction(f'Adauga din sablonul: {name}  ({len(folders)})', lambda n=name: self.apply_template(n))
        menu.addSeparator()
        menu.addAction('Salveaza lista curenta ca sablon...', self.save_template)
        menu.addAction('Adauga folderele existente din destinatie', self.import_existing)
        menu.addAction('Creeaza acum toate folderele pe disc', self.create_all)
        menu.exec(self.template_btn.mapToGlobal(self.template_btn.rect().bottomLeft()))

    def apply_template(self, name):
        known = {c['nume'].lower() for c in self.cats}
        for folder in self.settings['sabloane'][name]:
            if folder.lower() not in known:
                self.cats.append({'nume': folder, 'culoare': COLORS[len(self.cats) % len(COLORS)]})
        self.settings['sablon'] = name
        self.save_settings()
        self.rebuild_categories()

    def save_template(self):
        name, ok = QInputDialog.getText(self, 'Sablon', 'Numele sablonului (ex: Nunta mare, Botez):')
        if ok and clean_name(name):
            self.settings['sabloane'][clean_name(name)] = [c['nume'] for c in self.cats]
            self.settings['sablon'] = clean_name(name)
            self.save_settings()

    def import_existing(self):
        known = {c['nume'].lower() for c in self.cats}
        for entry in sorted(os.scandir(self.dest_root), key=lambda e: e.name.lower()):
            if entry.is_dir() and not entry.name.startswith('.') and Path(entry.path) != self.source and entry.name.lower() not in known:
                self.cats.append({'nume': entry.name, 'culoare': COLORS[len(self.cats) % len(COLORS)]})
        self.save_settings()
        self.rebuild_categories()

    def create_all(self):
        for cat in self.cats:
            self.cat_dir(cat).mkdir(parents=True, exist_ok=True)
        self.rebuild_categories()

    # ---------- mutare si anulare

    def selected_clips(self):
        rows = sorted(i.row() for i in self.grid.selectionModel().selectedIndexes()) if self.grid.selectionModel() else []
        return [self.model.clips[r] for r in rows if r < len(self.model.clips)]

    def move_selection(self, index):
        if index >= len(self.cats):
            return
        clips = self.selected_clips()
        if not clips:
            self.statusBar().showMessage(ui('Selecteaza intai clipurile (click, Cmd+click, Shift+click sau trage un dreptunghi)'), 5000)
            return
        cat = self.cats[index]
        dest = self.cat_dir(cat)
        if self.view_dir == dest:
            return
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return QMessageBox.warning(self, 'Mutare', f'Nu pot crea {dest}:\n{exc}')
        self.release_preview({c.path for c in clips})
        reserved = set()
        pairs = []
        for clip in clips:
            for f in [clip.path] + sidecars(clip.path):
                target = dest / f.name
                n = 2
                while target.exists() or str(target) in reserved:
                    target = dest / f'{f.stem} ({n}){f.suffix}'
                    n += 1
                reserved.add(str(target))
                pairs.append((str(f), str(target)))
        self.drop_from_grid(clips)
        size = sum(c.size for c in clips)
        cross = os.stat(clips[0].path).st_dev != os.stat(dest).st_dev
        batch = {'id': self.next_batch, 'ora': time.strftime('%Y-%m-%d %H:%M:%S'), 'folder': cat['nume'],
                 'sursa': str(self.source), 'perechi': pairs, 'clipuri': len(clips), 'octeti': size}
        self.run_batch(batch, f'{len(clips)} clipuri > {cat["nume"]}')
        self.undo_stack.append(batch)
        self.journal(batch, 'mutare')
        self.undo_btn.setEnabled(True)
        self.statusBar().showMessage(f'{len(clips)} clipuri ({human_size(size)}) > {cat["nume"]}'
                                     + ('  ·  copiere pe alt disc, poate dura' if cross else ''), 6000)
        self.grid.setFocus()

    def release_preview(self, paths):
        if self.loaded_preview in paths:
            self.player.stop()
            self.player.setSource(QUrl())
            self.loaded_preview = None
            QApplication.processEvents()

    def drop_from_grid(self, clips):
        # scoate clipurile din grila si selecteaza clipul urmator
        first_row = min(self.model.clips.index(c) for c in clips)
        paths = {c.path for c in clips}
        self.all_clips = [c for c in self.all_clips if c.path not in paths]
        self.model.remove_paths(paths)
        if self.model.rowCount():
            idx = self.model.index(min(first_row, self.model.rowCount() - 1))
            self.grid.selectionModel().setCurrentIndex(idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            self.grid.scrollTo(idx)
        else:
            self.player.stop()
            self.player.setSource(QUrl())
            self.loaded_preview = None

    def trash_selection(self):
        """Muta selectia in Cosul macOS; se poate anula cu Cmd+Z cat timp Cosul nu e golit."""
        clips = self.selected_clips()
        if not clips:
            return self.statusBar().showMessage('Selecteaza intai clipurile de sters', 4000)
        self.release_preview({c.path for c in clips})
        pairs, errors, trashed = [], [], []
        for clip in clips:
            ok = True
            for f in [clip.path] + sidecars(clip.path):
                q = QFile(str(f))
                if q.moveToTrash():
                    # fara cale in Cos (ex: Cos dezactivat) stergerea nu mai poate fi anulata
                    if q.fileName() != str(f) and os.path.exists(q.fileName()):
                        pairs.append((str(f), q.fileName()))
                else:
                    ok = False
                    errors.append(f.name)
            if ok:
                trashed.append(clip)
        if trashed:
            self.drop_from_grid(trashed)
            size = sum(c.size for c in trashed)
            batch = {'id': self.next_batch, 'ora': time.strftime('%Y-%m-%d %H:%M:%S'), 'folder': 'Cos',
                     'sursa': str(self.source), 'perechi': pairs, 'clipuri': len(trashed), 'octeti': size}
            self.undo_stack.append(batch)
            self.journal(batch, 'mutare')
            self.undo_btn.setEnabled(True)
            self.update_counts()
            self.statusBar().showMessage(ui(f'{len(trashed)} clipuri ({human_size(size)}) in Cos  ·  Cmd+Z le readuce'), 6000)
        if errors:
            QMessageBox.warning(self, 'Cos', 'Nu am putut muta in Cos:\n' + '\n'.join(errors[:20]))
        self.grid.setFocus()

    def select_short(self):
        limit = self.short_limit.value()
        sel = QItemSelection()
        for row, clip in enumerate(self.model.clips):
            if clip.duration < limit:
                sel.select(self.model.index(row), self.model.index(row))
        self.grid.selectionModel().select(sel, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        if not sel.isEmpty():
            first = sel.indexes()[0]
            self.grid.selectionModel().setCurrentIndex(first, QItemSelectionModel.SelectionFlag.NoUpdate)
            self.grid.scrollTo(first)
        self.statusBar().showMessage(ui(f'{len(sel.indexes())} clipuri sub {limit} s (teste, expunere). Verifica-le, apoi Cmd+Backspace = Cos'), 6000)
        self.grid.setFocus()

    def run_batch(self, batch, label):
        bid = self.next_batch
        self.next_batch += 1
        self.batches[bid] = batch
        self.moving += 1
        self.move_pool.start(MoveJob(bid, batch['perechi'], label, self.signals))

    def move_progress(self, bid, done, total, label):
        self.statusBar().showMessage(f'Mut: {label}  {done}/{total}')

    def move_done(self, bid, errors):
        self.moving -= 1
        batch = self.batches.pop(bid, {})
        if errors:
            QMessageBox.warning(self, 'Unele fisiere nu s-au mutat', '\n'.join(errors[:20]))
            self.journal({'erori': errors, 'folder': batch.get('folder')}, 'erori')
            self.show_folder(self.view_dir)
        elif batch.get('reselect'):
            self.show_folder(self.view_dir)
            self.restore_selection({Path(p) for p in batch['reselect']})
        else:
            self.rebuild_categories()
        if not self.moving:
            self.statusBar().showMessage(f'Mutare terminata: {batch.get("folder", "")}', 4000)
            if self.view_dir == self.source and not self.all_clips and not self.search.text():
                self.finished_report()

    def undo(self):
        if not self.undo_stack:
            return self.statusBar().showMessage('Nimic de anulat', 3000)
        batch = self.undo_stack.pop()
        back = [(dst, src) for src, dst in reversed(batch['perechi'])]
        self.journal(batch, 'anulare')
        self.undo_btn.setEnabled(bool(self.undo_stack))
        self.run_batch({'perechi': back, 'folder': f'anulare {batch["folder"]}', 'reselect': [src for _, src in back]},
                       f'inapoi din {batch["folder"]}')
        self.statusBar().showMessage(f'Anulat: {batch["clipuri"]} clipuri inapoi din {batch["folder"]}', 5000)

    def journal(self, batch, kind):
        with JOURNAL_FILE.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'tip': kind, 'ora': time.strftime('%Y-%m-%d %H:%M:%S'), **batch}, ensure_ascii=False) + '\n')

    def load_undo_stack(self):
        # reconstruieste anularile din jurnal, pentru sursa curenta
        stack = []
        try:
            lines = JOURNAL_FILE.read_text(encoding='utf-8').splitlines()
        except OSError:
            lines = []
        for line in lines:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get('sursa') != str(self.source):
                continue
            if entry.get('tip') == 'mutare':
                stack.append(entry)
            elif entry.get('tip') == 'anulare' and stack:
                stack.pop()
        self.undo_stack = [b for b in stack if all(os.path.exists(d) for _, d in b['perechi'])][-50:]
        self.undo_btn.setEnabled(bool(self.undo_stack))

    def finished_report(self):
        lines = [f'{c["nume"]}: {count_videos(self.cat_dir(c))} clipuri' for c in self.cats if count_videos(self.cat_dir(c))]
        box = QMessageBox(self)
        box.setWindowTitle('Gata')
        box.setText(f'Toate clipurile din {self.source.name} sunt sortate.\n\n' + '\n'.join(lines))
        box.addButton(ui('Deschide destinatia in Finder'), QMessageBox.ButtonRole.AcceptRole)
        box.addButton('Inchide', QMessageBox.ButtonRole.RejectRole)
        if box.exec() == 0:
            self.open_in_finder(self.dest_root)

    # ---------- miniaturi

    def queue_frames(self):
        if not FFMPEG:
            self.statusBar().showMessage('ffmpeg nu este instalat: fara miniaturi', 8000)
            return
        # intai cadrul principal pentru toate clipurile, apoi cadrele pentru derulare
        for priority, indexes in ((10, [POSTER]), (0, [i for i in range(FRAMES) if i != POSTER])):
            for clip in self.model.clips:
                for i in indexes:
                    if i in self.frames.get(clip.key, set()) or (clip.key, i) in self.pending or not clip.duration:
                        continue
                    self.pending.add((clip.key, i))
                    seconds = clip.duration * (i + 0.5) / FRAMES
                    self.thumb_pool.start(FrameJob(clip.key, i, clip.path, seconds, self.signals), priority)

    def frame_ready(self, key, index):
        self.pending.discard((key, index))
        self.frames.setdefault(key, set()).add(index)
        self.model.refresh_key(key)

    def frame_pixmap(self, clip, index):
        ready = self.frames.get(clip.key, set())
        if index not in ready:
            if POSTER in ready:
                index = POSTER
            elif ready:
                index = min(ready)
            else:
                return None
        cache_key = f'{clip.key}_{index}'
        pix = QPixmapCache.find(cache_key)
        if pix is None or pix.isNull():
            pix = QPixmap(str(frame_file(clip.key, index)))
            if pix.isNull():
                return None
            QPixmapCache.insert(cache_key, pix)
        return pix

    def set_thumb_size(self, value):
        self.thumb_w = value
        self.grid.doItemsLayout()
        self.grid.viewport().update()

    def bump_size(self, step):
        self.size_slider.setValue(self.size_slider.value() + step)

    # ---------- selectie si previzualizare

    def selection_changed(self, *_):
        clips = self.selected_clips()
        if len(clips) > 1:
            groups = sorted({c.group for c in clips})
            self.statusBar().showMessage(f'Selectate {len(clips)} clipuri · {human_size(sum(c.size for c in clips))} · '
                                         f'{human_dur(sum(c.duration for c in clips))} · grup {", ".join(map(str, groups))}')

    def current_changed(self, current, _previous):
        if not current.isValid():
            return
        clip = self.model.clips[current.row()]
        when = datetime.fromtimestamp(clip.created).strftime('%d.%m.%Y  %H:%M:%S') if clip.created else '?'
        same_group = sum(1 for c in self.all_clips if c.group == clip.group)
        self.info.setText(f'<b style="font-size:15px">{clip.name}</b><br>'
                          f'Durata {human_dur(clip.duration)} · {human_size(clip.size)}<br>'
                          f'{clip.codec} {clip.width}x{clip.height} · {clip.fps:g} fps · audio {clip.audio or "-"}<br>'
                          f'Filmat: {when}<br>'
                          f'<span style="color:{group_color(clip.group).name()}">Grup {clip.group}: {same_group} clipuri</span> (G = selecteaza tot grupul)<br>'
                          f'<span style="color:#7d8a98">{clip.path.parent}</span>')
        if self.loaded_preview != clip.path:
            self.loaded_preview = clip.path
            self.player.setSource(QUrl.fromLocalFile(str(clip.path)))
            if self.autoplay.isChecked():
                self.player.play()

    def media_status(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia and not self.autoplay.isChecked():
            # arata un cadru din clip fara sa porneasca redarea
            self.player.setPosition(int(self.player.duration() * (POSTER + 0.5) / FRAMES))
            self.player.pause()

    def position_changed(self, ms):
        if not self.slider.isSliderDown():
            self.slider.setValue(ms)
        self.time_label.setText(f'{human_dur(ms / 1000)} / {human_dur(self.player.duration() / 1000)}')

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def set_rate(self, rate):
        self.player.setPlaybackRate(rate)
        for r, b in self.speed_btns.items():
            b.setChecked(r == rate)
        self.settings['viteza'] = rate

    def current_clip(self):
        idx = self.grid.currentIndex()
        return self.model.clips[idx.row()] if idx.isValid() and idx.row() < len(self.model.clips) else None

    def open_external(self):
        clip = self.current_clip()
        if not clip:
            return
        self.player.pause()
        if MAC and Path('/Applications/IINA.app').exists():
            subprocess.Popen(['open', '-a', 'IINA', str(clip.path)])
        else:
            open_path(clip.path)

    def reveal(self):
        clip = self.current_clip()
        if clip:
            open_path(clip.path, reveal=True)

    def open_in_finder(self, folder):
        Path(folder).mkdir(parents=True, exist_ok=True)
        open_path(folder)

    def select_group(self):
        groups = {c.group for c in self.selected_clips()} or ({self.current_clip().group} if self.current_clip() else set())
        sel = QItemSelection()
        for row, clip in enumerate(self.model.clips):
            if clip.group in groups:
                sel.select(self.model.index(row), self.model.index(row))
        self.grid.selectionModel().select(sel, QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def grid_menu(self, pos):
        if not self.selected_clips():
            return
        menu = QMenu(self)
        target = menu.addMenu('Muta in')
        for i, cat in enumerate(self.cats):
            target.addAction(cat['nume'], lambda c=i: self.move_selection(c))
        menu.addAction('Folder nou si muta aici...', lambda: self.add_category(True, move_after=True))
        menu.addAction(ui('Sterge in Cos (Cmd+Backspace)'), self.trash_selection)
        if self.view_dir != self.source:
            menu.addAction('Inapoi in nesortate', self.move_back_to_source)
        menu.addSeparator()
        menu.addAction('Selecteaza tot grupul (G)', self.select_group)
        menu.addAction(ui('Deschide in IINA (Enter)'), self.open_external)
        menu.addAction(ui('Arata in Finder (R)'), self.reveal)
        menu.addAction('Copiaza caile', lambda: QApplication.clipboard().setText('\n'.join(str(c.path) for c in self.selected_clips())))
        menu.exec(self.grid.viewport().mapToGlobal(pos))

    def move_back_to_source(self):
        self.cats.append({'nume': '__sursa__', 'culoare': '#000000'})
        saved_root, self.dest_root = self.dest_root, self.source.parent
        self.cats[-1]['nume'] = self.source.name
        try:
            self.move_selection(len(self.cats) - 1)
        finally:
            self.cats.pop()
            self.dest_root = saved_root
            self.rebuild_categories()

    # ---------- taste

    def eventFilter(self, obj, event):
        if obj is self.grid and event.type() == QEvent.Type.KeyPress:
            key, mods = event.key(), event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
            if mods == Qt.KeyboardModifier.NoModifier:
                if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
                    if not event.isAutoRepeat():
                        n = key - Qt.Key.Key_0
                        self.move_selection(9 if n == 0 else n - 1)
                    return True
                if key == Qt.Key.Key_Space:
                    self.toggle_play()
                    return True
                if key == Qt.Key.Key_G:
                    self.select_group()
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.open_external()
                    return True
                if key == Qt.Key.Key_R:
                    self.reveal()
                    return True
                if key == Qt.Key.Key_M:
                    self.mute.toggle()
                    return True
                if key in (Qt.Key.Key_J, Qt.Key.Key_L):
                    self.player.setPosition(max(0, self.player.position() + (5000 if key == Qt.Key.Key_L else -5000)))
                    return True
                if key == Qt.Key.Key_Escape:
                    self.grid.clearSelection()
                    return True
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls() if event.source() is None else []
        if urls and Path(urls[0].toLocalFile()).is_dir():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.open_source(event.mimeData().urls()[0].toLocalFile())

    # ---------- ajutor si salvare

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Ajutor Separare Clipuri')
        dialog.resize(720, 760)
        layout = QVBoxLayout(dialog)
        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        view.setMarkdown(ui((APP_DIR / 'AJUTOR.md').read_text(encoding='utf-8')) if (APP_DIR / 'AJUTOR.md').exists() else '')
        layout.addWidget(view)
        dialog.exec()

    def save_settings(self):
        self.settings.update({'marime': self.thumb_w, 'sortare': self.sort_box.currentIndex(), 'pauza_grup': self.gap.value(),
                              'fara_sunet': self.mute.isChecked(), 'limita_scurte': self.short_limit.value(), 'autoredare': self.autoplay.isChecked()})
        save_json(SETTINGS_FILE, self.settings)

    def closeEvent(self, event):
        if self.moving:
            QMessageBox.information(self, 'Mutare in curs', 'Asteapta sa se termine mutarea fisierelor.')
            event.ignore()
            return
        self.settings['geometrie'] = bytes(self.saveGeometry().toHex()).decode()
        self.settings['impartire'] = bytes(self.split.saveState().toHex()).decode()
        self.save_settings()
        self.player.stop()
        self.thumb_pool.clear()
        self.thumb_pool.waitForDone(5000)
        event.accept()


def app_icon():
    pix = QPixmap(512, 512)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor('#15191f'))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(24, 24, 464, 464, 100, 100)
    for i, color in enumerate(('#3b82c4', '#2f9e74', '#c9822b')):
        p.setBrush(QColor(color))
        p.drawRoundedRect(70 + i * 130, 90, 110, 70, 12, 12)
    path = QPainterPath()
    path.moveTo(130, 230)
    path.lineTo(250, 230)
    path.lineTo(280, 265)
    path.lineTo(400, 265)
    path.lineTo(400, 420)
    path.lineTo(110, 420)
    path.lineTo(110, 250)
    path.closeSubpath()
    p.setBrush(QColor('#ffd166'))
    p.drawPath(path)
    p.setPen(QPen(QColor('#15191f'), 22, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawLine(256, 175, 256, 330)
    p.drawLine(205, 285, 256, 335)
    p.drawLine(307, 285, 256, 335)
    p.end()
    return pix


STYLE = """
QWidget { background:#15191f; color:#e9edf2; font-size:13px; }
QPushButton, QComboBox, QSpinBox, QToolButton { background:#293442; padding:7px 10px; border-radius:6px; border:none; }
QPushButton:hover, QToolButton:hover { background:#3a526a; }
QPushButton:checked { background:#287d76; }
QPushButton:disabled, QToolButton:disabled { color:#5d6b7a; }
QListView { background:#11151a; border:1px solid #2a3440; border-radius:6px; }
QLineEdit { background:#1c232c; border:1px solid #34404e; padding:6px; border-radius:6px; }
QProgressBar { background:#1c232c; border:1px solid #34404e; border-radius:6px; text-align:center; height:20px; }
QProgressBar::chunk { background:#287d76; border-radius:5px; }
QSplitter::handle { background:#15191f; width:6px; }
QMenu { background:#1c232c; border:1px solid #34404e; }
QMenu::item:selected { background:#365e73; }
QStatusBar { color:#9aa8b6; }
QScrollBar:vertical { background:#11151a; width:12px; }
QScrollBar::handle:vertical { background:#34404e; border-radius:5px; min-height:40px; }
QToolTip { background:#1c232c; color:#e9edf2; border:1px solid #34404e; }
"""


def main():
    if '--icon' in sys.argv:
        app = QApplication(sys.argv)
        app_icon().save(sys.argv[sys.argv.index('--icon') + 1])
        return
    app = QApplication(sys.argv)
    app.setApplicationName('Separare Clipuri')
    app.setOrganizationName('Urdea')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(app_icon()))
    window = Separator()
    window.show()
    if '--verificare' in sys.argv:
        # folosit la build: pachetul porneste, gaseste ffmpeg si ghidul, apoi se inchide
        ok = bool(FFMPEG and FFPROBE) and (APP_DIR / 'AJUTOR.md').exists()
        print('verificare', 'ok' if ok else 'esec', FFMPEG, FFPROBE, APP_DIR, DATA, flush=True)
        QTimer.singleShot(1500, lambda: app.exit(0 if ok else 3))
        sys.exit(app.exec())
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args and Path(args[0]).is_dir():
        QTimer.singleShot(0, lambda: window.open_source(args[0]))
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
