from __future__ import annotations

import errno
import json
import os
import tempfile

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.atomic_io import create_file_exclusively
from agent.domain_adapter import adapt_rooms_payload
from agent.project_foundation import (
    build_project_seed,
    canonical_json_bytes,
    sheet_manifest_reference,
)
from agent.project_models import (
    CanonicalProjectModel,
    ProjectLifecycleStatus,
)
from agent.project_preview_api import MAX_PROJECT_PAYLOAD_BYTES
from agent.project_storage import (
    ProjectStorageError,
    ProjectStore,
)


ROOT = Path(__file__).resolve().parents[1]
ROOMS_FIXTURE = ROOT / "tests" / "fixtures" / "rooms_v1_0.json"
FIXED_TIME = datetime(2026, 8, 1, tzinfo=timezone.utc)


def project_model(
    *,
    identity: str = "storage-test",
    revision: int = 1,
    status: ProjectLifecycleStatus = ProjectLifecycleStatus.DRAFT,
) -> CanonicalProjectModel:
    rooms = json.loads(ROOMS_FIXTURE.read_text(encoding="utf-8"))
    domain = adapt_rooms_payload(rooms, project_id=identity)
    seed = build_project_seed(domain, [], created_at=FIXED_TIME)
    return CanonicalProjectModel(
        project_id=domain.project.stable_id,
        revision=revision,
        status=status,
        domain=domain,
        seed=seed,
        sheet_manifest=sheet_manifest_reference(),
    )


def assert_code(error: pytest.ExceptionInfo[ProjectStorageError], code: str) -> None:
    assert error.value.code == code
    assert set(vars(error.value)) == {"code", "message"}


def test_create_load_idempotent_and_next_revision() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = ProjectStore(Path(directory) / "projects")
        revision_one = project_model()

        created = store.save_current_revision("SafeProject", revision_one)
        repeated = store.save_current_revision("SafeProject", revision_one)
        loaded = store.load_current("SafeProject")
        revision_two = revision_one.model_copy(update={"revision": 2})
        advanced = store.save_current_revision(
            "SafeProject",
            revision_two,
        )

        assert created.created is True
        assert repeated.created is False
        assert loaded.canonical_bytes == canonical_json_bytes(revision_one)
        assert advanced.created is True
        assert store.load_current("SafeProject").revision == 2
        history = (
            Path(directory)
            / "projects"
            / "SafeProject"
            / "canonical"
            / "history"
        )
        assert sorted(path.name for path in history.iterdir()) == [
            "project.r00000001.json",
            "project.r00000002.json",
        ]


def test_same_revision_different_bytes_conflicts() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = ProjectStore(Path(directory) / "projects")
        original = project_model()
        changed = original.model_copy(
            update={"status": ProjectLifecycleStatus.BLOCKED}
        )
        store.save_current_revision("SafeProject", original)

        with pytest.raises(ProjectStorageError) as raised:
            store.save_current_revision("SafeProject", changed)

        assert_code(raised, "project_revision_conflict")


def test_identity_and_skipped_revision_conflict() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = ProjectStore(Path(directory) / "projects")
        original = project_model()
        store.save_current_revision("SafeProject", original)

        with pytest.raises(ProjectStorageError) as identity:
            store.save_current_revision(
                "SafeProject",
                project_model(identity="different", revision=2),
            )
        with pytest.raises(ProjectStorageError) as skipped:
            store.save_current_revision(
                "SafeProject",
                original.model_copy(update={"revision": 3}),
            )

        assert_code(identity, "project_identity_conflict")
        assert_code(skipped, "project_revision_conflict")


def test_existing_matching_history_recovers_interrupted_publish() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        store = ProjectStore(root)
        first = project_model()
        second = first.model_copy(update={"revision": 2})
        store.save_current_revision("SafeProject", first)
        history = (
            root
            / "SafeProject"
            / "canonical"
            / "history"
            / "project.r00000002.json"
        )
        history.write_bytes(canonical_json_bytes(second))

        recovered = store.save_current_revision("SafeProject", second)

        assert recovered.created is True
        assert store.load_current("SafeProject").revision == 2


