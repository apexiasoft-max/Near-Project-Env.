# PyInstaller development specification for the Sprint 1 Windows shell.

from pathlib import Path

project_root = Path(SPECPATH).parent

a = Analysis(
    [str(project_root / "src" / "npe" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (
            str(project_root / "spikes" / "sprint0" / "scripts" / "normalize_model_fbx.py"),
            "tools",
        ),
    ],
    hiddenimports=[
        "npe.api.app",
        "npe.worker.runner",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
    ],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="NearProjectEnvironment",
    console=True,
)
