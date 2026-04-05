from __future__ import annotations
import os
from pathlib import Path

APP_NAME = "PujcovnaStroju"
RELEASE_ASSET_NAME = "PujcovnaStroju.exe"


def _read_app_version() -> str:
    version_file = Path(__file__).resolve().parent / "VERSION"
    try:
        value = version_file.read_text(encoding="utf-8").strip()
        return value or "0.0.0"
    except Exception:
        return "0.0.0"


APP_VERSION = _read_app_version()


def resolve_base_dir() -> Path:
    one_drive_candidates = [
        os.environ.get("OneDriveCommercial", "").strip(),
        os.environ.get("OneDriveConsumer", "").strip(),
        os.environ.get("OneDrive", "").strip(),
    ]
    for raw in one_drive_candidates:
        if raw:
            root = Path(raw)
            if root.exists():
                return root / APP_NAME
    return Path.home() / "Documents" / APP_NAME


BASE_DIR = resolve_base_dir()
DATA_DIR = BASE_DIR / "data"
CONTRACTS_DIR = DATA_DIR / "contracts"
BACKUPS_DIR = DATA_DIR / "backups"
EXPORTS_DIR = DATA_DIR / "exports"
LABELS_DIR = DATA_DIR / "labels"
PROTOCOLS_DIR = DATA_DIR / "protocols"
PHOTOS_DIR = DATA_DIR / "photos"
UPDATES_DIR = DATA_DIR / "updates"
DB_PATH = DATA_DIR / "app.db"
THEME_FILE = DATA_DIR / "theme.txt"
APP_LOCK_FILE = DATA_DIR / "app.lock.json"
AUTO_BACKUPS_KEEP = 10

DEFAULT_COMPANY = {
    "company_name": "Moje půjčovna strojů",
    "company_address": "Doplň adresu",
    "company_phone": "Doplň telefon",
    "company_email": "Doplň e-mail",
    "company_ico": "Doplň IČO",
    "company_dic": "",
    "contract_title": "Smlouva o zápůjčce stroje",
    "contract_subtitle": "Doklad o zapůjčení zařízení",
    "contract_place": "V Libčicích nad Vltavou",
    "contract_declaration": "Doplň prohlášení, které má být součástí smlouvy.",
    "contract_terms": "Doplň obchodní podmínky a text smlouvy.",
    "pin_code": "",
    "return_protocol_header_text": "",
    "return_protocol_footer": "Děkujeme za vrácení stroje. Při zjištění skrytých vad může být zákazník dodatečně kontaktován.",
}

for p in [BASE_DIR, DATA_DIR, CONTRACTS_DIR, BACKUPS_DIR, EXPORTS_DIR, LABELS_DIR, PROTOCOLS_DIR, PHOTOS_DIR, UPDATES_DIR]:
    p.mkdir(parents=True, exist_ok=True)


def load_theme() -> str:
    if THEME_FILE.exists():
        txt = THEME_FILE.read_text(encoding="utf-8").strip().lower()
        if txt in {"dark", "light"}:
            return txt
    return "dark"


def save_theme(theme: str) -> None:
    THEME_FILE.write_text(theme, encoding="utf-8")
