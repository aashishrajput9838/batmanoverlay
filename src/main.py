"""CLI Entry Point for batmanoverlay."""

import argparse
import sys

from src.app import BatmanOverlayApp
from src.version import __version__


def main(argv: list[str] | None = None) -> int:
    """Application CLI entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="batmanoverlay",
        description="Portable Windows Productivity & Presentation Assistant",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug log output to stderr",
    )

    args = parser.parse_args(argv)

    # Initialize QApplication
    qt_args = [sys.argv[0]]
    if args.debug:
        qt_args.append("--debug")

    app = BatmanOverlayApp(qt_args)
    app.aboutToQuit.connect(app.shutdown)
    app.boot(debug=args.debug)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
