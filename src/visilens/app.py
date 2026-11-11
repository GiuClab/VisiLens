"""Compatibility entry point for the VisiLens desktop application."""

from .desktop import MainWindow, main

__all__ = ["MainWindow", "main"]


if __name__ == "__main__":
    main()
