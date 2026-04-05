from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def main() -> int:
    if len(sys.argv) != 2:
        print("Pouziti: python scripts/set_version.py 1.2.3")
        return 1
    version = sys.argv[1].strip()
    if not VERSION_RE.fullmatch(version):
        print("Verze musi byt ve formatu major.minor.patch, napriklad 1.2.3")
        return 1
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    print(f"Verze nastavena na {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
