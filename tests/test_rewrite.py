"""Behavior boundaries for caller-supplied rewrite comparisons."""
import importlib
import importlib.util
import json

import pytest


def check(original, revised, **params):
    # Missing callable is an assertion failure during the first red run.
    assert importlib.util.find_spec('gsc_mcp.tools.rewrite'), 'rewrite comparison missing'
    module = importlib.import_module('gsc_mcp.tools.rewrite')
    return json.loads(module.rewrite_fidelity_check(original, revised, **params))


def test_zero_mechanical_changes_never_certifies_semantic_fidelity():
    result = check('Revenue is 20 EUR.', 'Revenue is 20 EUR.')
    assert result['findings'] == []
    assert result['assessment'] == 'mechanical_comparison_only'
    assert result['semantic_assessment'] == {
        'fidelity': 'unassessed', 'factual_truth': 'unassessed',
        'scope': 'unassessed', 'causality': 'unassessed',
    }
    assert 'faithful' not in result and 'factual_true' not in result


@pytest.mark.parametrize('original,revised,category', [
    ('Revenue is 20 EUR.', 'Revenue is 30 EUR.', 'number_unit'),
    ('Length is 20 cm.', 'Length is 20 km.', 'number_unit'),
    ('Launch: 2026-10-08.', 'Launch: 2026-10-09.', 'date'),
    ('[Report](https://a.example/x)', '[Report](https://a.example/y)', 'url'),
    ('Use `count = 20`.', 'Use `count = 30`.', 'code'),
    ('She said "20 percent".', 'She said "30 percent".', 'quotation'),
])
def test_changed_protected_literal_retains_pair_and_source_spans(original, revised, category):
    result = check(original, revised, format='markdown')
    finding = next(f for f in result['findings'] if f['category'] == category)
    assert finding['operation'] == 'changed'
    assert finding['context_review_required'] is True
    for side, source in [('original', original), ('revised', revised)]:
        observation = finding[side]
        assert source[observation['start']:observation['end']] == observation['literal']
        assert observation['excerpt']


def test_reordering_passages_does_not_invent_numeric_changes():
    result = check('Alpha costs 20 EUR. Beta costs 30 EUR.',
                   'Beta costs 30 EUR. Alpha costs 20 EUR.')
    assert result['findings'] == []


def test_same_values_swapped_between_referents_are_review_candidates():
    result = check('Alpha costs 20 EUR. Beta costs 30 EUR.',
                   'Alpha costs 30 EUR. Beta costs 20 EUR.')
    findings = [f for f in result['findings'] if f['category'] == 'number_unit']
    assert len(findings) == 2
    assert all(f['context_review_required'] for f in findings)
    assert {f['original']['literal'] for f in findings} == {'20 EUR', '30 EUR'}


def test_repeated_number_occurrence_removed_is_not_hidden_by_set_comparison():
    result = check('Alpha has 20 users. Beta has 20 users.', 'Alpha has 20 users.')
    removed = next(f for f in result['findings'] if f['operation'] == 'removed')
    assert 'Beta' in removed['original']['excerpt']


@pytest.mark.parametrize('original,revised,category', [
    ('This does not improve results.', 'This improves results.', 'negation'),
    ('This may improve results.', 'This improves results.', 'modality'),
    ('Results improve if tested.', 'Results improve.', 'condition'),
    ('Results improve.', 'Results always improve.', 'absolute'),
    ('Cela ne fonctionne pas.', 'Cela fonctionne.', 'negation'),
    ('Cela peut aider.', 'Cela aide.', 'modality'),
])
def test_qualifier_changes_are_contextual_candidates(original, revised, category):
    result = check(original, revised, language='fr' if original.startswith('Cela') else 'en')
    finding = next(f for f in result['findings'] if f['category'] == category)
    assert finding['context_review_required'] is True
    assert finding['aligned_passages']['original']
    assert finding['aligned_passages']['revised']


def test_qualifier_relocation_is_not_hidden_by_equal_tokens():
    result = check('Alpha may improve. Beta improves.', 'Alpha improves. Beta may improve.')
    assert any(f['category'] == 'modality' and f['operation'] == 'context_changed'
               for f in result['findings'])


