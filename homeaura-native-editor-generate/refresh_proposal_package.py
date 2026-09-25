from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh a HomeAura append-only proposal manifest and ZIP package.")
    parser.add_argument("proposal_dir", type=Path)
    parser.add_argument("packages_dir", type=Path)
    args = parser.parse_args()

    proposal_dir = args.proposal_dir.resolve()
    packages_dir = args.packages_dir.resolve()
    artifact_id = proposal_dir.name
    if not proposal_dir.is_dir():
        raise SystemExit(f"Proposal directory does not exist: {proposal_dir}")

    payloads = sorted(
        path
        for path in proposal_dir.iterdir()
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    manifest = {
        "artifact_id": artifact_id,
        "append_only": True,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in payloads
        ],
    }
    manifest_path = proposal_dir / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    packages_dir.mkdir(parents=True, exist_ok=True)
    package_path = packages_dir / f"{artifact_id}.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in [*payloads, manifest_path]:
            archive.write(path, arcname=path.name)

    with zipfile.ZipFile(package_path, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise SystemExit(f"Corrupt ZIP member: {bad_member}")
        expected = {path.name: sha256(path) for path in [*payloads, manifest_path]}
        actual = {name: hashlib.sha256(archive.read(name)).hexdigest().upper() for name in archive.namelist()}
        if actual != expected:
            raise SystemExit("ZIP payload differs from proposal directory.")

    print(json.dumps({
        "artifact_id": artifact_id,
        "manifest_files": len(payloads),
        "package": str(package_path),
        "package_bytes": package_path.stat().st_size,
        "package_sha256": sha256(package_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
