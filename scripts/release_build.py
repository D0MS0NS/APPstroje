from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
SPEC_FILE = ROOT / "PujcovnaStroju.spec"
EXE_FILE = ROOT / "dist" / "PujcovnaStroju.exe"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def find_git() -> str:
    candidates = [
        shutil.which("git"),
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise SystemExit("Git nebyl nalezen. Nainstaluj Git nebo ho pridej do PATH.")


def run(cmd: list[str], *, cwd: Path = ROOT) -> str:
    print("> " + " ".join(cmd))
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        raise SystemExit(completed.returncode)
    return completed.stdout.strip()


def parse_repo(origin_url: str) -> str:
    url = origin_url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@github.com:"):
        return url.split(":", 1)[1]
    marker = "github.com/"
    if marker in url:
        return url.split(marker, 1)[1]
    raise SystemExit(f"Nepodarilo se rozpoznat GitHub repo z URL: {origin_url}")


def github_request(
    url: str,
    *,
    token: str,
    method: str = "GET",
    payload: dict | None = None,
    content_type: str = "application/json",
) -> dict | list | None:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "PujcovnaStrojuReleaseScript/1.0",
    }
    if data is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API chyba {exc.code}: {body}") from exc


def github_upload(url: str, *, token: str, asset_path: Path) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "PujcovnaStrojuReleaseScript/1.0",
        "Content-Type": "application/vnd.microsoft.portable-executable",
    }
    request = urllib.request.Request(
        url,
        data=asset_path.read_bytes(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Nahrani assetu selhalo {exc.code}: {body}") from exc


def ensure_clean_tag(git: str, tag_name: str):
    tags = run([git, "tag", "--list", tag_name]).splitlines()
    if any(t.strip() == tag_name for t in tags):
        raise SystemExit(f"Tag {tag_name} uz existuje. Zvol novou verzi.")


def set_version(version: str):
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")


def build_release(version: str, git: str, token: str):
    repo_url = run([git, "remote", "get-url", "origin"])
    repo = parse_repo(repo_url)
    tag_name = f"v{version}"

    ensure_clean_tag(git, tag_name)
    set_version(version)

    run([sys.executable, "-m", "py_compile", "app_qt_full.py", "app.py", "settings.py", "database.py", "pdf_generator.py", "utils.py"])
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC_FILE.name)])

    if not EXE_FILE.exists():
        raise SystemExit(f"Nepodarilo se najit vystupni EXE: {EXE_FILE}")

    run([git, "add", "-A"])
    run([git, "commit", "-m", f"Prepare release {tag_name}"])
    run([git, "tag", tag_name])
    run([git, "push"])
    run([git, "push", "origin", tag_name])

    release_api = f"https://api.github.com/repos/{repo}/releases"
    release_payload = {
        "tag_name": tag_name,
        "name": tag_name,
        "draft": False,
        "prerelease": False,
        "generate_release_notes": True,
    }
    release = github_request(release_api, token=token, method="POST", payload=release_payload)
    if not isinstance(release, dict):
        raise SystemExit("GitHub nevratil data releasu.")

    for asset in release.get("assets", []):
        if str(asset.get("name")) == EXE_FILE.name:
            github_request(asset["url"], token=token, method="DELETE")

    upload_url_template = str(release.get("upload_url", ""))
    upload_url = upload_url_template.split("{", 1)[0] + "?" + urllib.parse.urlencode({"name": EXE_FILE.name})
    github_upload(upload_url, token=token, asset_path=EXE_FILE)

    print()
    print(f"Release {tag_name} je hotovy.")
    print(f"Repo: https://github.com/{repo}/releases/tag/{tag_name}")
    print(f"Asset: {EXE_FILE}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Pouziti: python scripts/release_build.py 1.0.5")
        return 1
    version = sys.argv[1].strip()
    if not VERSION_RE.fullmatch(version):
        print("Verze musi byt ve formatu major.minor.patch, napriklad 1.0.5")
        return 1
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("Chybi GITHUB_TOKEN nebo GH_TOKEN.")
        print("Jednorazove nastav treba v PowerShellu:")
        print('$env:GITHUB_TOKEN = "github_pat_..."')
        return 1
    git = find_git()
    build_release(version, git, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
