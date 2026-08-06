"""Local developer linting and static analysis runner."""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent


def run_step(name: str, cmd: list[str]) -> bool:
    """Run a single linting command."""
    print(f"\n--- Running: {name} ---")
    result = subprocess.run(cmd, cwd=ROOT_DIR, check=False)
    if result.returncode != 0:
        print(f"FAILED: {name}")
        return False
    print(f"PASSED: {name}")
    return True


def main() -> None:
    steps = [
        ("Ruff Linter", [sys.executable, "-m", "ruff", "check", "src", "tests"]),
        (
            "Ruff Formatter",
            [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"],
        ),
        ("Mypy Type Checker", [sys.executable, "-m", "mypy", "src"]),
        (
            "Import Boundary Checker",
            [
                sys.executable,
                "-c",
                "from importlinter.cli import lint_imports_command; import sys; sys.exit(lint_imports_command())",
            ],
        ),
    ]

    failed = False
    for name, cmd in steps:
        if not run_step(name, cmd):
            failed = True

    if failed:
        print("\n[FAIL] One or more linting checks failed.")
        sys.exit(1)
    else:
        print("\n[OK] All linting checks passed cleanly.")


if __name__ == "__main__":
    main()
