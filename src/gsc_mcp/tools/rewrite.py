"""Bounded literal comparison of caller-supplied text; no semantic verdict."""
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from gsc_mcp.meta import with_meta

MAX_TEXT = 20_000
MAX_FINDINGS = 100
MAX_EXCERPT = 240
MAX_OCCURRENCES = 500
MAX_NOTES = 100

_CODE = re.compile(r'```[^\n]*\n[\s\S]*?```|~~~[^\n]*\n[\s\S]*?~~~|(`+)([^`\n]+)\1')
_QUOTES = re.compile(r'"[^"\n]+"|“[^”\n]+”|«[^»\n]+»|‘[^’\n]+’|(?<!\w)\x27[^\x27\n]+\x27(?!\w)')
_BLOCKQUOTE = re.compile(r'^>[^\n]*(?:\n>[^\n]*)*', re.M)
_CLAUSE = re.compile(r'\b(?:and|but|while|et|mais|tandis\s+que)\b|(?<!\d),(?!\d)', re.I)
_URL = re.compile(r'https?://[^\s<>"`\]\)]+')
_DATE = re.compile(r'(?<!\w)(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})(?!\w)')
_NUMBER = re.compile(
    r'(?<!\w)(?P<prefix>[$€£]\s*)?(?P<number>[+-]?\d+(?:[.,]\d+|[ \u00a0\u202f]\d{3})*)'
    r'(?:\s*(?P<unit>%|€|\$|£|EUR\b|USD\b|GBP\b|km\b|cm\b|mm\b|kg\b|mg\b|g\b|m\b|'
    r'ms\b|s\b|MB\b|GB\b|kWh\b|million\b|billion\b|percent\b|pour\s+cent\b))?', re.I,
)
_QUALIFIERS = {
    'en': {'negation': r'not|no|never|neither|without|cannot|can\x27t|won\x27t|don\x27t|doesn\x27t|isn\x27t',
           'modality': r'may|might|could|can|should|must|will|probably|possibly|likely|certainly',
           'condition': r'if|unless|provided\s+that|only\s+when',
           'absolute': r'always|everyone|all|every|guaranteed|certain|definitely'},
    'fr': {'negation': r'ne|n\x27|pas|jamais|aucun|aucune|sans|ni',
           'modality': r'peut|peuvent|pourrait|pourraient|devrait|doit|probablement|possiblement|certainement',
           'condition': r'si|sauf|à\s+condition\s+que|seulement\s+quand',
           'absolute': r'toujours|tous|toutes|chaque|garanti|garantie|certain|certaine'},
}
_STOPWORDS = set('the a an is are was were has have this that it its does do de du des le la les un une '
                 'est sont cela ce cette et and to of in on for avec avec en au aux'.split())


@dataclass
class _Literal:
    category: str
    start: int
    end: int
    value: str
    normalized: str
    passage: str = ''
    context: str = ''


def _passages(text):
    # Sentence separators deliberately avoid periods between digits (decimals/dates).
    return [(m.start(), m.end(), m.group()) for m in re.finditer(
        r'[^\n;!?]+?(?:[!?;\n]|(?<!\d)\.(?=\s|$)|(?<=\d)\.(?!\d)(?=\s|$)|$)', text
    ) if m.group().strip()]


def _words(text):
    return set(re.findall(r'[^\W_]+', text.casefold())) - _STOPWORDS


def _similarity(left, right):
    if left == right:
        return 1.0
    a, b = _words(left), _words(right)
    return len(a & b) / len(a | b) if a or b else 0.0


