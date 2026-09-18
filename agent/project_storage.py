from __future__ import annotations

import hashlib
import os
import stat
import threading

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from agent.atomic_io import (
    create_file_exclusively,
    write_bytes_atomically,
)
from agent.project_foundation import canonical_json_bytes
from agent.project_models import (
    CanonicalProjectModel,
    ProjectJsonError,
)
from agent.project_preview_api import MAX_PROJECT_PAYLOAD_BYTES


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_PROJECTS_ROOT = ROOT_DIRECTORY / "projects"

ERROR_MESSAGES = {
    "project_name_invalid": "Некорректное имя проекта.",
    "project_path_escape": "Путь проекта выходит за каталог projects.",
    "project_not_found": "Canonical project не найден.",
    "project_payload_too_large": "Canonical project превышает 10 MiB.",
    "project_json_invalid": "Canonical project содержит некорректный JSON.",
    "project_identity_conflict": "Идентификатор проекта не совпадает.",
    "project_revision_conflict": "Ревизия проекта конфликтует с хранилищем.",
    "project_history_conflict": "История проекта конфликтует с ревизией.",
    "project_storage_corrupt": "Хранилище canonical project повреждено.",
    "project_storage_io": "Не удалось выполнить операцию хранилища.",
}

_WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
_WINDOWS_INVALID_NAME_CHARACTERS = frozenset('<>:"/\\|?*')
_REPARSE_POINT_ATTRIBUTE = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x0400,
)


class ProjectStorageError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(ERROR_MESSAGES[code])
        self.code = code
        self.message = ERROR_MESSAGES[code]


@dataclass(frozen=True)
class ProjectStorageRecord:
    project_id: UUID
    revision: int
    sha256: str
    canonical_bytes: bytes
    project: CanonicalProjectModel
    created: bool