@pytest.mark.parametrize('language,original,revised', [
    ('en', 'Revenue is 1,200.50 EUR.', 'Revenue is 1200.5 EUR.'),
    ('fr', 'Recette de 1\u202f200,50 EUR.', 'Recette de 1200,5 EUR.'),
])
def test_declared_decimal_format_equivalents_are_disclosed(language, original, revised):
    result = check(original, revised, language=language)
    assert result['findings'] == []
    assert result['method']['normalization']


def test_ambiguous_date_is_literal_and_requires_review():
    result = check('Launch: 03/04/2026.', 'Launch: 04/03/2026.')
    assert result['findings'][0]['category'] == 'date'
    assert result['parsing_notes']
    assert any('ambiguous' in note['reason'] for note in result['parsing_notes'])


def test_ambiguous_decimal_is_not_silently_normalized():
    result = check('Rate is 1,5 EUR.', 'Rate is 1.5 EUR.', language='en')
    assert result['findings']
    assert any('ambiguous' in note['reason'] for note in result['parsing_notes'])


def test_protected_code_and_quotes_do_not_emit_duplicate_qualifier_findings():
    result = check('`not always 20` and "may 30".', '`always 21` and "must 31".')
    assert {f['category'] for f in result['findings']} == {'code', 'quotation'}


@pytest.mark.parametrize('params', [
    {'original': '', 'revised': 'text'},
    {'original': 'text', 'revised': '  '},
    {'original': 'a' * 20001, 'revised': 'text'},
    {'original': 'text', 'revised': 'text', 'format': 'html'},
    {'original': 'text', 'revised': 'text', 'language': 'auto'},
    {'original': 1, 'revised': 'text'},
])
def test_invalid_input_is_explicit_and_not_assessed(params):
    result = check(**params)
    assert result['verdict'] == 'invalid_input'
    assert result['assessment'] == 'not_assessed'
    assert result['findings'] is None


def test_returned_findings_excerpts_and_meta_do_not_echo_unbounded_inputs():
    original = '\n'.join(f'Item {i} costs 20 EUR.' for i in range(130))
    revised = '\n'.join(f'Item {i} costs 30 EUR.' for i in range(130))
    result = check(original, revised)
    assert len(result['findings']) == 100
    assert result['findings_truncated'] is True
    for finding in result['findings']:
        for side in ('original', 'revised'):
            assert len(finding[side]['literal']) <= 240
            assert len(finding['aligned_passages'][side]) <= 240
    assert 'original' not in result['_meta']['params']
    assert 'revised' not in result['_meta']['params']


def test_identical_maximum_input_is_accepted_and_semantics_remain_unassessed():
    result = check('x' * 20000, 'x' * 20000)
    assert result['findings'] == []
    assert result['semantic_assessment']['fidelity'] == 'unassessed'


def test_reordering_numeric_clauses_within_one_sentence_preserves_literals():
    result = check('Alpha costs 20 EUR and Beta costs 30 EUR.',
                   'Beta costs 30 EUR and Alpha costs 20 EUR.')
    assert result['findings'] == []


def test_markdown_block_quotation_is_protected_as_one_literal():
    result = check('> They may not win 20 games.', '> They will win 30 games.', format='markdown')
    assert [f['category'] for f in result['findings']] == ['quotation']


def test_sentence_punctuation_outside_bare_url_is_not_target_change():
    result = check('Visit https://example.test/report.', 'Visit https://example.test/report!')
    assert result['findings'] == []


def test_invalid_language_and_format_do_not_expand_output_budget():
    result = check('text', 'text', language='x' * 50000, format='x' * 50000)
    assert result['verdict'] == 'invalid_input'
    assert len(json.dumps(result)) < 10000


def test_literal_budget_discloses_partial_comparison():
    result = check('\n'.join(f'Value {i}.' for i in range(501)),
                   '\n'.join(f'Value {i}.' for i in range(501)))
    assert result['analysis_truncated'] is True
    assert result['assessment'] == 'partial_mechanical_comparison'
    assert result['counts']['original_occurrences_checked'] == 500


