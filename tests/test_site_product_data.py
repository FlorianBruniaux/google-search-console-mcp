import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from gsc_mcp.registry import TOOLS


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "site" / "scripts" / "export-product-data.py"


def run_export(pyproject: Path, source_root: Path, output: Path):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pyproject",
            str(pyproject),
            "--source-root",
            str(source_root),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def write_fake_source(root: Path, registry_value: str) -> Path:
    package = root / "gsc_mcp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "registry.py").write_text(
        f"TOOLS = {registry_value}\n",
        encoding="utf-8",
    )
    return root


def write_pyproject(path: Path, *, include_repository: bool = True) -> Path:
    repository = (
        '\n[project.urls]\nRepository = "https://github.com/example/project"\n'
        if include_repository
        else ""
    )
    path.write_text(
        '[project]\nname = "gsc-mcp-tools"\nversion = "1.2.0"\n'
        'requires-python = ">=3.11"\n'
        + repository,
        encoding="utf-8",
    )
    return path


def test_export_matches_repository_sources(tmp_path):
    output = tmp_path / "product.json"
    result = run_export(REPO_ROOT / "pyproject.toml", REPO_ROOT / "src", output)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    project = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    assert payload == {
        "package": project["name"],
        "pythonRequires": project["requires-python"],
        "repository": project["urls"]["Repository"],
        "toolCount": len(TOOLS),
        "version": project["version"],
    }


def test_export_is_byte_deterministic(tmp_path):
    output = tmp_path / "product.json"
    first = run_export(REPO_ROOT / "pyproject.toml", REPO_ROOT / "src", output)
    first_bytes = output.read_bytes()
    second = run_export(REPO_ROOT / "pyproject.toml", REPO_ROOT / "src", output)

    assert first.returncode == second.returncode == 0
    assert output.read_bytes() == first_bytes


@pytest.mark.parametrize("registry_value", ["{}", "[]"])
def test_export_refuses_invalid_registry(tmp_path, registry_value):
    pyproject = write_pyproject(tmp_path / "pyproject.toml")
    source_root = write_fake_source(tmp_path / "src", registry_value)
    output = tmp_path / "product.json"

    result = run_export(pyproject, source_root, output)

    assert result.returncode != 0
    assert "TOOLS must be a non-empty dictionary" in result.stderr
    assert not output.exists()


def test_export_refuses_missing_repository_without_partial_file(tmp_path):
    pyproject = write_pyproject(tmp_path / "pyproject.toml", include_repository=False)
    source_root = write_fake_source(tmp_path / "src", '{"example": object()}')
    output = tmp_path / "product.json"

    result = run_export(pyproject, source_root, output)

    assert result.returncode != 0
    assert "project.urls.Repository" in result.stderr
    assert not output.exists()


def test_export_refuses_malformed_pyproject_without_partial_file(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project\nname = broken", encoding="utf-8")
    source_root = write_fake_source(tmp_path / "src", '{"example": object()}')
    output = tmp_path / "product.json"

    result = run_export(pyproject, source_root, output)

    assert result.returncode != 0
    assert "product data export failed" in result.stderr
    assert not output.exists()
