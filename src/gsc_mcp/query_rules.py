"""Experimental offline FR/EN baselines, deliberately outside the tool registry.

Release waits for #6 human taxonomy, labels, held-out evaluation and frozen
targets. Matching a lexical rule is not measured query intent or confidence.
"""
import re
import unicodedata


def _normalized(query):
    if not isinstance(query, str) or not query.strip() or len(query.encode()) > 2048:
        raise ValueError('Expected a bounded nonempty query')
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', query.casefold())
                            if unicodedata.category(c) != 'Mn').split())


def classify(query, language, brand_terms=None):
    if language not in {'fr', 'en'}: raise ValueError('Unsupported baseline language')
    value = _normalized(query)
    brands = [] if brand_terms is None else brand_terms
    if not isinstance(brands, list) or len(brands) > 100: raise ValueError('Invalid brand terms')
    question = bool(re.match(r'^(comment|pourquoi|quand|ou|quel|quelle|quels|quelles|qui|what|why|how|when|where|which|who)\b', value) or value.endswith('?'))
    transactional = bool(re.search(r'\b(acheter|commander|buy|purchase|order)\b', value))
    commercial = bool(re.search(r'\b(choisir|comparatif|comparaison|meilleur|meilleure|avis|best|review|reviews|compare|comparison)\b', value))
    brand = any(re.search(r'(?<!\w)' + re.escape(_normalized(term)) + r'(?!\w)', value) for term in brands)
    if re.search(r'\b(pas|sans|non|not|without|never)\b', value): label, reason = 'unclassified', 'negation_requires_review'
    elif sum((transactional, commercial, brand)) > 1: label, reason = 'unclassified', 'mixed_lexical_signals'
    elif transactional: label, reason = 'transactional', 'transaction_modifier'
    elif commercial: label, reason = 'commercial', 'comparison_modifier'
    elif brand: label, reason = 'navigational', 'caller_brand_term'
    elif question: label, reason = 'informational', 'question_only_candidate'
    else: label, reason = 'unclassified', 'no_supported_rule'
    return {'query': query, 'language': language, 'label': label, 'question_form': question,
            'reason': reason, 'basis': 'rule', 'profile': 'experimental-fr-en-v1',
            'release_status': 'human_evaluation_required'}


def near_query_candidates(queries):
    if not isinstance(queries, list) or len(queries) > 500: raise ValueError('Query count exceeds prototype budget')
    groups = {}
    for query in queries:
        group = groups.setdefault(_normalized(query), [])
        if query not in group: group.append(query)
    return [{'variants': values, 'reason': 'case_whitespace_accent_candidate', 'same_intent': None}
            for values in groups.values() if len(values) > 1]
