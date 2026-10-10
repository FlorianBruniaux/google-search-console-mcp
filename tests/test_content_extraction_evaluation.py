"""Synthetic runner checks only, not expert extraction-quality evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'eval_content_extraction.py'
HTML = '<html><body><div>Fixture navigation</div><main><p>Main fixture text.</p><p>Second fixture paragraph.</p></main><script>Hidden fixture text.</script></body></html>'


def dataset(tmp_path):
    raw = HTML.encode('utf-8')
    (tmp_path / 'fixture.html').write_bytes(raw)
    return {'schema_version': 1, 'corpus_id': 'synthetic-runner-smoke', 'provenance': 'synthetic',
            'protocol': {'frozen_before_tuning': True, 'inclusion_criteria': 'fixture paragraphs',
                         'omission_criteria': 'fixture navigation', 'resource_criteria': 'record observations only'},
            'cases': [{'id': 'fixture', 'split': 'held_out', 'task_family': 'fixture-task',
                       'site_family': 'fixture-site', 'page_family': 'fixture-page', 'language': 'en',
                       'page_type': 'article', 'source_url': 'https://fixture.example/article',
                       'html_path': 'fixture.html', 'html_sha256': hashlib.sha256(raw).hexdigest(),
                       'annotation': {'annotator': 'synthetic-author', 'reviewer': 'synthetic-reviewer',
                                      'source_authorization': 'authored synthetic fixture',
                                      'independent_of_extractors': True},
                       'include': ['Main fixture text.', 'Second fixture paragraph.', 'Hidden fixture text.'],
                       'omit': [{'text': 'Fixture navigation', 'kind': 'template'}]}]}


def run_cli(tmp_path, data=None, *extra):
    data = dataset(tmp_path) if data is None else data
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(data), encoding='utf-8')
    return subprocess.run([sys.executable, '-I', str(SCRIPT), '--dataset', str(manifest), *extra],
                          capture_output=True, text=True, check=False)


def test_actual_visible_metrics_partial_content_provenance_and_resources(tmp_path):
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    row = report['cases'][0]
    visible = row['profiles']['visible']
    assert visible['metrics']['included_hits'] == [True, True, False]
    assert visible['metrics']['inclusion_recall'] == pytest.approx(2 / 3)
    assert visible['metrics']['omission_leakage'] == 1
    assert visible['metrics']['omission_by_kind']['template'] == {'hits': 1, 'total': 1}
    assert visible['annotation_coverage'] == 'partial'
    assert row['html_sha256'] == hashlib.sha256(HTML.encode()).hexdigest()
    assert row['resolved_html_path'] == str(tmp_path / 'fixture.html')
    assert visible['wall_seconds'] >= 0
    assert visible['python_allocation_peak_bytes'] > 0
    assert 'text' not in visible['extraction']
    assert report['release_quality'] == 'UNKNOWN'
    assert report['synthetic_release_eligible'] is False
    assert report['coverage'] == {'language': {'en': 1}, 'page_type': {'article': 1}}
    assert report['downstream_warnings'] == 'not_measured'


@pytest.mark.parametrize('change', [
    lambda d: d['cases'][0].update(html_sha256='0' * 64),
    lambda d: d['cases'][0].update(html_path='../outside.html'),
    lambda d: d['cases'][0]['include'].append(' MAIN fixture text. '),
    lambda d: d['cases'][0]['omit'].append({'text': 'Main fixture text.', 'kind': 'comment'}),
    lambda d: d['cases'][0]['include'].append('No matching source text'),
    lambda d: d['cases'][0]['annotation'].update(reviewer='synthetic-author'),
    lambda d: d['cases'][0]['annotation'].update(independent_of_extractors=False),
    lambda d: d['protocol'].update(frozen_before_tuning=False),
    lambda d: d.update(cases=[]),
    lambda d: d['cases'][0].update(language='de'),
])
def test_reject_invalid_or_ambiguous_corpus_before_comparison(tmp_path, change):
    data = dataset(tmp_path)
    change(data)
    result = run_cli(tmp_path, data)
    assert result.returncode == 2
    assert not result.stdout
    assert 'Invalid evaluation input' in result.stderr


@pytest.mark.parametrize('family', ['task_family', 'site_family', 'page_family'])
def test_reject_families_crossing_splits(tmp_path, family):
    data = dataset(tmp_path)
    second = copy.deepcopy(data['cases'][0])
    second.update(id='second', split='tuning', html_path='second.html')
    for key in ('task_family', 'site_family', 'page_family'):
        if key != family:
            second[key] = 'second-' + key
    raw = HTML.replace('fixture', 'second').encode()
    (tmp_path / 'second.html').write_bytes(raw)
    second['html_sha256'] = hashlib.sha256(raw).hexdigest()
    second['include'] = ['Main second text.']
    second['omit'] = []
    data['cases'].append(second)
    result = run_cli(tmp_path, data)
    assert result.returncode == 2
    assert 'Family crosses splits' in result.stderr


def test_reject_duplicate_html_and_symlink_escape(tmp_path):
    data = dataset(tmp_path)
    duplicate = copy.deepcopy(data['cases'][0]); duplicate['id'] = 'duplicate'
    data['cases'].append(duplicate)
    result = run_cli(tmp_path, data)
    assert result.returncode == 2
    assert 'Duplicate HTML source' in result.stderr
    data['cases'].pop()
    external = tmp_path.parent / (tmp_path.name + '-outside.html')
    external.write_text(HTML, encoding='utf-8')
    (tmp_path / 'escape.html').symlink_to(external)
    data['cases'][0]['html_path'] = 'escape.html'
    assert run_cli(tmp_path, data).returncode == 2


def test_reject_oversized_html_duplicate_json_and_empty_split(tmp_path):
    data = dataset(tmp_path)
    (tmp_path / 'fixture.html').write_bytes(b' ' * (2_097_152 + 1))
    assert run_cli(tmp_path, data).returncode == 2
    dataset(tmp_path)
    assert run_cli(tmp_path, data, '--split', 'tuning').returncode == 2
    manifest = tmp_path / 'duplicate.json'
    manifest.write_text('{"schema_version": 1, "schema_version": 1}', encoding='utf-8')
    result = subprocess.run([sys.executable, '-I', str(SCRIPT), '--dataset', str(manifest)],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert 'Duplicate JSON key' in result.stderr


def test_unavailable_and_empty_results_do_not_become_zero_scores(tmp_path, monkeypatch):
    assert SCRIPT.is_file(), 'Evaluation runner not implemented'
    spec = importlib.util.spec_from_file_location('extraction_eval', SCRIPT)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    import gsc_mcp.content_extraction as extraction
    for status in ('dependency_unavailable', 'extraction_failed', 'no_main_content_returned', 'no_visible_text'):
        monkeypatch.setattr(extraction, 'extract_html', lambda *a, **k: {'status': status, 'text': None})
        row = module.measure('fixture', 'https://fixture.example/', 'visible', ['fixture'], [])
        assert row['extraction']['status'] == status
        assert row['metrics'] is None
        assert row['annotation_coverage'] == 'unavailable'


def test_no_inclusion_or_omission_labels_yields_null_not_perfect_score(tmp_path):
    data = dataset(tmp_path)
    data['cases'][0]['include'] = []
    data['cases'][0]['omit'] = []
    result = run_cli(tmp_path, data)
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)['cases'][0]['profiles']['visible']
    assert row['metrics']['inclusion_recall'] is None
    assert row['metrics']['omission_leakage'] is None
    assert row['annotation_coverage'] == 'no_inclusion_labels'
