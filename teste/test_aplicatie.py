"""Test automat pe clipuri generate cu ffmpeg, intr-un folder temporar (Mac si Windows).
Folosire: python teste/test_aplicatie.py"""
import os, sys, time, tempfile, subprocess
from pathlib import Path
TMP = Path(tempfile.mkdtemp(prefix='separare_test_'))
os.environ['SEPARARE_DATA'] = str(TMP / 'data')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main
from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

assert main.FFMPEG and main.FFPROBE, 'ffmpeg si ffprobe sunt necesare pentru test'
root = TMP / 'proiect'; src = root / 'Prores'; src.mkdir(parents=True)
for i, t in enumerate(['10:00:00', '10:01:10', '10:02:30', '11:30:00', '11:31:00', '13:00:00'], 1):
    subprocess.run([main.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=640x360:rate=25:duration=4',
                    '-f', 'lavfi', '-i', 'sine=d=4', '-c:v', 'prores_ks', '-profile:v', '0', '-c:a', 'pcm_s16le',
                    '-metadata', f'creation_time=2026-04-26T{t}Z', '-f', 'mov', '-y', str(src / f'DAN000{i}.MP4')], check=True)
(src / 'DAN0001.XML').write_text('x')
app = QApplication([]); app.setStyleSheet(main.STYLE)
w = main.Separator(); w.resize(1500, 900); w.show()
w.open_source(str(src))

def wait(cond, sec=60):
    end = time.time() + sec
    while time.time() < end and not cond():
        app.processEvents(); time.sleep(0.02)
    app.processEvents()
    return cond()

def key(k):
    app.sendEvent(w.grid, QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier))

def check(ok, msg):
    print(('OK   ' if ok else 'FAIL ') + msg)
    if not ok: check.failed = True
check.failed = False

check(w.model.rowCount() == 6, f'6 clipuri incarcate ({w.model.rowCount()})')
check([c.group for c in w.model.clips] == [1, 1, 1, 2, 2, 3], f'grupuri {[c.group for c in w.model.clips]}')
check([c['nume'] for c in w.cats][:2] == ['Acasa', 'Biserica'], 'sablon arhiva aplicat')
check(wait(lambda: not w.pending, 120), 'miniaturi generate')
check(all(len(w.frames[c.key]) == main.FRAMES for c in w.model.clips), 'cate 8 cadre pe clip')

# grupul 1 (3 clipuri) cu G, apoi tasta 1 -> Acasa
w.grid.setCurrentIndex(w.model.index(0)); key(Qt.Key.Key_G)
check(len(w.selected_clips()) == 3, 'G selecteaza grupul')
key(Qt.Key.Key_1); wait(lambda: not w.moving)
acasa = root / 'Acasa'
check(sorted(p.name for p in acasa.iterdir()) == ['DAN0001.MP4', 'DAN0001.XML', 'DAN0002.MP4', 'DAN0003.MP4'], 'mutate in Acasa cu .XML')
check(w.model.rowCount() == 3 and w.selected_clips()[0].name == 'DAN0004.MP4', 'selectia trece la urmatorul clip')

# folder nou din cod, tasta 0 nu exista -> nimic; mutare prin click pe buton
w.cats.append({'nume': 'Petrecere', 'culoare': '#c94f4f'}); w.rebuild_categories()
w.grid.setCurrentIndex(w.model.index(2)); w.move_selection(len(w.cats) - 1); wait(lambda: not w.moving)
check((root / 'Petrecere' / 'DAN0006.MP4').exists(), 'mutare intr-o eticheta noua creeaza folderul')

# coliziune de nume
(root / 'Biserica').mkdir(exist_ok=True); (root / 'Biserica' / 'DAN0004.MP4').write_bytes(b'x')
w.grid.setCurrentIndex(w.model.index(0)); key(Qt.Key.Key_2); wait(lambda: not w.moving)
check((root / 'Biserica' / 'DAN0004 (2).MP4').exists() and (root / 'Biserica' / 'DAN0004.MP4').stat().st_size == 1, 'fara suprascriere, nume (2)')

# undo de doua ori
w.undo(); wait(lambda: not w.moving)
check((src / 'DAN0004.MP4').exists() and w.model.rowCount() == 2, 'undo 1 readuce clipul')
check(any(c.name == 'DAN0004.MP4' for c in w.selected_clips()), 'clipul readus e selectat')
w.undo(); wait(lambda: not w.moving)
check((src / 'DAN0006.MP4').exists(), 'undo 2')

# undo dupa repornire (din jurnal)
w.close(); w2 = main.Separator(); w2.open_source(str(src)); w = w2
check(len(w.undo_stack) == 1, f'jurnal: 1 anulare ramasa ({len(w.undo_stack)})')
w.undo(); wait(lambda: not w.moving)
check((src / 'DAN0001.XML').exists() and (src / 'DAN0001.MP4').exists() and w.model.rowCount() == 6, 'undo dupa repornire, cu .XML')

# vizualizare folder categorie si mutare inapoi
w.grid.setCurrentIndex(w.model.index(0)); key(Qt.Key.Key_3); wait(lambda: not w.moving)
w.show_folder(root / 'Restaurant')
check(w.model.rowCount() == 1, 'vezi continutul folderului')
w.grid.setCurrentIndex(w.model.index(0)); w.move_back_to_source(); wait(lambda: not w.moving)
check((src / 'DAN0001.MP4').exists() and (src / 'DAN0001.XML').exists(), 'inapoi in nesortate')
check([c['nume'] for c in w.cats].count(src.name) == 0, 'sursa nu ramane in lista de foldere')
w.show_folder(src)

# clipuri scurte si Cos, cu anulare
short = src / 'DAN0009.MP4'
subprocess.run([main.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=0.5',
                '-c:v', 'prores_ks', '-f', 'mov', '-y', str(short)], check=True)
(src / 'DAN0009.XML').write_text('x')
w.show_folder(src); w.short_limit.setValue(2); w.select_short()
check([c.name for c in w.selected_clips()] == ['DAN0009.MP4'], 'selecteaza doar clipul scurt')
w.trash_selection()
check(not short.exists() and not (src / 'DAN0009.XML').exists() and w.model.rowCount() == 6, 'clipul scurt si .XML in Cos')
check(all(Path(d).exists() and Path(d).parent != src for _, d in w.undo_stack[-1]['perechi']), 'fisierele sunt in Cos')
w.undo(); wait(lambda: not w.moving)
check(short.exists() and (src / 'DAN0009.XML').exists() and w.model.rowCount() == 7, 'Cmd+Z readuce din Cos')
w.select_short(); w.trash_selection()
for _, d in w.undo_stack[-1]['perechi']:
    os.remove(d)  # curatenie: nu lasam fisiere de test in Cos
w.grab().save(str(TMP / 'captura.png'))
w.close()
print('REZULTAT:', 'ESEC' if check.failed else 'TOATE TESTELE AU TRECUT', '·', TMP)
sys.exit(1 if check.failed else 0)
