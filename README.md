# Půjčovna strojů – update

## Spuštění
1. Nainstaluj Python 3.11+
2. Otevři terminál v této složce
3. Spusť:

```bash
pip install -r requirements.txt
python app.py
```

Nebo spusť `spustit_aplikaci.bat`.

## Data
Aplikace ukládá data do:

`Dokumenty/PujcovnaStroju/data`

Najdeš tam:
- `app.db` – databáze
- `contracts/` – vygenerované PDF smlouvy
- `backups/` – zálohy databáze

## Co je přidané
- lepší dashboard s kartami a posledními smlouvami
- detail zákazníka
- historie zákazníka s otevřením PDF smlouvy
- detail stroje a historie stroje
- detail smlouvy
- otevření PDF a znovuvytvoření PDF
- rychlé akce v sidebaru
- jemné vizuální přechody


## Novinky v tomto update
- přepracovaný vzhled PDF smlouvy
- dashboard s grafem smluv za měsíce
- nejbližší vrácení
- nejpůjčovanější stroje
- historie zákazníka s otevřením i znovuvytvořením PDF


Aktualizace v8: rezervace, kontrola kolizí, kalendář zápůjček, upravené PDF a opravený layout zákazníků.
