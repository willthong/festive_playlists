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


def test_dry_run_is_accepted_after_subcommand() -> None:
    from festive_playlists.__main__ import _build_parser

    args = _build_parser().parse_args(["festive", "--dry-run"])
    assert args.dry_run is True
    assert args.command == "festive"