def test_matching_first_history_recovers_missing_current() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        project = project_model()
        raw = canonical_json_bytes(project)
        history = (
            root
            / "SafeProject"
            / "canonical"
            / "history"
            / "project.r00000001.json"
        )
        history.parent.mkdir(parents=True)
        history.write_bytes(raw)

        recovered = ProjectStore(root).save_current_revision(
            "SafeProject",
            project,
        )

        assert recovered.created is True
        assert ProjectStore(root).load_current(
            "SafeProject"
        ).canonical_bytes == raw


def test_conflicting_history_is_never_overwritten() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        store = ProjectStore(root)
        first = project_model()
        second = first.model_copy(update={"revision": 2})
        store.save_current_revision("SafeProject", first)
        history = (
            root
            / "SafeProject"
            / "canonical"
            / "history"
            / "project.r00000002.json"
        )
        history.write_bytes(b"private-conflict-marker")

        with pytest.raises(ProjectStorageError) as raised:
            store.save_current_revision("SafeProject", second)

        assert_code(raised, "project_history_conflict")
        assert history.read_bytes() == b"private-conflict-marker"
        assert store.load_current("SafeProject").revision == 1


def test_missing_current_is_not_reported_as_corruption() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        history = (
            root
            / "SafeProject"
            / "canonical"
            / "history"
            / "project.r00000001.json"
        )
        history.parent.mkdir(parents=True)
        history.write_bytes(canonical_json_bytes(project_model()))

        with pytest.raises(ProjectStorageError) as raised:
            ProjectStore(root).load_current("SafeProject")

        assert_code(raised, "project_not_found")


