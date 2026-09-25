"""Append-only HA-FH-VIS-003 package lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile

from pathlib import Path
from typing import Any

from agent.floor_heating_grid_layout import build_grid_first_layout
from agent.floor_heating_grid_svg import render_grid_layout
from agent.floor_heating_svg_certificate import capture_git_status


PNG_NAMES = (
    "full-layout.png", "pipes-only.png", "collector-transits-close-up.png",
    "circuit-1-close-up.png", "circuit-2-close-up.png",
    "exterior-wall-three-pass-close-up.png", "centre-turn-c1.png",
    "centre-turn-c2.png", "coverage-diagnostic.png",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, content: str | bytes) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite VIS-003 evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        mode = "wb" if isinstance(content, bytes) else "w"
        arguments = {} if isinstance(content, bytes) else {"encoding": "utf-8", "newline": "\n"}
        with os.fdopen(descriptor, mode, **arguments) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n"


def prepare(build_directory: Path, repositories: list[Path]) -> dict[str, Any]:
    if build_directory.exists():
        raise FileExistsError(f"VIS-003 build directory exists: {build_directory}")
    build_directory.mkdir(parents=True)
    _write_new(
        build_directory / "git_status_baseline.json",
        _json({"repositories": [capture_git_status(repository) for repository in repositories]}),
    )
    geometry = build_grid_first_layout()
    rendered = render_grid_layout(geometry)
    if rendered["report"]["verdict"] != "TWO_SPIRAL_GRID_LAYOUT_READY_FOR_VISUAL_REVIEW":
        raise ValueError(rendered["report"]["verdict"])
    validation = {
        "generation_version": geometry["generation_version"],
        "geometry_digest": geometry["geometry_digest"],
        "global_validation": geometry["global_validation"],
        "spacing_validation": geometry["spacing_validation"],
        "length_reconciliation": rendered["report"]["length_reconciliation"],
        "coverage": geometry["coverage"],
        "verdict": rendered["report"]["verdict"],
    }
    _write_new(build_directory / "canonical_geometry.json", _json(geometry))
    _write_new(build_directory / "validation.json", _json(validation))
    _write_new(build_directory / "floor_heating_layout.svg", rendered["svg"])
    _write_new(build_directory / "floor_heating_layout.html", rendered["html"])
    return {"geometry": geometry, "report": rendered["report"]}


def finalize(build_directory: Path, final_directory: Path, repositories: list[Path]) -> dict[str, Any]:
    if final_directory.exists():
        raise FileExistsError(f"VIS-003 final directory exists: {final_directory}")
    geometry = json.loads((build_directory / "canonical_geometry.json").read_text(encoding="utf-8"))
    validation = json.loads((build_directory / "validation.json").read_text(encoding="utf-8"))
    if validation["verdict"] != "TWO_SPIRAL_GRID_LAYOUT_READY_FOR_VISUAL_REVIEW":
        raise ValueError("REWORK_GRID_GEOMETRY")
    for name in PNG_NAMES:
        path = build_directory / name
        if not path.is_file() or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"missing valid PNG evidence: {name}")
    provenance = json.loads((build_directory / "capture_provenance.json").read_text(encoding="utf-8"))
    if provenance["source_svg_sha256"] != _sha256(build_directory / "floor_heating_layout.svg"):
        raise ValueError("PNG provenance does not match VIS-003 SVG")
    os.replace(build_directory, final_directory)
    _write_new(
        final_directory / "git_status_final.json",
        _json({"repositories": [capture_git_status(repository) for repository in repositories]}),
    )
    artifacts = sorted(path for path in final_directory.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    manifest = {
        "manifest_version": "HA-FH-VIS-003/1.0",
        "geometry_digest": geometry["geometry_digest"],
        "verdict": validation["verdict"],
        "artifacts": [
            {"name": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in artifacts
        ],
    }
    manifest["manifest_digest"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _write_new(final_directory / "artifact_manifest.json", _json(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--finalize", action="store_true")
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--final", type=Path)
    parser.add_argument("--repository", type=Path, action="append", default=[])
    arguments = parser.parse_args()
    repositories = arguments.repository or [Path.cwd()]
    if arguments.prepare:
        value = prepare(arguments.build, repositories)
        print(_json({"verdict": value["report"]["verdict"], "geometry_digest": value["geometry"]["geometry_digest"]}), end="")
    else:
        if arguments.final is None:
            parser.error("--final is required with --finalize")
        print(_json(finalize(arguments.build, arguments.final, repositories)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["PNG_NAMES", "finalize", "prepare"]
