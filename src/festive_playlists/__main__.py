"""CLI entry point for festive_playlists."""

import argparse
import logging
import os
from datetime import date

from festive_playlists.auth import get_client
from festive_playlists.defestive import run as run_defestive
from festive_playlists.festive import run as run_festive


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="festive_playlists",
        description="Automate a Spotify Christmas routine.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "festive",
        help="Back up Liked Songs and like the Christmas playlist.",
    )
    subparsers.add_parser(
        "de-festive",
        help="Unlike tracks in the Christmas playlist.",
    )
    return parser


def main() -> None:
    """Run the festive_playlists CLI."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = _build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    sp = get_client(os.environ)
    if args.command == "festive":
        plan = run_festive(sp, date.today(), dry_run=args.dry_run)
        print(f"backup: {plan.backup_name}")
        print(f"tracks to like: {len(plan.track_ids)}")
        for track_id in plan.track_ids:
            print(track_id)
    else:
        plan = run_defestive(sp, dry_run=args.dry_run)
        print(f"tracks to unlike: {len(plan.track_ids)}")
        for track_id in plan.track_ids:
            print(track_id)
        if plan.pre_existing_like_ids:
            print(f"pre-existing likes: {len(plan.pre_existing_like_ids)}")
            for track_id in plan.pre_existing_like_ids:
                print(track_id)


if __name__ == "__main__":
    main()
