"""Freeze the Vari compute sidecar into a standalone onedir bundle with
PyInstaller. Runs on macOS, Windows, and Linux (each produces that OS's binary).

Output: packaging/dist/vari-sidecar/  (contains the executable + _internal)
electron-builder copies this into the app's resources as `sidecar-bin`.
"""
import os

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLLECT_ALL = [
    "scipy", "statsmodels", "sklearn", "pandas", "numpy", "pyreadstat",
    "matplotlib", "openpyxl", "patsy", "threadpoolctl", "joblib", "sqlalchemy",
]

args = [
    os.path.join(ROOT, "packaging", "sidecar_entry.py"),
    "--name", "vari-sidecar",
    "--onedir",
    "--noconfirm",
    "--clean",
    "--console",
    "--distpath", os.path.join(ROOT, "packaging", "dist"),
    "--workpath", os.path.join(ROOT, "packaging", "build"),
    "--specpath", os.path.join(ROOT, "packaging"),
    "--paths", ROOT,
    "--collect-submodules", "sidecar",
]
for pkg in COLLECT_ALL:
    args += ["--collect-all", pkg]

if __name__ == "__main__":
    PyInstaller.__main__.run(args)
    print("Sidecar frozen -> packaging/dist/vari-sidecar")
