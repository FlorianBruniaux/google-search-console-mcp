from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "site.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_site_workflow_only_accepts_manual_dispatch():
    text = workflow_text()
    triggers = text.split("\non:\n", 1)[1].split("\nconcurrency:", 1)[0]
    assert triggers.strip() == "workflow_dispatch:"


@pytest.mark.parametrize("job", ["build", "deploy"])
def test_site_jobs_require_the_owner_and_manual_dispatch(job):
    text = workflow_text()
    job_header = text.split(f"\n  {job}:\n", 1)[1].split("    runs-on:", 1)[0]
    assert "github.actor_id == '3902606'" in job_header
    assert "github.event_name == 'workflow_dispatch'" in job_header


def test_site_publication_is_limited_to_main():
    text = workflow_text()
    deploy_header = text.split("\n  deploy:\n", 1)[1].split("    runs-on:", 1)[0]
    assert "github.ref == 'refs/heads/main'" in deploy_header
    assert "needs: build" in deploy_header


def test_site_workflow_has_isolated_permissions():
    text = workflow_text()
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
