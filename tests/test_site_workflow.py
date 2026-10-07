from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "site.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_site_workflow_has_isolated_triggers_and_permissions():
    text = workflow_text()
    assert 'branches: ["main"]' in text
    for path in ("site/**", "pyproject.toml", "src/gsc_mcp/**", ".github/workflows/site.yml"):
        assert path in text
    assert "pages: write" in text
    assert "id-token: write" in text
    assert "pypi" not in text.lower()


def test_site_workflow_verifies_before_uploading():
    text = workflow_text()
    assert text.index("pytest tests/test_site_product_data.py") < text.index("pnpm verify")
    assert text.index("pnpm verify") < text.index("actions/upload-pages-artifact")
    assert "site/dist/deployment.json" in text
    assert "site/dist/" in text


def test_site_workflow_uses_locked_toolchains():
    text = workflow_text()
    assert 'python-version: "3.11"' in text
    assert 'node-version: "22"' in text
    assert "version: 9" in text
    assert "pnpm install --frozen-lockfile" in text
    assert "playwright install --with-deps chromium" in text