@pytest.mark.parametrize(
    "current,history,code",
    [
        (b"{", b"{", "project_json_invalid"),
        (b'{}', b'{}', "project_storage_corrupt"),
        (b"x" * (MAX_PROJECT_PAYLOAD_BYTES + 1), b"x", "project_payload_too_large"),
    ],
    ids=["malformed-json", "invalid-model", "oversize"],
)
def test_invalid_current_storage_is_classified_safely(
    current: bytes,
    history: bytes,
    code: str,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        canonical = root / "SafeProject" / "canonical"
        history_path = canonical / "history" / "project.r00000001.json"
        history_path.parent.mkdir(parents=True)
        (canonical / "current.json").write_bytes(current)
        history_path.write_bytes(history)

        with pytest.raises(ProjectStorageError) as raised:
            ProjectStore(root).load_current("SafeProject")

        assert_code(raised, code)


def test_current_requires_byte_identical_history() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        store = ProjectStore(root)
        project = project_model()
        store.save_current_revision("SafeProject", project)
        history = (
            root
            / "SafeProject"
            / "canonical"
            / "history"
            / "project.r00000001.json"
        )
        history.write_bytes(b"different")

        with pytest.raises(ProjectStorageError) as raised:
            store.load_current("SafeProject")

        assert_code(raised, "project_storage_corrupt")


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "a/b",
        r"a\b",
        "a:b",
        "CON",
        "com1.txt",
        "trailing ",
        "trailing.",
        "control\x01",
    ],
)
def test_project_name_is_lexically_bounded(name: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        with pytest.raises(ProjectStorageError) as raised:
            ProjectStore(Path(directory)).load_current(name)

    assert_code(raised, "project_name_invalid")


def test_exclusive_create_preserves_existing_file_and_cleans_temp() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        destination = root / "history.json"
        destination.write_bytes(b"old")

        with pytest.raises(FileExistsError):
            create_file_exclusively(destination, b"new")

        assert destination.read_bytes() == b"old"
        assert sorted(path.name for path in root.iterdir()) == [
            "history.json"
        ]


def test_cross_volume_or_link_failure_maps_to_safe_io_error() -> None:
    with tempfile.TemporaryDirectory() as directory:
        store = ProjectStore(Path(directory) / "projects")
        with patch(
            "agent.project_storage.create_file_exclusively",
            side_effect=OSError(errno.EXDEV, "private-cross-volume"),
        ):
            with pytest.raises(ProjectStorageError) as raised:
                store.save_current_revision(
                    "SafeProject",
                    project_model(),
                )

        assert_code(raised, "project_storage_io")
        assert "private-cross-volume" not in str(raised.value)


def test_current_publish_failure_maps_to_safe_io_error() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        store = ProjectStore(root)
        with patch(
            "agent.project_storage.write_bytes_atomically",
            side_effect=OSError(errno.EIO, "private-current-write"),
        ):
            with pytest.raises(ProjectStorageError) as raised:
                store.save_current_revision(
                    "SafeProject",
                    project_model(),
                )

        assert_code(raised, "project_storage_io")
        assert "private-current-write" not in str(raised.value)
        assert not (
            root / "SafeProject" / "canonical" / "current.json"
        ).exists()


def test_current_publish_accepts_converged_identical_destination() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        store = ProjectStore(root)

        def converge_then_fail(destination: Path, raw: bytes) -> None:
            destination.write_bytes(raw)
            raise OSError(errno.EIO, "simulated-replace-race")

        with patch(
            "agent.project_storage.write_bytes_atomically",
            side_effect=converge_then_fail,
        ):
            record = store.save_current_revision(
                "SafeProject",
                project_model(),
            )

        assert record.created is True
        assert store.load_current("SafeProject").revision == 1


def test_resolved_project_escape_is_rejected_before_write() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        projects = root / "projects"
        candidate = projects / "Linked"
        outside = root / "outside"
        projects.mkdir()
        outside.mkdir()
        original_resolve = Path.resolve

        def resolve_with_escape(
            path: Path,
            *args: object,
            **kwargs: object,
        ) -> Path:
            if path == candidate:
                return outside
            return original_resolve(path, *args, **kwargs)

        with patch.object(
            Path,
            "resolve",
            autospec=True,
            side_effect=resolve_with_escape,
        ):
            with pytest.raises(ProjectStorageError) as raised:
                ProjectStore(projects).save_current_revision(
                    "Linked",
                    project_model(),
                )

        assert_code(raised, "project_path_escape")
        assert not (outside / "canonical").exists()


def test_resolved_canonical_descendant_escape_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        projects = root / "projects"
        project_directory = projects / "SafeProject"
        escaped = project_directory / "canonical"
        outside = root / "outside"
        project_directory.mkdir(parents=True)
        outside.mkdir()
        original_resolve = Path.resolve

        def resolve_with_escape(
            path: Path,
            *args: object,
            **kwargs: object,
        ) -> Path:
            if path == escaped:
                return outside
            return original_resolve(path, *args, **kwargs)

        with patch.object(
            Path,
            "resolve",
            autospec=True,
            side_effect=resolve_with_escape,
        ):
            with pytest.raises(ProjectStorageError) as raised:
                ProjectStore(projects).save_current_revision(
                    "SafeProject",
                    project_model(),
                )

    assert_code(raised, "project_path_escape")
    assert not (outside / "history").exists()


def test_reparse_component_is_rejected_before_storage_write() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        root.mkdir()
        project_directory = root / "SafeProject"
        project_directory.mkdir()
        canonical = project_directory / "canonical"
        canonical.mkdir()
        original_lstat = os.lstat

        def lstat_with_reparse(path: Path):
            metadata = original_lstat(path)
            if Path(path) == canonical:
                return SimpleNamespace(
                    st_mode=metadata.st_mode,
                    st_file_attributes=0x0400,
                )
            return metadata

        with patch(
            "agent.project_storage.os.lstat",
            side_effect=lstat_with_reparse,
        ):
            with pytest.raises(ProjectStorageError) as raised:
                ProjectStore(root).save_current_revision(
                    "SafeProject",
                    project_model(),
                )

        assert_code(raised, "project_path_escape")
        assert not (canonical / "current.json").exists()


def test_same_revision_concurrency_is_idempotent_and_temp_free() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        store = ProjectStore(root)
        project = project_model()

        with ThreadPoolExecutor(max_workers=4) as executor:
            records = list(
                executor.map(
                    lambda _: store.save_current_revision(
                        "SafeProject",
                        project,
                    ),
                    range(8),
                )
            )

        assert {record.sha256 for record in records} == {
            records[0].sha256
        }
        assert store.load_current("SafeProject").revision == 1
        assert not list(root.rglob("*.tmp"))


def test_separate_store_instances_converge_on_same_revision() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "projects"
        project = project_model()
        stores = [ProjectStore(root), ProjectStore(root)]

        with ThreadPoolExecutor(max_workers=2) as executor:
            records = list(
                executor.map(
                    lambda store: store.save_current_revision(
                        "SafeProject",
                        project,
                    ),
                    stores,
                )
            )

        assert {record.sha256 for record in records} == {
            records[0].sha256
        }
        assert ProjectStore(root).load_current(
            "SafeProject"
        ).revision == 1
        assert not list(root.rglob("*.tmp"))
