"""Test automat pe clipuri generate cu ffmpeg, intr-un folder temporar (Mac si Windows).
Folosire: python teste/test_aplicatie.py"""
import os, sys, time, tempfile, subprocess, traceback, faulthandler
from pathlib import Path
faulthandler.enable()  # la un crash nativ ramane macar stiva in log
CI = bool(os.environ.get('GITHUB_ACTIONS'))
TMP = Path(tempfile.mkdtemp(prefix='separare_test_'))
os.environ['SEPARARE_DATA'] = str(TMP / 'data')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def report(msg, level='error'):
    # pe GitHub, erorile devin adnotari vizibile in pagina build-ului
    if CI:
        print(f'::{level}::' + msg.replace('%', '%25').replace('\r', '').replace('\n', '%0A'), flush=True)

def check(ok, msg):
    print(('OK   ' if ok else 'FAIL ') + msg, flush=True)
    if not ok:
        check.failed = True
        report(f'{sys.platform}: FAIL {msg}')
check.failed = False

def excepthook(kind, value, tb):
    # orice exceptie neprinsa (import, pornire) ajunge si ea in adnotari
    report(f'{sys.platform}: exceptie\n' + ''.join(traceback.format_exception(kind, value, tb)))
    sys.__excepthook__(kind, value, tb)
sys.excepthook = excepthook

import main
if main.MEDIA_ERROR:
    print('Fara QtMultimedia (previzualizare dezactivata):', main.MEDIA_ERROR, flush=True)
    report(f'{sys.platform}: QtMultimedia indisponibil, previzualizare dezactivata: {main.MEDIA_ERROR}', 'warning')
from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

# textele pentru Windows, verificate pe orice platforma
mac = main.MAC; main.MAC = False
check(main.ui('Cmd+Z in Finder, Deschide in IINA') == 'Ctrl+Z in Explorer, Deschide in player', 'texte Windows')
main.MAC = mac

assert main.FFMPEG and main.FFPROBE, 'ffmpeg si ffprobe sunt necesare pentru test'
root = TMP / 'proiect'; src = root / 'Prores'; src.mkdir(parents=True)
for i, t in enumerate(['10:00:00', '10:01:10', '10:02:30', '11:30:00', '11:31:00', '13:00:00'], 1):
    made = subprocess.run([main.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=640x360:rate=25:duration=4',
                           '-f', 'lavfi', '-i', 'sine=d=4', '-c:v', 'prores_ks', '-profile:v', '0', '-c:a', 'pcm_s16le',
                           '-metadata', f'creation_time=2026-04-26T{t}Z', '-f', 'mov', '-y', str(src / f'DAN000{i}.MP4')],
                          capture_output=True, text=True)
    if made.returncode:
        raise RuntimeError('ffmpeg nu a creat clipurile de test: ' + made.stderr)
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


# dialogurile modale ar bloca testul: le inregistram ca erori
from PySide6.QtWidgets import QMessageBox
def no_dialog(*args, **kwargs):
    check(False, 'dialog: ' + ' | '.join(str(a) for a in args[1:3]))
    return QMessageBox.StandardButton.Ok
QMessageBox.warning = QMessageBox.information = no_dialog

