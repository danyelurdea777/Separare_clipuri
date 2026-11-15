# Separare Clipuri

Muti clipurile transcodate in foldere pe categorii (Biserica, Restaurant, Acasa...), direct din miniaturi, ca in Adobe Bridge. Apoi folderele intra la sync.

## Pregătirea unui eveniment

1. Apasă **Pregătire eveniment…** și alege folderul general de scanat. Dacă ai deja o sesiune deschisă, calea este completată.
2. Lasă **Scanează subfolderele · Sony + RØDE + F6** pentru un eveniment cu mai multe carduri. Alege destinația categoriilor: același folder sau un alt folder de pe același disc.
3. Alege șablonul și bifează doar categoriile utile. **Scanează și pregătește** deschide lista **Nesortate** și creează folderele bifate. Pentru foldere goale fără scanare, alege **Doar creează foldere**.
4. Scanarea Sony caută video în `M4ROOT/CLIP`, audio în folderele RØDE și WAV/BWF cu pistele F6 bifate (implicit **Tr1, Tr2, Tr6**). Mixul TrL_R, proxy-urile din SUB și folderele de sortare cunoscute sunt omise. Fișierele apar direct din locația lor; scanarea nu copiază și nu mută nimic.
5. Pentru un singur folder plat, folosește **Deschide folder clipuri** (Cmd+O) sau trage-l din Finder. Într-o sesiune fără profil, se citesc doar fișierele aflate direct în acel folder; destinația inițială este, de regulă, folderul părinte.

**Eveniment curent** arată ce ai deschis. **Sesiuni recente** schimbă sau redeschide sesiunea; nu trebuie să alegi din nou folderul după pregătire.

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

- **▶ Redă / ⏸ Pauză**, **Spațiu** sau click pe imagine.
- **J / L** inapoi / inainte 5 secunde, **Q** partea cu sunet, **M** sunet pornit / oprit, viteze 1x, 2x, 4x.
- **Enter** sau dublu click deschide clipul in IINA; **R** il arata in Finder.
- "Reda automat clipul selectat" porneste redarea la fiecare selectie (ProRes 4K poate fi greu pe Mac Intel; implicit e oprit).

## Răsfoire, sortare și foldere

- **Răsfoire** este modul de pornire. Etichetele deschise, cu folder albastru, afișează conținutul în aplicație. Mutarea prin click, taste sau tragere este blocată.
- **Sortare** se activează din comutatorul deasupra folderelor. Etichetele colorate, cu săgeată spre stânga, mută selecția. Folosește click, tastele **1–9 și 0** pentru primele zece categorii sau trage selecția peste folder.
- **Finder** deschide folderul de pe disc fără să mute clipuri sau să schimbe modul. **Vezi conținutul**, din meniul de click dreapta al categoriei, revine în Răsfoire. **Înapoi la nesortate** afișează sursa.
- **+ Etichetă** adaugă numele în listă; folderul se creează la prima mutare. **+ Folder nou** îl creează imediat. Click dreapta pe categorie permite schimbarea culorii, ordinii, redenumirea sau scoaterea din listă; scoaterea etichetei nu șterge folderul.
- Numărul din paranteze arată câte fișiere sunt în categorie; **(nou)** înseamnă că folderul nu există încă.

## Audio (recordere, lavaliere)

- Fisierele audio (WAV, BWF, MP3, M4A, FLAC, AIFF) apar in grila langa clipuri, pe carduri mov, cu forma de unda in loc de imagine. Plimbi mouse-ul peste ele si vezi pozitia.
- Ora inregistrarii se citeste din WAV-urile de la Zoom, Tascam, Sound Devices (BWF). La alte fisiere se deduce din ora la care s-a terminat inregistrarea.
- Audio-ul intra in grupul clipurilor filmate in acelasi timp, deci **G** il selecteaza impreuna cu ele.
- **Audio sincron merge cu clipurile** este inițial debifată în profilul Sony + RØDE + F6. Când o activezi, clipurile asociate după oră primesc marcajul **SYNC**, iar profilul îți arată lista și cere confirmare înainte de mutare.
- **SYNC partial** (chenar punctat): inregistrarea acopera si alte clipuri inca nesortate (de ex. recorderul a mers toata slujba). Ramane pe loc si pleaca odata cu ultimul clip cu care se suprapune. Daca vrei altfel, o selectezi si o muti manual.
- Ceasurile camerei si recorderului trebuie sa fie sincronizate (toleranta: 5 secunde).
- Lista de sus **Video si audio / Doar video / Doar audio** arata doar ce te intereseaza; filtrul schimbă afișarea, nu bifa pentru mutarea audio.

## Sunet

- Pe fiecare miniatura, **barele din dreapta jos** arata nivelul sunetului in 8 puncte din clip: gri = liniste, verde = normal, galben = tare, rosu = foarte tare. Vezi dintr-o privire unde sunt discursurile si muzica.
- **FARA SUNET** = clipul nu are pista audio; **LINISTE** = are, dar e aproape mut.
- Sub previzualizare e **forma de unda** a clipului curent, cu pozitia redarii; click sau tragi pe ea ca sa sari in clip.
- **Q** sau **Sunet (Q)** reda clipul de la partea cea mai puternica a sunetului: auzi repede daca e discurs, interviu sau muzica.