class ProjectStore:
    def __init__(self, projects_root: Path | None = None) -> None:
        self.projects_root = projects_root or DEFAULT_PROJECTS_ROOT
        self._write_lock = threading.RLock()

    @staticmethod
    def _normalized_path(path: Path) -> str:
        normalized = os.path.normcase(os.path.abspath(str(path)))
        if normalized.startswith("\\\\?\\UNC\\"):
            return "\\\\" + normalized[8:]
        if normalized.startswith("\\\\?\\"):
            return normalized[4:]
        return normalized

    @classmethod
    def _require_within(cls, candidate: Path, root: Path) -> None:
        normalized_candidate = cls._normalized_path(candidate)
        normalized_root = cls._normalized_path(root)
        try:
            common = os.path.commonpath(
                [normalized_candidate, normalized_root]
            )
        except ValueError as error:
            raise ProjectStorageError("project_path_escape") from error
        if common != normalized_root:
            raise ProjectStorageError("project_path_escape")

    @staticmethod
    def _reject_reparse_components(path: Path) -> None:
        """Reject existing symlink/junction components before resolving."""
        absolute = Path(os.path.abspath(str(path)))
        components: list[Path] = []
        current = absolute
        while True:
            components.append(current)
            parent = current.parent
            if parent == current:
                break
            current = parent

        for component in reversed(components):
            try:
                if not os.path.lexists(component):
                    continue
                metadata = os.lstat(component)
            except OSError as error:
                raise ProjectStorageError("project_storage_io") from error
            if stat.S_ISLNK(metadata.st_mode) or (
                getattr(metadata, "st_file_attributes", 0)
                & _REPARSE_POINT_ATTRIBUTE
            ):
                raise ProjectStorageError("project_path_escape")

    @staticmethod
    def _valid_project_name(project_name: str) -> bool:
        if (
            not project_name
            or project_name in {".", ".."}
            or project_name[-1] in {" ", "."}
            or Path(project_name).name != project_name
            or any(
                character in _WINDOWS_INVALID_NAME_CHARACTERS
                or ord(character) < 32
                for character in project_name
            )
        ):
            return False
        stem = project_name.partition(".")[0].upper()
        return stem not in _WINDOWS_RESERVED_NAMES

    def _project_directory(
        self,
        project_name: str,
        *,
        create: bool,
    ) -> Path:
        if not self._valid_project_name(project_name):
            raise ProjectStorageError("project_name_invalid")

        try:
            if create:
                self.projects_root.mkdir(parents=True, exist_ok=True)
            self._reject_reparse_components(self.projects_root)
            self._reject_reparse_components(
                self.projects_root / project_name
            )
            projects_root = self.projects_root.resolve()
            project_directory = (
                self.projects_root / project_name
            ).resolve()
            self._require_within(project_directory, projects_root)
            if create:
                project_directory.mkdir(parents=True, exist_ok=True)
                project_directory = project_directory.resolve()
                self._require_within(project_directory, projects_root)
        except ProjectStorageError:
            raise
        except ValueError as error:
            raise ProjectStorageError("project_path_escape") from error
        except OSError as error:
            raise ProjectStorageError("project_storage_io") from error
        return project_directory

    @staticmethod
    def _descendant(project_directory: Path, *parts: str) -> Path:
        try:
            candidate_path = project_directory.joinpath(*parts)
            ProjectStore._reject_reparse_components(candidate_path)
            resolved_project = project_directory.resolve()
            candidate = candidate_path.resolve()
            ProjectStore._require_within(candidate, resolved_project)
        except ProjectStorageError:
            raise
        except ValueError as error:
            raise ProjectStorageError("project_path_escape") from error
        except OSError as error:
            raise ProjectStorageError("project_storage_io") from error
        return candidate

    @staticmethod
    def _read_bounded(
        path: Path,
        *,
        missing_code: str,
    ) -> bytes:
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_PROJECT_PAYLOAD_BYTES + 1)
        except FileNotFoundError as error:
            raise ProjectStorageError(missing_code) from error
        except OSError as error:
            raise ProjectStorageError("project_storage_io") from error
        if len(raw) > MAX_PROJECT_PAYLOAD_BYTES:
            raise ProjectStorageError("project_payload_too_large")
        return raw

    @staticmethod
    def _parse(raw: bytes) -> CanonicalProjectModel:
        try:
            project = CanonicalProjectModel.model_validate_json(raw)
            if canonical_json_bytes(project) != raw:
                raise ProjectStorageError("project_storage_corrupt")
            return project
        except ProjectStorageError:
            raise
        except ProjectJsonError as error:
            raise ProjectStorageError("project_json_invalid") from error
        except (ValidationError, RecursionError) as error:
            raise ProjectStorageError("project_storage_corrupt") from error

    @staticmethod
    def _record(
        project: CanonicalProjectModel,
        raw: bytes,
        *,
        created: bool,
    ) -> ProjectStorageRecord:
        return ProjectStorageRecord(
            project_id=project.project_id,
            revision=project.revision,
            sha256=hashlib.sha256(raw).hexdigest(),
            canonical_bytes=raw,
            project=project,
            created=created,
        )

    def _paths(
        self,
        project_directory: Path,
        revision: int,
        *,
        create: bool,
    ) -> tuple[Path, Path, Path]:
        canonical_directory = self._descendant(
            project_directory,
            "canonical",
        )
        history_directory = self._descendant(
            project_directory,
            "canonical",
            "history",
        )
        try:
            if create:
                canonical_directory.mkdir(parents=True, exist_ok=True)
                history_directory.mkdir(parents=True, exist_ok=True)
                canonical_directory = self._descendant(
                    project_directory,
                    "canonical",
                )
                history_directory = self._descendant(
                    project_directory,
                    "canonical",
                    "history",
                )
        except OSError as error:
            raise ProjectStorageError("project_storage_io") from error
        current = self._descendant(
            project_directory,
            "canonical",
            "current.json",
        )
        history = self._descendant(
            project_directory,
            "canonical",
            "history",
            f"project.r{revision:08d}.json",
        )
        return current, history, history_directory

    def _validate_current_history(
        self,
        project_directory: Path,
        project: CanonicalProjectModel,
        raw: bytes,
    ) -> None:
        _, history, _ = self._paths(
            project_directory,
            project.revision,
            create=False,
        )
        history_raw = self._read_bounded(
            history,
            missing_code="project_storage_corrupt",
        )
        if history_raw != raw:
            raise ProjectStorageError("project_storage_corrupt")

    def load_current(self, project_name: str) -> ProjectStorageRecord:
        project_directory = self._project_directory(
            project_name,
            create=False,
        )
        current, _, _ = self._paths(
            project_directory,
            1,
            create=False,
        )
        raw = self._read_bounded(
            current,
            missing_code="project_not_found",
        )
        project = self._parse(raw)
        self._validate_current_history(
            project_directory,
            project,
            raw,
        )
        return self._record(project, raw, created=False)

    def _publish_history(
        self,
        history_path: Path,
        raw: bytes,
    ) -> None:
        try:
            create_file_exclusively(history_path, raw)
            return
        except FileExistsError:
            existing = self._read_bounded(
                history_path,
                missing_code="project_history_conflict",
            )
            if existing != raw:
                raise ProjectStorageError("project_history_conflict")
        except OSError as error:
            raise ProjectStorageError("project_storage_io") from error

    def _publish_current(
        self,
        current_path: Path,
        raw: bytes,
    ) -> None:
        try:
            write_bytes_atomically(current_path, raw)
            return
        except OSError as error:
            try:
                existing = self._read_bounded(
                    current_path,
                    missing_code="project_storage_io",
                )
            except ProjectStorageError:
                raise ProjectStorageError(
                    "project_storage_io"
                ) from error
            if existing != raw:
                raise ProjectStorageError(
                    "project_storage_io"
                ) from error

    def save_current_revision(
        self,
        project_name: str,
        project: CanonicalProjectModel,
    ) -> ProjectStorageRecord:
        with self._write_lock:
            return self._save_current_revision(project_name, project)

    def _save_current_revision(
        self,
        project_name: str,
        project: CanonicalProjectModel,
    ) -> ProjectStorageRecord:
        raw = canonical_json_bytes(project)
        if len(raw) > MAX_PROJECT_PAYLOAD_BYTES:
            raise ProjectStorageError("project_payload_too_large")

        project_directory = self._project_directory(
            project_name,
            create=True,
        )
        current, history, history_directory = self._paths(
            project_directory,
            project.revision,
            create=True,
        )

        try:
            current_exists = current.is_file()
        except OSError as error:
            raise ProjectStorageError("project_storage_io") from error

        if not current_exists:
            if project.revision != 1:
                raise ProjectStorageError("project_revision_conflict")
            try:
                unexpected_history = any(
                    self._normalized_path(path)
                    != self._normalized_path(history)
                    for path in history_directory.glob(
                        "project.r*.json"
                    )
                )
            except OSError as error:
                raise ProjectStorageError("project_storage_io") from error
            if unexpected_history:
                raise ProjectStorageError("project_history_conflict")
            self._publish_history(history, raw)
            self._publish_current(current, raw)
            return self._record(project, raw, created=True)

        current_raw = self._read_bounded(
            current,
            missing_code="project_not_found",
        )
        current_project = self._parse(current_raw)
        self._validate_current_history(
            project_directory,
            current_project,
            current_raw,
        )

        if current_project.project_id != project.project_id:
            raise ProjectStorageError("project_identity_conflict")
        if project.revision == current_project.revision:
            if raw != current_raw:
                raise ProjectStorageError("project_revision_conflict")
            return self._record(project, raw, created=False)
        if project.revision != current_project.revision + 1:
            raise ProjectStorageError("project_revision_conflict")

        self._publish_history(history, raw)
        self._publish_current(current, raw)
        return self._record(project, raw, created=True)
