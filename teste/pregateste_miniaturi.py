"""Citeste metadatele si genereaza miniaturile unui folder, fara sa mute nimic.
Folosire: .venv/bin/python teste/pregateste_miniaturi.py '/cale/folder/clipuri'"""
import os, sys, time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main
from PySide6.QtWidgets import QApplication

app = QApplication([])
w = main.Separator()
w.open_source(sys.argv[1])
app.processEvents()
total = len(w.pending)
start = time.time()
while w.pending:
    app.processEvents()
    time.sleep(0.2)
print(f'{w.model.rowCount()} clipuri, {total} cadre generate in {time.time() - start:.0f} s')
w.close()
