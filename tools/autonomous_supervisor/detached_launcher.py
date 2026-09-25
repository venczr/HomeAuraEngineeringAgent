from __future__ import annotations

import subprocess
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "dev" / "autonomous"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--hours', type=float, default=0,
                        help='wall-clock hours; 0 keeps the supervisor continuous')
    parser.add_argument('--max-attempts', type=int, default=None)
    parser.add_argument('--only-task', default=None)
    parser.add_argument('--ufh', action='store_true')
    args = parser.parse_args()
    CONTROL.mkdir(parents=True, exist_ok=True)
    stdout = (CONTROL / "supervisor.stdout.log").open("ab")
    stderr = (CONTROL / "supervisor.stderr.log").open("ab")
    creationflags = (
        subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NO_WINDOW
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "tools.autonomous_supervisor.cli",
            "run",
            "--hours",
            str(args.hours),
            "--turn-timeout",
            "900",
            *((["--max-attempts", str(args.max_attempts)]) if args.max_attempts is not None else []),
            *((["--only-task", args.only_task]) if args.only_task else []),
            *((["--ufh"]) if args.ufh else []),
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=stderr,
        close_fds=True,
        creationflags=creationflags,
    )
    print(process.pid)


if __name__ == "__main__":
    main()
