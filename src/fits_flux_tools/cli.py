"""Top-level CLI for package metadata and command discovery."""

from __future__ import annotations

import argparse

from . import __author__, __author_email__, __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fits-flux-tools",
        description="Top-level CLI for fits-flux-tools.",
        epilog=(
            f"Version: {__version__}\n"
            f"Author: {__author__}\n"
            f"Author email: {__author_email__}\n\n"
            "Installed commands:\n"
            "  polymask\n"
            "  cal-int-flux-density"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main() -> None:
    parser = build_parser()
    parser.parse_args()