def test_long_code_literal_and_parsing_notes_have_disclosed_truncation():
    result = check('`' + 'a' * 500 + '`', '`' + 'b' * 500 + '`')
    assert len(result['findings'][0]['original']['literal']) == 240
    assert result['findings'][0]['original']['literal_truncated'] is True
    result = check('\n'.join('Launch 03/04/2026.' for _ in range(60)),
                   '\n'.join('Launch 03/04/2026.' for _ in range(60)))
    assert len(result['parsing_notes']) == 100
    assert result['parsing_notes_truncated'] is True


def test_absent_protected_literal_does_not_hide_unassessed_meaning_change():
    result = check('Treatment preceded recovery.', 'Treatment caused recovery.')
    assert result['findings'] == []
    assert result['semantic_assessment']['causality'] == 'unassessed'


def test_markdown_quotation_keeps_caret_inside_protected_literal():
    result = check('> x^2 may be 20.', '> x^2 must be 30.', format='markdown')
    assert [f['category'] for f in result['findings']] == ['quotation']


def test_explicit_link_target_keeps_terminal_punctuation_as_literal():
    result = check('[Report](https://example.test/report.)',
                   '[Report](https://example.test/report!)', format='markdown')
    assert result['findings'][0]['category'] == 'url'
    assert result['findings'][0]['original']['literal'].endswith('.')


def test_fenced_multiline_code_is_a_single_protected_literal():
    result = check('```python\nnot_allowed = 20\n```',
                   '```python\nallowed = 30\n```', format='markdown')
    assert [f['category'] for f in result['findings']] == ['code']


def test_large_integer_change_is_not_rounded_away_by_decimal_context():
    result = check('Value 1234567890123456789012345678901.',
                   'Value 1234567890123456789012345678902.')
    assert len(result['findings']) == 1
    assert result['findings'][0]['operation'] == 'changed'


def test_long_passage_alignment_only_compares_bounded_local_windows(monkeypatch):
    module = importlib.import_module('gsc_mcp.tools.rewrite')
    similarity = module._similarity

    def bounded_similarity(left, right):
        assert len(left) <= 240 and len(right) <= 240
        return similarity(left, right)

    monkeypatch.setattr(module, '_similarity', bounded_similarity)
    result = check('Alpha ' + 'context ' * 1000 + '20 EUR.',
                   'Beta ' + 'context ' * 1000 + '30 EUR.')
    assert result['findings']


def test_same_sentence_numeric_referent_swap_is_not_hidden_by_token_sets():
    result = check('Alpha costs 20 EUR and Beta costs 30 EUR.',
                   'Alpha costs 30 EUR and Beta costs 20 EUR.')
    assert len(result['findings']) == 2
    assert {f['operation'] for f in result['findings']} == {'changed'}
    assert {f['original']['literal'] for f in result['findings']} == {'20 EUR', '30 EUR'}
    assert all(f['context_review_required'] for f in result['findings'])


@pytest.mark.parametrize('original,revised,format', [
    ('She said "run `task` today".', 'She said "run `task` tomorrow".', 'plain'),
    ('> Run `task` today.', '> Run `task` tomorrow.', 'markdown'),
])
def test_outer_quotation_with_inline_code_remains_a_compared_literal(original, revised, format):
    result = check(original, revised, format=format)
    assert [f['category'] for f in result['findings']] == ['quotation']
    assert result['findings'][0]['operation'] == 'changed'
    assert 'today' in result['findings'][0]['original']['literal']
    assert 'tomorrow' in result['findings'][0]['revised']['literal']


def test_identical_outer_quotation_with_code_does_not_warn():
    text = 'She said "run `task` today".'
    assert check(text, text)['findings'] == []


def test_quotation_inside_fenced_code_keeps_code_protection():
    result = check('```python\nmessage = "today"\n```',
                   '```python\nmessage = "tomorrow"\n```', format='markdown')
    assert [f['category'] for f in result['findings']] == ['code']


def test_french_numeric_clause_reordering_and_referent_swap_are_distinct():
    original = 'Alpha coûte 20 EUR et Beta coûte 30 EUR.'
    assert check(original, 'Beta coûte 30 EUR et Alpha coûte 20 EUR.', language='fr')['findings'] == []
    swapped = check(original, 'Alpha coûte 30 EUR et Beta coûte 20 EUR.', language='fr')
    assert len(swapped['findings']) == 2
    assert all(f['operation'] == 'changed' for f in swapped['findings'])
