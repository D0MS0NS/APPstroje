# Půjčovna strojů – Qt Full

Tahle verze spouští přímo nový frontend v PySide6/Qt.

## Co je převedené do Qt
- dashboard
- stroje: seznam, přidání, úprava, detail, fotky, příslušenství, PDF štítek
- zákazníci: seznam, přidání, úprava, detail + historie
- smlouvy: vytvoření, detail, vrácení, PDF smlouvy / vratný protokol
- rezervace: vytvoření, detail
- servis: vytvoření, úprava, dokončení, detail, PDF protokol
- nastavení
- globální hledání
- export CSV
- záloha databáze

## Spuštění
```bash
pip install -r requirements.txt
python app.py
```

ve Windows můžeš použít:
- `spustit_aplikaci.bat`

## Poznámka
Databázová vrstva zůstává stejná jako ve funkční verzi, ale UI už je čistě v Qt.
