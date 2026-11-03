import subprocess
import sys
from pathlib import Path


def test_cli_loads_all_models_in_a_fresh_process():
    """O deploy roda `python -m app.cli bootstrap` num processo novo: todos os modelos
    (inclusive os de imagens) precisam estar registrados, senão a preparação do banco quebra."""
    code = "import app.cli; from sqlalchemy.orm import configure_mappers; configure_mappers()"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-2000:]