try:
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

    # ---------- audio: WAV de la recorder (BWF), sincron cu clipurile dupa ora
    from datetime import datetime
    src2 = TMP / 'proiect2' / 'Clipuri'; src2.mkdir(parents=True)
    epoch = lambda hms: datetime.fromisoformat(f'2026-04-26T{hms}+00:00').timestamp()
    def video(name, hms, sound=True):
        args = [main.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=4']
        args += ['-f', 'lavfi', '-i', 'sine=d=4', '-c:a', 'pcm_s16le'] if sound else []
        subprocess.run(args + ['-c:v', 'prores_ks', '-metadata', f'creation_time=2026-04-26T{hms}Z', '-f', 'mov', '-y',
                               str(src2 / name)], check=True, capture_output=True)
    def bwf(name, start, seconds):
        local = datetime.fromtimestamp(start)  # recorderul scrie ora locala
        subprocess.run([main.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', f'sine=f=100:sample_rate=1000:d={seconds}',
                        '-c:a', 'pcm_s16le', '-write_bext', '1', '-metadata', f'origination_date={local:%Y-%m-%d}',
                        '-metadata', f'origination_time={local:%H:%M:%S}', '-y', str(src2 / name)], check=True, capture_output=True)
    video('V1.MP4', '10:00:00'); video('V2.MP4', '10:01:10'); video('V3.MP4', '11:30:00', sound=False)
    bwf('ZOOM0001.WAV', epoch('09:59:50'), 90)      # acopera V1 si V2
    bwf('ZOOM0002.WAV', epoch('10:01:00'), 5400)    # acopera V2 ... V3
    w.open_source(str(src2))
    by = {c.name: c for c in w.all_clips}
    check(sorted(by) == ['V1.MP4', 'V2.MP4', 'V3.MP4', 'ZOOM0001.WAV', 'ZOOM0002.WAV'], f'audio in grila ({sorted(by)})')
    check(by['ZOOM0001.WAV'].kind == 'audio' and abs(by['ZOOM0001.WAV'].created - epoch('09:59:50')) < 2, 'ora din BWF citita corect')
    check([by[n].group for n in ('V1.MP4', 'V2.MP4', 'V3.MP4', 'ZOOM0001.WAV', 'ZOOM0002.WAV')] == [1, 1, 2, 1, 1],
          f'audio in grupul clipurilor ({[by[n].group for n in sorted(by)]})')
    check(wait(lambda: not w.pending, 120), 'forme de unda si niveluri gata')
    check(all(main.wave_file(by[n].key).exists() for n in ('ZOOM0001.WAV', 'ZOOM0002.WAV')), 'forma de unda pentru audio')
    check(bool(by['V1.MP4'].levels) and max(by['V1.MP4'].levels) > -40, f'nivel sunet masurat ({by["V1.MP4"].levels})')
    check(by['V3.MP4'].levels == [] and not by['V3.MP4'].audio, 'clip fara sunet recunoscut')
    w.kind_box.setCurrentIndex(2)
    check(sorted(c.name for c in w.model.clips) == ['ZOOM0001.WAV', 'ZOOM0002.WAV'], 'filtru doar audio')
    w.kind_box.setCurrentIndex(1)
    check(sorted(c.name for c in w.model.clips) == ['V1.MP4', 'V2.MP4', 'V3.MP4'], 'filtru doar video')
    w.kind_box.setCurrentIndex(0)
    w.restore_selection({src2 / 'V1.MP4', src2 / 'V2.MP4'})
    check(w.sync_follow == {by['ZOOM0001.WAV'].key} and w.sync_partial == {by['ZOOM0002.WAV'].key}, 'SYNC si SYNC partial marcate')
    w.grab().save(str(TMP / 'captura_audio.png'))
    key(Qt.Key.Key_Q)  # partea cu sunet: nu trebuie sa dea eroare
    w.move_selection(0); wait(lambda: not w.moving)
    acasa2 = TMP / 'proiect2' / 'Acasa'
    check(sorted(p.name for p in acasa2.iterdir()) == ['V1.MP4', 'V2.MP4', 'ZOOM0001.WAV'], 'audio sincron mutat cu clipurile')
    check((src2 / 'ZOOM0002.WAV').exists(), 'audio partial ramane')
    w.restore_selection({src2 / 'V3.MP4'})
    check(w.sync_follow == {by['ZOOM0002.WAV'].key}, 'audio partial devine SYNC la ultimul clip')
    w.move_selection(1); wait(lambda: not w.moving)
    check(w.report_box.isVisible() and 'Biserica: 2' in w.report_box.text(), 'rezumat la final, cu audio numarat')
    w.report_box.close()
    check(sorted(p.name for p in (TMP / 'proiect2' / 'Biserica').iterdir()) == ['V3.MP4', 'ZOOM0002.WAV'], 'audio lung mutat cu ultimul clip')
    w.undo(); wait(lambda: not w.moving)
    check((src2 / 'V3.MP4').exists() and (src2 / 'ZOOM0002.WAV').exists(), 'anularea readuce si audio-ul')
    w.audio_follow.setChecked(False)
    w.restore_selection({src2 / 'V3.MP4'})
    check(not w.sync_follow, 'fara bifa, audio-ul nu mai urmeaza clipurile')
    w.audio_follow.setChecked(True)

    # ---------- LUT: un cub care inverseaza culorile, usor de verificat pe pixeli
    from PySide6.QtGui import QImage, QColor
    inv = TMP / 'inversare.cube'
    inv.write_text('LUT_3D_SIZE 2\n' + ''.join(f'{1 - r} {1 - g} {1 - b}\n' for b in (0, 1) for g in (0, 1) for r in (0, 1)))
    bad = TMP / 'unu_d.cube'
    bad.write_text('LUT_1D_SIZE 2\n0 0 0\n1 1 1\n')
    check(w.load_lut(str(bad)) is None, 'LUT 1D refuzat')
    v3 = next(c for c in w.all_clips if c.name == 'V3.MP4')
    w.set_project_lut(str(inv))
    tag = w.load_lut(str(inv)).tag
    check(w.fkey(v3) == f'{v3.key}_{tag}', 'miniaturile cu LUT au cheie separata')
    check(wait(lambda: not w.pending, 60) and main.frame_file(w.fkey(v3), main.POSTER).exists(), 'miniatura cu LUT generata')
    plain, graded = QImage(str(main.frame_file(v3.key, main.POSTER))), QImage(str(main.frame_file(w.fkey(v3), main.POSTER)))
    spots = [(plain.width() * x // 8, plain.height() // 3) for x in (1, 3, 5, 7)]
    inverted = all(abs(QColor(plain.pixel(*s)).red() + QColor(graded.pixel(*s)).red() - 255) < 50 and
                   abs(QColor(plain.pixel(*s)).green() + QColor(graded.pixel(*s)).green() - 255) < 50 for s in spots)
    check(inverted, 'LUT aplicat pe miniatura (culori inversate)')
    sample = QImage(4, 4, QImage.Format.Format_RGB888); sample.fill(QColor(200, 50, 10))
    out = QColor(w.load_lut(str(inv)).apply(sample).pixel(1, 1))
    check(abs(out.red() - 55) <= 3 and abs(out.green() - 205) <= 3 and abs(out.blue() - 245) <= 3,
          f'LUT pe previzualizare ({out.red()}, {out.green()}, {out.blue()})')
    w.restore_selection({src2 / 'V3.MP4'})
    if not main.MEDIA_ERROR:  # fara QtMultimedia nu exista previzualizare video deloc
        check(w.preview_stack.currentIndex() == 1 and w.preview_lut is not None, 'previzualizarea trece prin LUT')
    shown = main.MEDIA_ERROR or wait(lambda: w.lut_view.pixmap() is not None and not w.lut_view.pixmap().isNull(), 15)
    if not shown:  # depinde de redarea video a sistemului; pe serverele de build poate lipsi
        print('INFO previzualizarea cu LUT nu a primit cadre in 15 s', flush=True)
        report(f'{sys.platform}: previzualizarea cu LUT nu a primit cadre', 'warning')
    w.project()['reguli_lut'] = [{'prefix': 'v3', 'lut': ''}]
    w.apply_lut_change()
    check(w.fkey(v3) == v3.key and w.preview_stack.currentIndex() == 0, 'regula pe camera: fara LUT pentru V3')
    w.project()['reguli_lut'] = []
    w.set_project_lut('')
    check(w.fkey(v3) == v3.key and w.project()['lut'] == '', 'LUT scos')
    if not main.MEDIA_ERROR:
        # din semnalul "clip incarcat" playerul nu trebuie atins direct: in fereastra reala se blocheaza
        calls = []
        w.player.pause = lambda: calls.append('pause')
        w.player.mediaStatus = lambda: main.QMediaPlayer.MediaStatus.LoadedMedia
        w.player.playbackState = lambda: main.QMediaPlayer.PlaybackState.PausedState
        w.media_status(main.QMediaPlayer.MediaStatus.LoadedMedia)
        check(not calls, 'pauza nu se cere din semnalul playerului (fara blocaj)')
        wait(lambda: calls, 5)
        check(bool(calls) and set(calls) == {'pause'}, 'cadrul de previzualizare apare imediat dupa incarcare')
        del w.player.pause, w.player.mediaStatus, w.player.playbackState
    sony = Path('/Applications/Adobe Premiere Pro 2023/Adobe Premiere Pro 2023.app/Contents/Lumetri/LUTs/1_SGamut3CineSLog3_To_LC-709.cube')
    if sony.exists():
        lut = main.CubeLut(sony)
        grey = QImage(2, 2, QImage.Format.Format_RGB888); grey.fill(QColor(105, 105, 105))  # gri 18% in S-Log3
        out = QColor(lut.apply(grey).pixel(0, 0))
        check(lut.size == 33 and 90 < out.red() < 140 and abs(out.red() - out.green()) < 12, f'LUT Sony S-Log3: gri 105 > {out.red()}')

    # ---------- gamma camerei: originale Sony cu XML, transcodate fara, invatate dupa prefix
    src3 = TMP / 'proiect3' / 'Originale'; src3.mkdir(parents=True)
    src4 = TMP / 'proiect3' / 'ProRes'; src4.mkdir(parents=True)
    def camera_clip(path, gamma=None, model=None):
        args = [main.FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=2', '-c:v', 'prores_ks']
        if gamma:
            xml = (f'<NonRealTimeMeta><Item name="CaptureGammaEquation" value="{gamma}"/>'
                   f'<Device manufacturer="Sony" modelName="{model}" serialNo="1"/></NonRealTimeMeta>')
            args += ['-metadata', f'comment={xml}']
        subprocess.run(args + ['-f', 'mov', '-y', str(path)], check=True, capture_output=True)
    camera_clip(src3 / 'DAN0001.MP4', 's-log3-cine', 'ZV-E1'); camera_clip(src3 / 'URDEA0001.MP4', 'rec709', 'ILCE-7SM3')
    camera_clip(src3 / 'DAN0003.MP4', 'rec709', 'ZV-E1')  # aceeasi camera, profil schimbat in timpul filmarii
    for name in ('DAN0001.MP4', 'DAN0002.MP4', 'DAN0003.MP4', 'URDEA0002.MP4', 'X0001.MP4'):
        camera_clip(src4 / name)
    w.settings['lut_gamma'] = {'s-log3-cine': str(inv)}
    w.open_source(str(src3))
    by = {c.name: c for c in w.all_clips}
    check(by['DAN0001.MP4'].gamma == 's-log3-cine' and by['DAN0001.MP4'].camera == 'Sony ZV-E1', 'gamma si camera citite din Sony')
    check(w.lut_for(by['DAN0001.MP4']) is not None and w.lut_for(by['DAN0001.MP4']).tag == tag, 'S-Log3 primeste LUT automat')
    check(w.lut_for(by['URDEA0001.MP4']) is None, 'rec709 ramane fara LUT')
    check('SLOG3' in by['DAN0001.MP4'].badge(), f'eticheta SLOG3 pe miniatura ({by["DAN0001.MP4"].badge()})')
    w.set_project_lut(str(inv))
    check(w.lut_for(by['URDEA0001.MP4']) is None, 'LUT-ul proiectului nu strica clipurile rec709')
    w.project()['reguli_lut'] = [{'prefix': 'ZV-E1', 'lut': ''}]
    check(w.lut_for(by['DAN0001.MP4']) is None, 'regula dupa modelul camerei')
    w.project()['reguli_lut'] = []
    w.open_source(str(src4))
    by = {c.name: c for c in w.all_clips}
    check(by['DAN0001.MP4'].gamma == 's-log3-cine' and by['DAN0001.MP4'].gamma_guess and w.lut_for(by['DAN0001.MP4']) is not None,
          'ProRes: gamma mostenita dupa nume si durata (S-Log3 > LUT)')
    check(by['DAN0003.MP4'].gamma == 'rec709' and w.lut_for(by['DAN0003.MP4']) is None, 'ProRes: acelasi prefix dar rec709 > fara LUT')
    check(by['DAN0002.MP4'].gamma == '', 'fara original si prefix amestecat: gamma necunoscuta')
    check(by['URDEA0002.MP4'].gamma == 'rec709' and w.lut_for(by['URDEA0002.MP4']) is None, 'prefix cu profil constant: dedus (rec709)')
    check(by['X0001.MP4'].gamma == '' and w.lut_for(by['X0001.MP4']) is None, 'camera necunoscuta: LUT-ul proiectului (aici fara)')
    menus = [a.text() for a in w.menuBar().actions()]
    check(menus == ['Fisier', 'Editare', 'Foldere', 'Vizualizare', 'Previzualizare', 'Ajutor'], f'meniul de sus ({menus})')
    w.forget([str(src4)])
    check(w.source is None and str(src4) not in w.settings['proiecte'] and str(src4) not in w.settings['recente']
          and w.model.rowCount() == 0 and (src4 / 'DAN0002.MP4').exists(), 'sesiunea stearsa, fisierele raman')
    w.open_source(str(src3))
    check(w.model.rowCount() == 3, 'alta sesiune se deschide normal dupa stergere')
    cats_before = [c['nume'] for c in w.cats]
    w.close_session()
    check(w.source is None and w.model.rowCount() == 0 and not w.cats and 'ultima_sursa' not in w.settings
          and str(src3) in w.settings['proiecte'] and str(src3) in w.settings['recente'], 'sesiunea inchisa, dar salvata')
    w.open_source(str(src3))
    check(w.model.rowCount() == 3 and [c['nume'] for c in w.cats] == cats_before, 'sesiunea redeschisa e cum a ramas')
    w.settings['lut_gamma'] = {}
    w.grab().save(str(TMP / 'captura.png'))
    w.close()
except Exception:
    check.failed = True
    print(traceback.format_exc(), flush=True)
    report(f'{sys.platform}: exceptie\n' + traceback.format_exc())
print('REZULTAT:', 'ESEC' if check.failed else 'TOATE TESTELE AU TRECUT', '·', TMP)
sys.exit(1 if check.failed else 0)
