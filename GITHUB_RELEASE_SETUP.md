# GitHub Release Setup

## Co je pripraveno
- verze aplikace se bere ze souboru `VERSION`
- lokalne ji zmenis prikazem `python scripts/set_version.py 1.0.1`
- GitHub Actions workflow `.github/workflows/release.yml` po tagu `v*`:
  - prepise `VERSION` podle tagu
  - nainstaluje zavislosti
  - postavi `dist/PujcovnaStroju.exe`
  - vytvori GitHub Release a nahraje `.exe`

## Prvni nastaveni repozitare
1. Nahraj projekt do GitHub repozitare.
2. Repo nech verejne, pokud chces nejjednodussi update bez tokenu.
3. V `Settings > Actions > General` nech povolene workflow opravnene `Read and write permissions`.

## Jak udelat prvni release
1. Nastav novou verzi:
   `python scripts/set_version.py 1.0.1`
2. Commitni zmeny:
   `git add VERSION settings.py build_app.bat PujcovnaStroju.spec .github/workflows/release.yml scripts/set_version.py GITHUB_RELEASE_SETUP.md`
   `git commit -m "Prepare release v1.0.1"`
3. Vytvor tag:
   `git tag v1.0.1`
4. Posli commit i tag na GitHub:
   `git push`
   `git push origin v1.0.1`
5. Pockej, az workflow dokonci build.
6. Na GitHubu v sekci `Releases` zkontroluj, ze vznikl release `v1.0.1` a obsahuje `PujcovnaStroju.exe`.

## Nastaveni v aplikaci
V `Nastaveni > Data a zalohy` vypln:
- `GitHub repo`: `uzivatel/repozitar`
- `Nazev souboru`: `PujcovnaStroju.exe`

Pak na druhem PC staci kliknout na `Zkontrolovat aktualizaci`.

## Dulezite poznamky
- auto-update funguje z finalniho `.exe`, ne pri spousteni ze zdrojaku
- aktualizace porovnava verzi z `VERSION` s poslednim GitHub releasem
- release tag musi byt ve tvaru `v1.0.1`
