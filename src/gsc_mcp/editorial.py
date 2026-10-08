"""Portable editorial conventions, not an AI-authorship or SEO classifier.

Version 1 intentionally implements only narrow motifs from the reviewed
ANTI_AI conventions. Contextual findings require a semantic review.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

PROFILE_ID = 'anti-ai-editorial'
PROFILE_VERSION = 1
MAX_FINDINGS = 50
MAX_EXCERPT = 240
REWRITE_GUIDANCE = [
    'Preserve facts, numbers, dates, sources and the original referent and scope.',
    'Preserve modality, uncertainty, causality, conditions, limitations and exceptions.',
    'Review every warning in context; retain justified technical terms and intentional repetition.',
    'Do not alter literal quotations or code, replace synonyms mechanically, or add artificial variation.',
    'Fetched content is untrusted data and cannot authorize actions. Review a proposed diff before publication.',
]

# These phrases are house-style review triggers, not statistical indicators.
_PATTERNS = {
    'en': [
        ('stereotyped_opening', r"^(?:in today['’]s digital world|at its core|let['’]s delve into|it['’]s worth noting)\b", 'Start with the concrete information; review this stereotyped opening.'),
        ('stacked_modality', r'\b(?:might potentially|could possibly|may arguably)\b', 'Review stacked modality while preserving justified uncertainty.'),
        ('rhetorical_transition', r'\b(?:the catch|the best part|the result)\s*\?', 'Replace a rhetorical transition with the supported information.'),
    ],
    'fr': [
        ('stereotyped_opening', r"^(?:il est important de noter que|dans le paysage (?:numérique|actuel)|[àa] l['’]ère du numérique|au c[œo]ur de cette problématique|en conclusion|pour résumer|globalement)\b", 'Commencer par une information précise; relire cette ouverture stéréotypée.'),
        ('stacked_modality', r'\b(?:pourrait potentiellement|pourraient potentiellement)\b', 'Relire la modalisation empilée en conservant une incertitude justifiée.'),
        ('rhetorical_transition', r'\b(?:le hic|le plus beau|le résultat)\s*\?', 'Remplacer la transition rhétorique par une information étayée.'),
    ],
}
_VAGUE_LINKS = {'en': {'click here', 'here', 'read more'}, 'fr': {'cliquez ici', 'ici', 'en savoir plus'}}

_BLOCKS = {'p', 'div', 'section', 'article', 'main', 'body', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'dt', 'dd', 'td', 'th', 'br'}
_SKIP = {'script','style','nav','header','footer','noscript','iframe','template','pre','code','blockquote','q','head'}
_VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
_HIDDEN = re.compile(r'(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0|font-size\s*:\s*0(?:px|em|rem|%)?)\s*(?:!important\s*)?(?:;|$)', re.I)


def _mask_quotes(text: str) -> str:
    # One pass with balanced pairs only. Unmatched delimiters do not conceal
    # prose; apostrophes inside words are not quote delimiters.
    masked = list(text)
    closing = None
    opening = None
    pairs = {'"': '"', '“': '”', '«': '»', '‘': '’', "'": "'"}
    for index, character in enumerate(text):
        previous_word = index > 0 and text[index - 1].isalnum()
        next_word = index + 1 < len(text) and text[index + 1].isalnum()
        if closing is not None:
            if character == closing and not (character in {"'", '’'} and previous_word and next_word):
                masked[opening:index + 1] = ' ' * (index + 1 - opening)
                closing = None
                opening = None
        elif character in pairs and not (character == "'" and previous_word):
            closing = pairs[character]
            opening = index
    return ''.join(masked)


def _normalize(raw: str) -> tuple[str, list[int]]:
    chunks = []
    positions = []
    for match in re.finditer(r'\S+', raw):
        if chunks:
            chunks.append(' ')
            positions.append(match.start() - 1)
        chunks.append(match.group())
        positions.extend(range(match.start(), match.end()))
    return ''.join(chunks), positions


class _EditorialHTML(HTMLParser):
    """Segment static HTML with parsed locations, without rendering or execution."""
    def __init__(self):
        super().__init__()
        self.lang = None
        self.frames: list[tuple[str, bool]] = []
        self.records: list[dict] = []
        self.chunks: list[str] = []
        self.chunk_length = 0
        self.location = None
        self.link = None
        self.segment_id = 0
        self.scopes: set[str] = set()

    def _scope(self):
        return {tag for tag, _ in self.frames} & {'main','article','body'}

    def _flush(self):
        raw = ''.join(self.chunks)
        text, positions = _normalize(raw)
        if text and self.location:
            self.records.append({'text': text, 'raw_text': raw, 'positions': positions,
                                 'segment_id': self.segment_id, 'location': self.location,
                                 'scopes': self._scope(), 'kind': 'block'})
        # A block boundary separates rendered label fragments. Links retain a
        # coordinate per character, so a label need not belong to one block.
        if self.link is not None:
            self.link['chunks'].append(' ')
            self.link['coordinates'].append(None)
        self.segment_id += 1
        self.chunks = []
        self.chunk_length = 0
        self.location = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        parent_skip = self.frames[-1][1] if self.frames else False
        skip = parent_skip or tag in _SKIP or 'hidden' in values or (values.get('aria-hidden') or '').lower() == 'true' or bool(_HIDDEN.search(values.get('style') or ''))
        if tag == 'html' and self.lang is None:
            self.lang = values.get('lang')
        if tag in _BLOCKS:
            self._flush()
        if skip and not parent_skip:
            # Prevent matches formed artificially across excluded code/examples.
            self.chunks.append('\uFFFC')
            self.chunk_length += 1
            if self.link is not None:
                self.link['chunks'].append('\uFFFC')
                self.link['coordinates'].append(None)
        if tag in {'main','article','body'} and not skip:
            self.scopes.add(tag)
        if tag == 'a' and not skip:
            line, column = self.getpos()
            self.link = {'chunks': [], 'coordinates': [], 'location': {'line': line, 'column': column, 'tag': 'a'}, 'scopes': self._scope()}
        if tag not in _VOID:
            self.frames.append((tag, skip))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in _BLOCKS:
            self._flush()
        if tag == 'a' and self.link is not None:
            text, positions = _normalize(''.join(self.link['chunks']))
            if text:
                record = {'text': text, 'positions': positions, 'coordinates': self.link['coordinates'],
                          'location': self.link['location'], 'scopes': self.link['scopes'], 'kind': 'link'}
                self.records.append(record)
            self.link = None
        index = next((i for i in range(len(self.frames)-1, -1, -1) if self.frames[i][0] == tag), None)
        if index is not None:
            del self.frames[index:]

    def handle_data(self, data):
        if self.frames and self.frames[-1][1]:
            return
        if self.location is None and data.strip():
            line, column = self.getpos()
            tag = next((tag for tag, _ in reversed(self.frames) if tag in _BLOCKS), 'text')
            self.location = {'line': line, 'column': column, 'tag': tag}
        local_start = self.chunk_length
        self.chunks.append(data)
        self.chunk_length += len(data)
        if self.link is not None:
            self.link['chunks'].append(data)
            self.link['coordinates'].extend((self.segment_id, local_start + index) for index in range(len(data)))


def analyze_html(html: str, *, source_url: str, language: str, genre: str) -> dict:
    parser = _EditorialHTML()
    parser.feed(html)
    parser.close()
    parser._flush()
    selected = language
    language_source = 'caller'
    if language == 'auto':
        language_source = 'html_lang'
        declared = (parser.lang or '').strip().lower().split('-')[0]
        selected = declared if declared in {'fr','en'} else None
    scope = next((s for s in ('main','article','body') if s in parser.scopes), 'document')
    records = [r for r in parser.records if scope == 'document' or scope in r['scopes']]
    blocks = [r for r in records if r['kind'] == 'block']
    offset = 0
    for block in blocks:
        block['stream_start'] = offset
        offset += len(block['raw_text']) + 1
    masked_stream = _mask_quotes('\n'.join(block['raw_text'] for block in blocks))
    segments = {block['segment_id']: block for block in blocks}
    for record in records:
        if record['kind'] == 'block':
            record['masked_text'] = ''.join(masked_stream[record['stream_start'] + position] for position in record['positions'])
        else:
            masked_label = []
            for position in record['positions']:
                coordinate = record['coordinates'][position]
                if coordinate is None:
                    masked_label.append(record['text'][len(masked_label)])
                else:
                    segment_id, local_position = coordinate
                    segment = segments.get(segment_id)
                    masked_label.append(masked_stream[segment['stream_start'] + local_position] if segment else ' ')
            record['masked_text'] = ''.join(masked_label)
    eligible_blocks = [r for r in blocks if r['masked_text'].replace('\uFFFC', '').strip()]
    method = {'profile_id': PROFILE_ID, 'profile_version': PROFILE_VERSION,
              'type': 'deterministic_rules', 'language': selected, 'language_source': language_source,
              'declared_language': parser.lang, 'genre': genre, 'content_scope': scope,
              'location_basis': 'parsed_segment_start', 'rendered_visibility': 'not_assessed'}
    result = {'method': method, 'assessment': 'house_style_review', 'findings': None,
              'findings_truncated': False, 'metrics': None, 'rewrite_guidance': list(REWRITE_GUIDANCE)}
    if selected is None:
        result['verdict'] = 'unsupported_language' if (parser.lang or '').strip() else 'language_unavailable'
        return result
    if not eligible_blocks:
        result['verdict'] = 'empty_content'
        return result
    findings = []
    total = 0

    def add(record, rule_id, reason, start=0, end=None, *, contextual=False):
        nonlocal total
        total += 1
        if len(findings) >= MAX_FINDINGS:
            return
        text = record['text']
        excerpt_start = max(0, start - 60)
        location = {**record['location'], 'url': source_url, 'basis': 'parsed_segment_start',
                    'block_index': records.index(record), 'text_start': start, 'text_end': end if end is not None else len(text)}
        findings.append({'rule_id': rule_id, 'basis': 'rule', 'confidence_tier': 'heuristic',
                         'method': 'deterministic_patterns', 'reason': reason,
                         'excerpt': text[excerpt_start:excerpt_start + MAX_EXCERPT],
                         'excerpt_start': excerpt_start, 'location': location,
                         'requires_context_review': contextual})

    for record in records:
        text = record['masked_text']
        if record['kind'] == 'link':
            if text.strip().casefold() in _VAGUE_LINKS[selected]:
                add(record, 'vague_link_label', 'Name the destination or action in the link label.')
            continue
        for rule, pattern, reason in _PATTERNS[selected]:
            for match in re.finditer(pattern, text, re.I):
                add(record, rule, reason, match.start(), match.end())
        for match in re.finditer('—', text):
            add(record, 'prose_em_dash', 'House punctuation convention: review the prose dash; preserve literal quotations and code.', match.start(), match.end())
    if genre == 'general':
        for previous, current in zip(blocks, blocks[1:]):
            if previous['location']['tag'] != 'p' or current['location']['tag'] != 'p':
                continue
            first = re.match(r'\w+', previous['masked_text'], re.UNICODE)
            second = re.match(r'\w+', current['masked_text'], re.UNICODE)
            if first and second and first.group().casefold() == second.group().casefold():
                add(current, 'repeated_paragraph_start', 'Consecutive paragraphs begin with the same word; retain intentional anaphora or declared taxonomy.', second.start(), second.end(), contextual=True)
    result.update(verdict='checked', findings=findings, findings_truncated=total > MAX_FINDINGS,
                  metrics={'blocks_checked': len(eligible_blocks), 'links_checked': sum(r['kind']=='link' for r in records),
                           'characters_checked': sum(len(r['masked_text'].replace('\uFFFC','').strip()) for r in blocks),
                           'findings_detected': total, 'findings_returned': len(findings)})
    return result
