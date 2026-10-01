"""Locations of bundled files, both when run from source and from the packaged exe."""
import os
import sys


def base_dir():
    if getattr(sys, "frozen", False):  # PyInstaller one-folder build: data files are in _internal
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource(*parts):
    """Path of a bundled file. A file next to the exe (models/...) takes priority over one inside the bundle."""
    if getattr(sys, "frozen", False):
        beside_exe = os.path.join(os.path.dirname(sys.executable), *parts)
        if os.path.exists(beside_exe):
            return beside_exe
    return os.path.join(base_dir(), *parts)