## LUT pentru previzualizare

- **Implicit** folosește LUT-ul salvat, cu regulile **Pe cameră**. Clipurile cu profil cunoscut non-log sunt lăsate fără LUT implicit. Pentru material transcodificat, aplicația poate deduce gamma din originale după nume și durată.
- **Fără LUT** dezactivează complet efectul pentru proiect. Alegerea explicită a unui LUT îl aplică previzualizării și miniaturilor video.
- **Încarcă alt LUT (.cube)** permite alegerea fișierului de oriunde și îl copiază în biblioteca locală `data/luts/biblioteca/`. **Folder LUT** deschide biblioteca; **Setează implicit** păstrează LUT-ul pentru proiectele viitoare.
- LUT-ul nu modifică fișierele video. Miniaturile colorizate se păstrează separat în cache.

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

## Mutare, anulare și reluarea sesiunii

- În profilul Sony + RØDE + F6, mutările între discuri sunt blocate. Pe același disc aplicația mută fișierele fără să le copieze. Modul obișnuit poate copia între discuri, verifica dimensiunea, apoi elimina sursa.
- Numele identice primesc un sufix. Fișierele însoțitoare cu același nume de bază se mută împreună cu clipul.
- **Cmd+Z / Anulează ultima mutare** folosește jurnalul `data/jurnal.jsonl`. Dacă un lot reușește doar parțial, fișierele mutate cu succes rămân disponibile pentru anulare și după restart.
- Poți opri sortarea și reveni mâine. Redeschide sesiunea; lista nesortată este citită din nou. După mutări manuale în Finder, apasă **↻ Reîmprospătează** ca să recitești folderul afișat și contoarele fără să pierzi etichetele sau filtrele.
- **Resetare sesiune** revine la Nesortate, golește căutarea, filtrul audio/video și etichetele, apoi trece în Răsfoire. Nu mută sau șterge fișiere. Destinațiile memorate rămân excluse din scanare. Pentru reluare, folosește **Sesiuni recente**, nu resetarea.
- După ultima mutare, dacă nu mai sunt fișiere eligibile în sursă, poți **Încheia sesiunea**, **Rămâne în sesiune** sau deschide destinația în Finder. Sesiunea încheiată rămâne disponibilă în **Sesiuni recente**.

## Fișiere XML: arhivă și SSD

- **Adună XML-urile** caută în destinația evenimentului și subfolderele ei. Creează folderul și eticheta **XML** și, după confirmare, mută fișierele XML în acel folder. Numele duplicate primesc sufix, iar mutarea se poate anula cu **Cmd+Z**. `MEDIAPRO.XML` și directoarele `DATABASE` nu sunt atinse. Eticheta XML deschide folderul în Finder, inclusiv în Sortare.
- **Foldere → Copiază XML lângă clipuri…**: alege folderul XML de pe backup și folderul de lucru de pe SSD. Aplicația caută și în subfoldere, potrivește numele (inclusiv `URDEA1001M01.XML` cu `URDEA1001.MP4`) și copiază XML-ul lângă clip. Omite potrivirile ambigue, fișierele fără pereche și destinațiile existente. Backupul rămâne intact.

## Meniul de sus si sesiunile

- Toate functiile sunt si in meniul de sus: **Fisier, Editare, Foldere, Vizualizare, Previzualizare, Ajutor**, cu scurtaturile lor.
- O **sesiune** = un folder de clipuri deschis, cu folderele alese, LUT-ul si istoricul de anulare.
- Sesiunile se salveaza singure, dupa fiecare schimbare. Ca sa treci la alt proiect deschizi alt folder; cel vechi ramane in **Fisier > Sesiuni recente** si in lista de sus.
- **Fisier > Inchide sesiunea** (Cmd+W) goleste fereastra ca sa incepi de pe curat, fara sa uite nimic; si la urmatoarea pornire aplicatia porneste goala.
- **Fisier > Sterge sesiunea curenta** o uita definitiv pe cea deschisa; **Fisier > Sterge sesiuni...** arata lista, cu cele al caror folder nu mai exista deja bifate. Clipurile si folderele de pe disc nu se ating.
- **Fisier > Goleste miniaturile salvate** elibereaza spatiul ocupat de miniaturi; se refac singure cand deschizi un folder.
- **Cmd+1 / 2 / 3**: video si audio / doar video / doar audio.

## Sesiune cu folder redenumit sau mutat

Dacă aplicația nu mai găsește folderul la pornire sau când deschizi sesiunea din **Sesiuni recente**, apasă **Găsește folderul mutat…** și alege noua locație a sursei. Rămân profilul, etichetele și jurnalul de anulare. Căile din interiorul folderului mutat se actualizează; destinațiile externe rămân la adresa lor. Dacă discul este doar deconectat, apasă **Mai târziu**. Reconectarea nu mută fișiere.

## Alte scurtaturi

- **Cmd+F** cautare in nume, **Cmd+=** / **Cmd+-** miniaturi mai mari / mai mici, **F1** acest ajutor.
- În modul Sortare, clipurile se pot trage și direct în DaVinci Resolve (ca o copiere de referinta, nu se muta).
