"""Optional extraction is independent and does not masquerade as empty content."""
import importlib
import json
from unittest.mock import patch

import pytest

URL = 'https://example.com/article'
HTML = '<html><body><nav>Menu</nav><article><p>Useful Paris evidence in 2026.</p></article></body></html>'


def extractor():
    return importlib.import_module('gsc_mcp.content_extraction')


def test_missing_optional_dependency_is_unavailable_without_fallback():
    with patch('importlib.import_module', side_effect=ImportError('missing')):
        result = extractor_module.extract_html(HTML, URL, 'trafilatura-precision')
    assert result['status'] == 'dependency_unavailable'
    assert result['text'] is None
    assert result['profile'] == 'trafilatura-precision'


def test_visible_profile_preserves_existing_text_and_empty_distinction():
    result = extractor().extract_html(HTML, URL, 'visible')
    assert result['text'] == 'Useful Paris evidence in 2026.'
    assert result['status'] == 'extracted'
    assert extractor().extract_html('<script>JS only</script>', URL, 'visible')['status'] == 'no_visible_text'
    assert extractor().extract_html('', URL, 'visible')['status'] == 'empty_input'


def test_optional_failure_and_no_main_text_are_not_zero_scores():
    content = importlib.import_module('gsc_mcp.tools.content')
    for status in ('dependency_unavailable', 'extraction_failed', 'no_main_content_returned'):
        with patch.object(content, 'safe_fetch_html', return_value=(HTML, 200)) as fetch, \
             patch('gsc_mcp.content_extraction.extract_html', return_value={'status': status, 'text': None, 'profile': 'trafilatura-precision'}):
            result = json.loads(content.content_quality(URL, extractor='trafilatura-precision'))
        assert fetch.call_count == 1
        assert result['verdict'] == 'extraction_unavailable'
        assert 'word_count' not in result and 'overall_quality' not in result


def test_invalid_profile_fails_before_fetch():
    content = importlib.import_module('gsc_mcp.tools.content')
    with patch.object(content, 'safe_fetch_html') as fetch, pytest.raises(ValueError):
        content.content_quality(URL, extractor='unknown')
    fetch.assert_not_called()


@pytest.mark.parametrize('outcome, expected', [(None, 'no_main_content_returned'), (ValueError('source-secret'), 'extraction_failed')])
def test_adapter_empty_and_failed_selection_do_not_echo_source_error(outcome, expected):
    from types import SimpleNamespace
    from configparser import ConfigParser
    from unittest.mock import Mock
    module = extractor()
    extract = Mock(return_value=outcome) if outcome is None else Mock(side_effect=outcome)
    with patch.object(module, 'version', return_value='2.3.1'), patch.object(module.importlib, 'import_module',
            return_value=SimpleNamespace(settings=SimpleNamespace(DEFAULT_CONFIG=ConfigParser()), extract=extract)):
        result = module.extract_html(HTML, URL, 'trafilatura-precision')
    assert result['status'] == expected and result['text'] is None
    assert 'source-secret' not in json.dumps(result)


def test_optional_non_success_http_cannot_get_quality_scores():
    content = importlib.import_module('gsc_mcp.tools.content')
    with patch.object(content, 'safe_fetch_html', return_value=(HTML, 503)), \
         patch('gsc_mcp.content_extraction.extract_html', return_value={'status': 'extracted', 'text': 'Error page', 'profile': 'trafilatura-precision'}):
        result = json.loads(content.content_quality(URL, extractor='trafilatura-precision'))
    assert result['extraction']['status'] == 'http_unavailable'
    assert result['verdict'] == 'extraction_unavailable' and 'overall_quality' not in result


def test_optional_settings_are_explicit_without_global_deduplication():
    from types import SimpleNamespace
    from configparser import ConfigParser
    module = extractor()
    with patch.object(module, 'version', return_value='2.3.1'), \
         patch.object(module.importlib, 'import_module', return_value=SimpleNamespace(
             settings=SimpleNamespace(DEFAULT_CONFIG=ConfigParser()), extract=lambda html, **kwargs: 'Main text')):
        result = module.extract_html(HTML, URL, 'trafilatura-precision')
    assert result['version'] == '2.3.1'
    assert result['options']['deduplicate'] is False
    assert result['options']['include_comments'] is False
    assert result['options']['include_tables'] is True
    assert result['coverage'] == 'unknown_main_content_recall'
    assert len(result['decoded_html_sha256']) == 64


def test_actual_optional_extractor_repeated_and_interleaved_calls():
    pytest.importorskip('trafilatura')
    article = '<html><body><nav>ACCOUNT MENU</nav><article><h1>A study</h1>' + ''.join(
        f'<p>Observation {i}: Paris recorded {i+10} samples in 2026. These results describe the selected site and its evidence.</p>'
        for i in range(10)) + '</article><footer>COOKIE NOTICE</footer></body></html>'
    module = extractor()
    first = module.extract_html(article, URL, 'trafilatura-precision')
    other = module.extract_html(article.replace('Paris', 'Lyon'), 'https://other.example/article', 'trafilatura-precision')
    repeated = module.extract_html(article, URL, 'trafilatura-precision')
    assert first['status'] == other['status'] == repeated['status'] == 'extracted'
    assert first['text'] == repeated['text'] and 'Lyon' in other['text']
    assert 'ACCOUNT MENU' not in first['text'] and 'COOKIE NOTICE' not in first['text']


# Loaded before ImportError patch so only the optional dependency is unavailable.
extractor_module = extractor()
