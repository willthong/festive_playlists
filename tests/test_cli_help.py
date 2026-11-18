"""Scaffold slice: the package exists and its CLI advertises both run types."""

import subprocess
import sys


def test_help_lists_both_run_types_and_dry_run() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "festive_playlists", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "festive" in result.stdout, result.stdout
    assert "de-festive" in result.stdout, result.stdout
    assert "--dry-run" in result.stdout, result.stdout
