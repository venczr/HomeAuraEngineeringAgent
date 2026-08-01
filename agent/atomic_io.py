from __future__ import annotations

import os
import tempfile

from pathlib import Path


def write_bytes_atomically(
    destination: Path,
    data: bytes,
) -> None:
    """Publish exact bytes with a same-directory atomic replace."""
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary_path = Path(temporary_name)

    try:
        stream = os.fdopen(file_descriptor, "wb")
        file_descriptor = -1

        with stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        temporary_path.replace(destination)
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        temporary_path.unlink(missing_ok=True)


def write_text_atomically(
    destination: Path,
    text: str,
) -> None:
    """Publish UTF-8 text with a same-directory atomic replace."""
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary_path = Path(temporary_name)

    try:
        stream = os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
        )
        file_descriptor = -1

        with stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())

        temporary_path.replace(destination)
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        temporary_path.unlink(missing_ok=True)
