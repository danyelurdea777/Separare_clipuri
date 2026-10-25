## Ce descarci (sectiunea Assets, mai jos)

- **Windows**: `SeparareClipuri-Windows.zip`
- **Mac cu procesor Intel**: `SeparareClipuri-Mac-Intel.dmg`
- **Mac cu M1, M2, M3, M4...**: `SeparareClipuri-Mac-AppleSilicon.dmg` (vezi meniul Apple > About This Mac > Chip)

ffmpeg este inclus in toate pachetele; nu trebuie instalat nimic altceva.

## Windows

1. Click dreapta pe zip > **Extract All** (Extrage tot), de exemplu in `Documente`.
2. Deschide folderul `SeparareClipuri` si dublu click pe **SeparareClipuri.exe**.
3. La primul start Windows poate afisa "Windows protected your PC": apasa **More info** > **Run anyway**. Aplicatia nu e semnata digital, de aceea apare mesajul.

Scurtatura pe Desktop: click dreapta pe `SeparareClipuri.exe` > Send to > Desktop.

## Mac

1. Deschide `.dmg`-ul si trage **Separare Clipuri** peste folderul **Applications**.
2. La primul start macOS spune ca nu poate verifica aplicatia (nu e semnata la Apple). Apasa **Done**, apoi **System Settings > Privacy & Security**, jos la "Separare Clipuri was blocked", **Open Anyway**.
3. La prima deschidere a unui SSD extern, macOS cere acces la volum: **Allow**.

## Folosire pe scurt

- **Deschide folder clipuri** si alegi folderul cu clipurile de sortat. Folderele categoriilor se creeaza langa el.
- Selectezi clipurile (click, Cmd/Ctrl+click, Shift+click sau tragi un dreptunghi), apoi apesi tasta folderului (1, 2, 3...) sau click pe folder.
- **G** selecteaza tot momentul filmat (grupul), **Spatiu** reda clipul, **Cmd/Ctrl+Z** anuleaza ultima mutare.
- **Selecteaza scurte** + **Cmd+Backspace** (Mac) sau **Delete** (Windows): testele de expunere merg in Cos.
- Fisierele audio de la recorder (WAV) apar langa clipuri si se muta automat cu clipurile filmate in acelasi timp (marcaj **SYNC**).
- Barele de pe miniaturi arata unde e sunet; **Q** reda partea cu sunet.
- **LUT** (dreapta jos): alegi un `.cube` (S-Log3, C-Log, V-Log, D-Log) si miniaturile si previzualizarea apar corectate; **Pe camera** pune LUT diferit dupa numele fisierului (ex: DJI).
- Ghidul complet: **F1** in aplicatie.

ffmpeg: Windows, build LGPL de la BtbN/FFmpeg-Builds; Mac, build static de la ffmpeg.martin-riedl.de. Licentele ffmpeg se aplica acestor executabile.
