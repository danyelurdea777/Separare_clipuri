# Separare Clipuri

Aplicatie Mac (Python + Qt) cu care muti clipurile transcodate in foldere pe categorii, din miniaturi, inainte de edit si sync. Ghidul complet de folosire este in `AJUTOR.md` (si in aplicatie, F1).

## Pornire

- Dublu click pe **Separare Clipuri.app** (o poti trage in Dock), sau
- dublu click pe **Porneste.command** (Terminalul se inchide singur; ramane deschis doar la eroare).

Daca muti folderul aplicatiei in alt loc, ruleaza din nou `Creeaza_app.command`.

## Windows

La fiecare push pe `main`, GitHub Actions ruleaza testele pe Windows, construieste `SeparareClipuri.exe` (cu ffmpeg inclus) si il publica la **Releases**. Link de dat mai departe, mereu ultima versiune:

https://github.com/danyelurdea777/separare-clipuri/releases/latest

Instructiunile de instalare pentru Windows sunt in `INSTALARE-WINDOWS.md` (apar si pe pagina release-ului).

## Instalare pe alt Mac

```bash
cd "/cale/Separare_clipuri_inainte_de _edit" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && ./Creeaza_app.command
```

Miniaturile si metadatele cer `ffmpeg` si `ffprobe` (aici sunt in `/opt/local/bin`).

## Fisiere

- `main.py`: toata aplicatia
- `AJUTOR.md`: ghidul afisat cu F1
- `data/`: setari, proiecte, sabloane, jurnalul mutarilor (`jurnal.jsonl`), miniaturi si `pornire.log` (erori)
- `teste/test_aplicatie.py`: test automat pe clipuri generate (muta, anuleaza, coliziuni, fisiere insotitoare, Cos); ruleaza pe Mac si Windows
- `.github/workflows/windows.yml`: build-ul Windows
- `teste/pregateste_miniaturi.py`: genereaza dinainte miniaturile unui folder, fara sa mute nimic

## Idei preluate din Culling Studio

Pornirea prin `.command` cu jurnal de erori, tema intunecata si culorile, miniaturile cu ffmpeg in fundal, tastele numerice pentru categorii, selectia multipla si anularea.

## Mai departe

- `.dmg` complet independent (cu Python inclus): PyInstaller sau py2app, cand aplicatia e matura
- Reguli automate (ex: clipurile DJI direct in folderul dronei)
- Stele / marcaj "rebut" inainte de mutare
