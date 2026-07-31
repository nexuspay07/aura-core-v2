import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def _alembic(database: Path, command: str, revision: str) -> None:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}"}
    result = subprocess.run([sys.executable, "-m", "alembic", command, revision], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, f"Alembic {command} failed:\n{result.stdout}\n{result.stderr}"


def upgrade(database: Path, revision: str = "head") -> None:
    _alembic(database, "upgrade", revision)


def downgrade(database: Path, revision: str) -> None:
    _alembic(database, "downgrade", revision)

def current(database: Path) -> str:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}"}
    result = subprocess.run([sys.executable, "-m", "alembic", "current"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout
