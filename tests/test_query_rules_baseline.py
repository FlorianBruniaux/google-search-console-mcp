"""Offline rule prototype, without an MCP callable or a release-accuracy claim."""
import importlib

import pytest


def rules():
    assert importlib.util.find_spec('gsc_mcp.query_rules'), 'query prototype not implemented'
    return importlib.import_module('gsc_mcp.query_rules')


@pytest.mark.parametrize('query,language,label,question', [
    ('comment choisir un vélo ?', 'fr', 'commercial', True),
    ('buy running shoes', 'en', 'transactional', False),
    ('how does photosynthesis work', 'en', 'informational', True),
    ('chaussure', 'fr', 'unclassified', False),
    ('ne pas acheter une voiture', 'fr', 'unclassified', False),
    ('do not buy this', 'en', 'unclassified', False),
])
def test_explicit_rule_priority_question_form_and_abstention(query, language, label, question):
    result = rules().classify(query, language)
    assert result['label'] == label
    assert result['question_form'] == question
    assert result['basis'] == 'rule'
    assert 'confidence' not in result
    assert result['query'] == query


def test_brand_matching_is_explicit_and_does_not_match_substrings():
    api = rules()
    assert api.classify('twaino login', 'en', ['twaino'])['label'] == 'navigational'
    assert api.classify('twainologist', 'en', ['twaino'])['label'] == 'unclassified'


def test_candidate_normalization_preserves_direction_and_negation():
    api = rules()
    result = api.near_query_candidates(['référencement SEO', 'referencement seo', 'Paris Londres', 'Londres Paris', 'acheter vélo', 'ne pas acheter vélo'])
    assert result == [{'variants': ['référencement SEO', 'referencement seo'],
                       'reason': 'case_whitespace_accent_candidate', 'same_intent': None}]


def test_prototype_is_not_registered_as_a_public_tool():
    from gsc_mcp.registry import TOOLS
    api = rules()
    assert not any(fn is api.classify or fn is api.near_query_candidates for fn in TOOLS.values())
    with pytest.raises(ValueError): api.classify('bonjour', 'de')
