# Release Checklist

## Pred nasazenim

- Spustit `python -m unittest -v tests.test_database`
- Spustit `python -m py_compile app_qt_full.py database.py tests\test_database.py`
- Overit build prikazem `python -m PyInstaller --noconfirm PujcovnaStroju.spec`
- Zkontrolovat, ze vznikl `dist\PujcovnaStroju.exe`
- Pri GitHub releasu nahrat prave lokalni `dist\PujcovnaStroju.exe` do release assetu

## Rucni smoke test

- Otevrit aplikaci a zkontrolovat, ze se nacte prehled bez chyb
- Vytvorit testovaciho zakaznika
- Vytvorit testovy stroj
- Vytvorit rezervaci na volny stroj
- Overit, ze kolizni rezervace je odmitnuta
- Vytvorit smlouvu na volny stroj
- Overit, ze stav stroje prejde na `pujceny`
- Smazat testovou smlouvu
- Overit, ze stav stroje se vrati na `volny`
- Vytvorit servisni zaznam a dokoncit ho
- Overit, ze stav stroje odpovida realnemu workflow
- Otevrit detail zakaznika, stroje, smlouvy a rezervace
- Overit diakritiku v prehledu, detailech a notifikacich
- Vygenerovat PDF smlouvy a vratneho protokolu
- Overit export CSV a vytvoreni zalohy databaze

## Data a obnova

- Udelat zalohu produkcni databaze pred prvnim nasazenim
- Otestovat obnovu zalohy do kopie prostredi
- Overit pristupova prava k adresarum pro PDF, fotky a zalohy

## Po nasazeni

- Provest prvni pracovni den se zapnutym logovanim chyb v konzoli nebo dohledem obsluhy
- Uchovat posledni funkcni build a posledni zalohu databaze
