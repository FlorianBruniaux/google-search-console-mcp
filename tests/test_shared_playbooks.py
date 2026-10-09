"""Repository discovery and declared calls, not model behavior or SEO accuracy."""
import inspect
import json
from pathlib import Path
import re

import pytest

from gsc_mcp.registry import TOOLS

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / '.agents/skills').iterdir())


@pytest.mark.parametrize('skill', SKILLS, ids=lambda p: p.name)
def test_both_hosts_resolve_the_same_source_and_resources(skill):
    source = skill / 'SKILL.md'
    assert (ROOT / '.claude/skills' / skill.name / 'SKILL.md').resolve() == source.resolve()
    text = source.read_text()
    assert text.startswith('---\n') and f'name: {skill.name}\n' in text
    assert 'Done when' in text
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
            continue
        resource = (skill / target.split('#')[0]).resolve()
        assert resource.is_relative_to(ROOT) and resource.is_file(), target
    scenarios = json.loads((skill / 'evals/scenarios.json').read_text())
    assert scenarios['target'] == skill.name
    assert len(scenarios['positive']) >= 8 and len(scenarios['negative']) >= 2
    corpus = ROOT / '.claude/routing-corpus' / skill.name / 'scenarios.json'
    # The existing indexing/sitemap projection may link the complete directory.
    assert corpus.resolve() == (skill / 'evals/scenarios.json').resolve()


@pytest.mark.parametrize('skill', SKILLS, ids=lambda p: p.name)
def test_declared_workflow_arguments_exist_and_include_required_inputs(skill):
    contract = json.loads((skill / 'evals/calls.json').read_text())
    text = (skill / 'SKILL.md').read_text()
    assert contract['calls']
    for name, arguments in contract['calls'].items():
        assert name in TOOLS and name in text
        inspect.signature(TOOLS[name]).bind(**dict.fromkeys(arguments, object()))
    # A bare registered tool in inline code must be included in the inventory.
    for name in re.findall(r'`([a-z][a-z_]+)`', text):
        if name in TOOLS:
            assert name in contract['calls'], name


def test_reviewed_boundaries_for_penalty_ai_loss_and_consolidation():
    weekly = (ROOT / '.agents/skills/seo-weekly-report/SKILL.md').read_text()
    ai = (ROOT / '.agents/skills/ai-overviews-impact/SKILL.md').read_text()
    overlap = (ROOT / '.agents/skills/cannibalization-check/SKILL.md').read_text()
    assert 'not manual actions or security notices' in weekly
    assert 'unavailable and unverified' in ai
    assert 'intent UNKNOWN' in overlap and '90-day' in overlap
    assert 'Do not execute any write or destructive action' in overlap


@pytest.mark.parametrize('role,skill', [
    ('gsc-content-optimizer', 'content-opportunities'),
    ('gsc-schema-auditor', 'schema-audit'),
    ('gsc-page-analyst', 'page-deep-dive'),
    ('gsc-seo-reporter', 'seo-weekly-report'),
    ('gsc-sitemap-auditor', 'sitemap-audit'),
    ('gsc-indexing-auditor', 'indexing-audit'),
    ('gsc-traffic-doctor', 'traffic-drop-diagnosis'),
    ('gsc-cannibalization-checker', 'cannibalization-check'),
    ('gsc-ai-overviews-analyst', 'ai-overviews-impact'),
])
def test_role_allowlist_covers_its_reviewed_skill_calls(role, skill):
    text = (ROOT / '.claude/agents' / f'{role}.md').read_text()
    frontmatter = text.split('---', 2)[1]
    calls = json.loads((ROOT / '.agents/skills' / skill / 'evals/calls.json').read_text())['calls']
    for name in calls:
        assert f'mcp__gsc-mcp__{name}\n' in frontmatter, (role, name)
