"""Consumer-visible CLI and evidence boundaries for the follow-up workflows."""
import json
from gsc_mcp.cli import main
from gsc_mcp.tools.change_impact import seo_change_impact
from gsc_mcp.tools.rewrite import rewrite_fidelity_check


def test_rewrite_cli_preserves_mechanical_finding_and_unassessed_semantics(capsys):
    assert main(['rewrite-fidelity-check', '--original', 'Price is 20 EUR.',
                 '--revised', 'Price is 30 EUR.', '--meta']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['findings'][0]['category'] == 'number_unit'
    assert data['semantic_assessment']['fidelity'] == 'unassessed'
    records = data['_meta']['evidence']['fields']
    assert records['/findings/0/category']['basis'] == 'rule'
    assert records['/semantic_assessment/fidelity']['basis'] is None


def test_change_impact_cli_keeps_future_observation_unavailable(capsys):
    event = {'site': 'sc-domain:example.com', 'url': 'https://example.com/a',
             'changed_at': '2030-01-10T12:00:00+01:00', 'timezone': 'Europe/Paris',
             'description': 'Caller changed a title'}
    assert main(['seo-change-impact', '--event', json.dumps(event),
                 '--baseline-start', '2030-01-01', '--baseline-end', '2030-01-07',
                 '--filters', json.dumps([{'dimension': 'country', 'operator': 'equals', 'expression': 'fra'}]),
                 '--page-mapping', json.dumps({'baseline_url': 'https://example.com/a', 'comparison_url': 'https://example.com/b'}),
                 '--comparison-start', '2030-01-11', '--comparison-end', '2030-01-17', '--meta']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['comparison']['status'] == 'unavailable'
    assert data['search_evidence'] is None
    assert data['page_mapping']['comparison_url'] == 'https://example.com/b'
    assert data['source_options']['filters'][0]['expression'] == 'fra'
    records = data['_meta']['evidence']['fields']
    assert records['/comparison/status']['basis'] is None
    assert records['/attribution/causal_effect']['basis'] is None


def test_draft_cli_keeps_original_input_coordinates_and_source(capsys):
    assert main(['editorial-audit', '--text', 'It is important to note that this may help.',
                 '--language', 'en', '--format', 'markdown', '--meta']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['source'] == {'origin': 'caller', 'format': 'markdown'}
    assert data['http_status'] is None
    assert data['method']['location_basis'] == 'original_source_span'
    records = data['_meta']['evidence']['fields']
    assert records['/http_status']['basis'] is None
    assert records['/method/coverage']['basis'] == 'rule'


def test_rewrite_zero_findings_cannot_become_fidelity_evidence():
    data = json.loads(rewrite_fidelity_check('Unchanged prose.', 'Unchanged prose.'))
    assert data['findings'] == []
    records = data['_meta']['evidence']['fields']
    assert records['/counts/findings_detected']['basis'] == 'derived'
    assert all(records[f'/semantic_assessment/{key}']['basis'] is None
               for key in ('fidelity', 'factual_truth', 'scope', 'causality'))


def test_change_impact_cli_rejects_nonobject_event_without_running_tool(capsys):
    assert main(['seo-change-impact', '--event', '[]',
                 '--baseline-start', '2030-01-01', '--baseline-end', '2030-01-07',
                 '--comparison-start', '2030-01-11', '--comparison-end', '2030-01-17']) == 2
    captured = capsys.readouterr()
    assert captured.out == ''
    assert '--event must be a JSON object' in captured.err


def test_change_impact_cli_rejects_malformed_event_json(capsys):
    assert main(['seo-change-impact', '--event', '{broken',
                 '--baseline-start', '2030-01-01', '--baseline-end', '2030-01-07',
                 '--comparison-start', '2030-01-11', '--comparison-end', '2030-01-17']) == 2
    captured = capsys.readouterr()
    assert captured.out == ''
    assert '--event is not valid JSON' in captured.err
