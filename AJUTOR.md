# Separare Clipuri

Muti clipurile transcodate in foldere pe categorii (Biserica, Restaurant, Acasa...), direct din miniaturi, ca in Adobe Bridge. Apoi folderele intra la sync.

## Pornire rapida

1. **Deschide folder clipuri** (Cmd+O) sau trage folderul din Finder peste fereastra. Ex: `Video Botez/Prores`.
2. Destinatia implicita este folderul parinte (`Video Botez`), deci categoriile apar langa `Prores`. O schimbi din butonul **Destinatie**.
3. Prima data se citesc durata si ora filmarii (cateva secunde), apoi miniaturile se genereaza in fundal.
4. Selectezi clipurile, apoi apesi tasta folderului (1, 2, 3...) sau click pe folder. Clipurile dispar din grila si selectia trece pe urmatorul clip.

## Selectie

- Click, **Cmd+click** (adaugi/scoti), **Shift+click** (interval), sau tragi un dreptunghi pe spatiul gol.
- **Cmd+A** selecteaza tot ce se vede.
- **G** selecteaza tot grupul de filmare al clipurilor selectate.
- **Esc** goleste selectia.

## Grupuri de filmare

Clipurile sunt ordonate dupa ora filmarii (din metadatele camerei). Cand intre doua clipuri e o pauza mai mare decat "Grup nou dupa X min", incepe un grup nou. Fiecare grup are o banda colorata si eticheta `G3` pe miniatura.

La un botez, de obicei un grup = un moment (acasa, biserica, restaurant). Flux rapid: click pe primul clip, **G**, tasta folderului. Daca grupurile ies prea mari sau prea mici, schimba numarul de minute.

## Derulare din miniatura

Plimba mouse-ul de la stanga la dreapta peste o miniatura: vezi 8 cadre din tot clipul, fara sa-l deschizi. Bara galbena arata pozitia.

## Previzualizare (dreapta)

- **Spatiu** reda / pauza, click pe imagine la fel.
- **J / L** inapoi / inainte 5 secunde, **M** sunet pornit / oprit, viteze 1x, 2x, 4x.
- **Enter** sau dublu click deschide clipul in IINA; **R** il arata in Finder.
- "Reda automat clipul selectat" porneste redarea la fiecare selectie (ProRes 4K poate fi greu pe Mac Intel; implicit e oprit).

## Folderele (stanga)

- Primele 10 foldere au tastele **1-9** si **0**. Restul merg prin click, tragere sau click dreapta pe clip > Muta in.
- Poti trage clipurile din grila peste un buton de folder.
- **+ Eticheta**: adauga numele in lista; folderul se creeaza la prima mutare.
- **+ Folder nou** (Cmd+N): creeaza imediat folderul pe disc.
- Click dreapta pe clipuri > **Folder nou si muta aici**: creezi folderul si muti selectia dintr-un pas.
- Click dreapta pe un folder: vezi continutul, deschide in Finder, redenumeste (si pe disc), culoare, ordine, scoate din lista (folderul ramane pe disc).
- **Vezi**: arata ce ai mutat deja acolo. De acolo poti muta mai departe in alt folder sau "Inapoi in nesortate". **Inapoi la nesortate** revine la sursa.
- Numarul dintre paranteze = cate clipuri sunt deja in folder; "(nou)" = folderul nu exista inca pe disc.

## Teste de expunere si clipuri pornite din greseala

- **Selecteaza scurte** (langa cautare) selecteaza toate clipurile mai scurte decat limita aleasa (implicit sub 2 s).
- Le verifici rapid din miniaturi, scoti cu Cmd+click ce vrei sa pastrezi, apoi **Sterge in Cos** (butonul rosu din stanga, **Cmd+Backspace** sau click dreapta).
- Merg in Cosul macOS, nu se sterg definitiv. **Cmd+Z** le readuce la locul lor cat timp nu golesti Cosul.
- Pe SSD-ul extern, Cosul ocupa spatiu pe acelasi disc pana il golesti.

## Sabloane de foldere

- **Botez (arhiva mea)**: Acasa, Biserica, Restaurant, Sedinta Video, Interviuri, dji mini pro 4 (din arhiva ta).
- **Nunta**: lista mai lunga, pentru nunti.
- "Salveaza lista curenta ca sablon" pastreaza lista pentru urmatoarele proiecte.
- La un proiect nou: daca in destinatie exista deja foldere cu clipuri, ele devin lista; altfel se foloseste ultimul sablon ales.

## Siguranta

- Mutarea pe acelasi disc este o simpla redenumire: instantanee, fara copiere.
- Pe alt disc: copiere, verificare marime, apoi stergerea originalului, in fundal.
- Nimic nu se sterge si nimic nu se suprascrie: la nume identic se adauga " (2)".
- Fisierele insotitoare cu acelasi nume (.XML Sony, .LRF/.SRT DJI, .THM) se muta impreuna cu clipul.
- **Cmd+Z** / "Anuleaza ultima mutare" muta inapoi ultimul lot. Merge de mai multe ori si chiar dupa redeschiderea aplicatiei (jurnalul e in `data/jurnal.jsonl`).
- Cand sursa se goleste, aplicatia arata un rezumat pe foldere.

## Alte scurtaturi

- **Cmd+F** cautare in nume, **Cmd+=** / **Cmd+-** miniaturi mai mari / mai mici, **F1** acest ajutor.
- Clipurile se pot trage si direct in DaVinci Resolve (ca o copiere de referinta, nu se muta).
