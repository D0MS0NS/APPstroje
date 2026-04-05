# GitHub Release Setup

## Co je pripraveno
- verze aplikace se bere ze souboru `VERSION`
- jednim prikazem `release.bat 1.0.5` se udela:
  - zmena verze
  - kontrolni `py_compile`
  - build `PujcovnaStroju.exe`
  - `git add`, `commit`, `tag`, `push`
  - vytvoreni GitHub releasu
  - nahrani lokalne postaveneho `dist\PujcovnaStroju.exe`

## Jednorazove nastaveni
1. Nahraj projekt do GitHub repozitare.
2. Repo nech verejne, pokud chces nejjednodussi update v aplikaci.
3. Vytvor si GitHub token s pravem `Contents: Read and write`.
4. Na svem PC nastav token do prostredi:

PowerShell pro aktualni okno:
`$env:GITHUB_TOKEN = "github_pat_..."`

Trvale pro dalsi spusteni:
`setx GITHUB_TOKEN "github_pat_..."`

5. Otevri novy PowerShell nebo terminal, pokud jsi pouzil `setx`.

## Jak udelat release
Staci spustit:

`release.bat 1.0.5`

Skript sam:
- postavi novou verzi
- pushne zmeny na GitHub
- vytvori release `v1.0.5`
- nahraje do nej `PujcovnaStroju.exe`

## Nastaveni v aplikaci
V `Nastaveni > Data a zalohy` vypln:
- `GitHub repo`: `D0MS0NS/APPstroje`
- `Nazev souboru`: `PujcovnaStroju.exe`

Pak na druhem PC staci kliknout na `Zkontrolovat aktualizaci`.

## Dulezite poznamky
- auto-update funguje z finalniho `.exe`, ne pri spousteni ze zdrojaku
- aktualizace porovnava verzi z `VERSION` s poslednim GitHub releasem
- release tag musi byt ve tvaru `v1.0.5`
- release uz nevytvari GitHub Actions po tagu, ale lokalni release skript