def _excerpt(text, center=0):
    start = max(0, min(center - MAX_EXCERPT // 2, len(text) - MAX_EXCERPT))
    return text[start:start + MAX_EXCERPT]


def _normalize_number(match, language):
    number = match['number']
    grammar = (r'[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?' if language == 'en'
               else r'[+-]?(?:\d+|\d{1,3}(?:[ \u00a0\u202f]\d{3})+)(?:,\d+)?')
    if not re.fullmatch(grammar, number):
        return match.group(), 'ambiguous numeric separators for declared language; compared literally'
    number = re.sub(r'[ \u00a0\u202f]', '', number)
    number = number.replace(',', '' if language == 'en' else '.')
    normalized = format(Decimal(number), 'f')
    if '.' in normalized:
        normalized = normalized.rstrip('0').rstrip('.')
    if Decimal(number) == 0:
        normalized = '0'
    # Unit symbols/casing and prefix position stay literal: no currency/unit conversion.
    return '|'.join((normalized, (match['prefix'] or '').strip(), match['unit'] or '')), None


def _extract(text, language, side, format):
    literals, occupied, notes = [], [], []

    def add(category, pattern):
        for match in pattern.finditer(text):
            overlaps = [(start, end) for start, end in occupied
                        if match.start() < end and match.end() > start]
            if category == 'quotation' and overlaps and all(
                    match.start() <= start and end <= match.end() for start, end in overlaps):
                # Compare the enclosing quote, suppressing duplicate child code/literals.
                literals[:] = [literal for literal in literals
                               if not (match.start() <= literal.start and literal.end <= match.end())]
                occupied[:] = [span for span in occupied if span not in overlaps]
            elif overlaps:
                continue
            start, end = match.start(), match.end()
            value, normalized, reason = match.group(), match.group(), None
            if category == 'url' and text[max(0, start - 1):start] not in ('(', '<'):
                # Bare prose URLs omit terminal punctuation; explicit Markdown targets retain it.
                value = value.rstrip('.,!?;')
                end = start + len(value)
                normalized = value
            if category == 'number_unit':
                normalized, reason = _normalize_number(match, language)
            elif category == 'date' and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                reason = 'ambiguous numeric date order/calendar validity unassessed; compared literally'
            if reason:
                notes.append({'side': side, 'start': start, 'end': end, 'reason': reason})
            literals.append(_Literal(category, start, end, value, normalized))
            occupied.append((start, end))

    add('code', _CODE)
    if format == 'markdown':
        add('quotation', _BLOCKQUOTE)
    for category, pattern in [('quotation', _QUOTES), ('url', _URL),
                              ('date', _DATE), ('number_unit', _NUMBER)]:
        add(category, pattern)
    for category, expressions in _QUALIFIERS[language].items():
        add(category, re.compile(r'(?<!\w)(?:' + expressions + r')(?!\w)', re.I))
    literals.sort(key=lambda literal: literal.start)
    truncated = len(literals) > MAX_OCCURRENCES
    literals = literals[:MAX_OCCURRENCES]
    passages = _passages(text)
    for literal in literals:
        start, _, passage = next((p for p in passages if p[0] <= literal.start < p[1]),
                                 (0, len(text), text))
        offset = literal.start - start
        literal.passage = _excerpt(passage, offset)
        # Numeric/qualifier anchors keep their own clause so a sentence's other
        # referents cannot hide swaps. Literal quotes/code retain outer context.
        clause_start, clause_end = 0, len(passage)
        if literal.category not in ('code', 'quotation', 'url'):
            for separator in _CLAUSE.finditer(passage):
                if separator.end() <= offset:
                    clause_start = separator.end()
                elif separator.start() >= offset + len(literal.value):
                    clause_end = separator.start()
                    break
        context = passage[clause_start:offset] + ' ' + passage[offset + len(literal.value):clause_end]
        context = _excerpt(context, offset - clause_start)
        literal.context = ' '.join(re.findall(r'[^\W_]+', context.casefold()))
    return literals, notes, truncated, passages


def _observation(literal):
    if literal is None:
        return None
    return {'start': literal.start, 'end': literal.end, 'literal': literal.value[:MAX_EXCERPT],
            'literal_truncated': len(literal.value) > MAX_EXCERPT, 'excerpt': literal.passage}


def _counterpart(literal, passages):
    if not passages:
        return ''
    passage = max(passages, key=lambda p: _similarity(literal.context, _excerpt(p[2])))
    return _excerpt(passage[2])


def _compare(original, revised, original_passages, revised_passages):
    findings = []

    def finding(left, right, operation, method):
        findings.append({'category': (left or right).category, 'operation': operation,
                         'original': _observation(left), 'revised': _observation(right),
                         'aligned_passages': {
                             'original': left.passage if left else _counterpart(right, original_passages),
                             'revised': right.passage if right else _counterpart(left, revised_passages)},
                         'method': method, 'context_review_required': True})

    categories = sorted({literal.category for literal in original + revised})
    for category in categories:
        left = [x for x in original if x.category == category]
        right = [x for x in revised if x.category == category]
        used_left, used_right = set(), set()
        # Exact local anchors pair occurrences before values, detecting referent swaps.
        anchors = defaultdict(deque)
        for j, literal in enumerate(right):
            anchors[literal.context].append(j)
        for i, literal in enumerate(left):
            if anchors[literal.context]:
                j = anchors[literal.context].popleft()
                used_left.add(i)
                used_right.add(j)
                if literal.normalized != right[j].normalized:
                    finding(literal, right[j], 'changed', 'exact_local_anchor')
        # ponytail: <=500 occurrences per input bounds quadratic lexical pairing;
        # upgrade via evaluated alignment corpus before increasing the ceiling.
        candidates = sorted(((_similarity(a.context, b.context), i, j)
                             for i, a in enumerate(left) if i not in used_left
                             for j, b in enumerate(right) if j not in used_right), reverse=True)
        for score, i, j in candidates:
            if i in used_left or j in used_right:
                continue
            a, b = left[i], right[j]
            if score < 0.5 and a.normalized != b.normalized:
                continue
            used_left.add(i)
            used_right.add(j)
            if a.normalized != b.normalized:
                finding(a, b, 'changed', 'lexical_local_anchor_candidate')
            elif score < 0.5:
                finding(a, b, 'context_changed', 'equal_literal_different_local_anchor_candidate')
        for i, literal in enumerate(left):
            if i not in used_left:
                finding(literal, None, 'removed', 'unmatched_occurrence')
        for j, literal in enumerate(right):
            if j not in used_right:
                finding(None, literal, 'added', 'unmatched_occurrence')
    return sorted(findings, key=lambda f: ((f['original'] or f['revised'])['start'], f['category']))


def rewrite_fidelity_check(original: str, revised: str, language: str = 'en', format: str = 'plain') -> str:
    """Compare protected literals/qualifiers in supplied text; semantics unassessed.

    language: fr/en (explicit numeric convention). format: plain/markdown (no
    renderer). Max 20,000 characters per input, 500 literal occurrences per side,
    100 findings, 240-character excerpts. No fetch, model, correction or write.
    """
    params = {'language': language if language in ('en', 'fr') else None,
              'format': format if format in ('plain', 'markdown') else None,
              'original_length': len(original) if isinstance(original, str) else None,
              'revised_length': len(revised) if isinstance(revised, str) else None}
    result = {
        'verdict': 'invalid_input', 'assessment': 'not_assessed', 'findings': None,
        'findings_truncated': False, 'analysis_truncated': False,
        'parsing_notes': [], 'parsing_notes_truncated': False,
        'semantic_assessment': {dimension: 'unassessed' for dimension in
                                ('fidelity', 'factual_truth', 'scope', 'causality')},
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'method': {'type': 'deterministic_literal_comparison', 'version': '1',
                   'language': params['language'], 'format': params['format'],
                   'alignment': '240-character local lexical anchors (numeric/qualifier conjunction clauses), '
                                'then token-overlap candidates; no semantic matching',
                   'normalization': 'Declared EN comma-grouping/dot-decimal or FR space-grouping/comma-decimal; '
                                    'Decimal value equivalence only. Bare URLs strip terminal .,!;? punctuation; '
                                    'explicit targets retain it. Other literals exact; contexts case/whitespace folded.',
                   'limits': ['Numeric dates retained literally; calendar validity/order unassessed.',
                              'Finite FR/EN qualifier and unit lists; other expressions may be missed.',
                              'Simple code/quote/URL patterns, no Markdown parser or renderer.',
                              'Context overlap can miss referent changes or flag harmless wording; human review required.']},
        'budgets': {'max_input_characters_per_side': MAX_TEXT, 'max_occurrences_per_side': MAX_OCCURRENCES,
                    'max_findings': MAX_FINDINGS, 'max_excerpt_characters': MAX_EXCERPT,
                    'max_parsing_notes': MAX_NOTES},
    }

    def output():
        return json.dumps(with_meta(result, tool='rewrite_fidelity_check', params=params), ensure_ascii=False)

    if (not isinstance(original, str) or not isinstance(revised, str)
            or not original.strip() or not revised.strip()
            or len(original) > MAX_TEXT or len(revised) > MAX_TEXT
            or language not in ('fr', 'en') or format not in ('plain', 'markdown')):
        result['error'] = 'original/revised must be nonempty strings <=20000 characters; language fr/en; format plain/markdown'
        return output()
    left, left_notes, left_truncated, left_passages = _extract(original, language, 'original', format)
    right, right_notes, right_truncated, right_passages = _extract(revised, language, 'revised', format)
    findings = _compare(left, right, left_passages, right_passages)
    notes = left_notes + right_notes
    truncated = left_truncated or right_truncated
    result.update(verdict='compared', assessment='partial_mechanical_comparison' if truncated else 'mechanical_comparison_only',
                  findings=findings[:MAX_FINDINGS], findings_truncated=len(findings) > MAX_FINDINGS,
                  analysis_truncated=truncated, parsing_notes=notes[:MAX_NOTES],
                  parsing_notes_truncated=len(notes) > MAX_NOTES,
                  counts={'original_occurrences_checked': len(left), 'revised_occurrences_checked': len(right),
                          'findings_detected': len(findings), 'findings_returned': min(len(findings), MAX_FINDINGS)})
    return output()
