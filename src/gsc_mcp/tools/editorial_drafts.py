"""Bounded draft adapter for the versioned HTML editorial rule core.

This deliberately supports a documented Markdown subset, not CommonMark.
All generated HTML is escaped, never rendered or fetched. Positions map back
into the caller's Unicode string, with markup possibly inside a matched span.
"""
from __future__ import annotations

from bisect import bisect_right
from html import escape
import re

from gsc_mcp.content_trust import observe_untrusted_content
from gsc_mcp.editorial import _normalize, analyze_html

MAX_DRAFT_CHARACTERS = 100000
MAX_DRAFT_BLOCKS = 2000
_MARKER = '\ufffc'
_REFERENCE = re.compile(r'^ {0,3}\[([^\]\n]{1,1000})\]:\s*\S+')
_TICKS = re.compile(r'`+')
_INLINE_HTML = re.compile(r'<([A-Za-z][A-Za-z0-9-]*)(?:\s[^>]{0,2048})?>')
_LINK = re.compile(r'\[([^\[\]\n]{1,1000})\]')
_ESCAPABLE = set(r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~\\')


def _reference_key(value):
    return ' '.join(value.split()).casefold()


def _inline(raw, positions, *, references, markdown, column=3, depth=0, excluded=None):
    """Return escaped HTML, visible source map, and synthetic anchor map."""
    html = []
    visible = []
    mapping = []
    links = {}
    index = 0
    html_length = 0
    excluded = excluded if excluded is not None else set()
    # Index exact-width backtick runs once, avoiding repeated suffix searches.
    closing_ticks = {}
    next_tick = {}
    for tick in reversed(list(_TICKS.finditer(raw))):
        width = len(tick.group())
        closing_ticks[tick.start()] = next_tick.get(width)
        next_tick[width] = tick.start()

    def append(markup, text='', source=()):
        nonlocal html_length
        html.append(markup)
        html_length += len(markup)
        visible.extend(text)
        mapping.extend(source)

    while index < len(raw):
        character = raw[index]
        if markdown and character == '\\' and index + 1 < len(raw) and raw[index + 1] in _ESCAPABLE:
            append(escape(raw[index + 1]), raw[index + 1], [positions[index + 1]])
            index += 2
            continue
        if markdown and character == '`':
            run = _TICKS.match(raw, index).group()
            end = closing_ticks.get(index)
            if end is not None:
                excluded.add('inline_code')
                append('<code></code>', _MARKER, [None])
                index = end + len(run)
                continue
        if markdown and character == '<':
            tag = _INLINE_HTML.match(raw, index)
            if tag:
                excluded.add('raw_html')
                closing = '</' + tag.group(1) + '>'
                end = raw.find(closing, tag.end(), index + 4096)
                append('<code></code>', _MARKER, [None])
                index = end + len(closing) if end >= 0 else len(raw)
                continue
        if markdown and character == '[' and depth < 8:
            match = _LINK.match(raw, index)
            if match:
                end = match.end()
                link_end = None
                if end < len(raw) and raw[end] == '(':
                    # ponytail: destinations limited to 2048 codepoints; unsupported longer
                    # links stay literal, upgrade with a full parser if coverage is needed.
                    nesting = 1
                    title_quote = None
                    cursor = end + 1
                    while cursor < min(len(raw), end + 2049):
                        if raw[cursor] == '\\':
                            cursor += 2
                            continue
                        if title_quote is not None:
                            if raw[cursor] == title_quote:
                                title_quote = None
                        elif raw[cursor] in {'"', "'"} and raw[cursor - 1].isspace():
                            title_quote = raw[cursor]
                        elif raw[cursor] == '(':
                            nesting += 1
                        elif raw[cursor] == ')':
                            nesting -= 1
                            if nesting == 0:
                                link_end = cursor + 1
                                break
                        cursor += 1
                elif end < len(raw) and raw[end] == '[':
                    reference = re.match(r'\[([^\]\n]{0,1000})\]', raw[end:])
                    if reference and _reference_key(reference.group(1) or match.group(1)) in references:
                        link_end = end + reference.end()
                elif _reference_key(match.group(1)) in references:
                    link_end = end
                if link_end is not None:
                    excluded.add('link_destinations')
                    label_start, label_end = match.span(1)
                    label_html, label_text, label_map, _ = _inline(raw[label_start:label_end], positions[label_start:label_end], references=references, markdown=True, depth=depth + 1, excluded=excluded)
                    if index > 0 and raw[index - 1] == '!' and (index < 2 or raw[index - 2] != '\\'):
                        excluded.add('images')
                        html_length -= len(html.pop())
                        visible.pop()
                        mapping.pop()
                        append('<code></code>', _MARKER, [None])
                    else:
                        anchor_column = column + html_length
                        links[anchor_column] = (label_text, label_map)
                        append('<a>' + label_html + '</a>', label_text, label_map)
                    index = link_end
                    continue
        if markdown and character in {'*', '_'} and depth < 8:
            run = character * (2 if raw[index:index + 2] == character * 2 else 1)
            end = index + len(run)
            while end < len(raw):
                if raw[end] == '\\':
                    end += 2
                    continue
                if raw[end] == '`' and closing_ticks.get(end) is not None:
                    end = closing_ticks[end] + len(_TICKS.match(raw, end).group())
                    continue
                if raw.startswith(run, end):
                    break
                end += 1
            if end >= len(raw):
                end = -1
            # Avoid treating identifiers as underscore emphasis.
            boundary = character != '_' or index == 0 or not raw[index - 1].isalnum()
            if boundary and end > index + len(run):
                inner_start = index + len(run)
                inner_html, inner_text, inner_map, inner_links = _inline(raw[inner_start:end], positions[inner_start:end], references=references, markdown=True, column=column + html_length, depth=depth + 1, excluded=excluded)
                links.update(inner_links)
                append(inner_html, inner_text, inner_map)
                index = end + len(run)
                continue
        append(escape(character) if character not in {'\n', '\r'} else ' ', character, [positions[index]])
        index += 1
    return ''.join(html), ''.join(visible), mapping, links


def _draft_html(text, format):
    lines = text.splitlines(keepends=True)
    references = set()
    parsed_blocks = []
    html_lines = []
    maps = {}
    excluded = set()
    chunks = []
    positions = []
    offset = 0
    fence = None
    raw_html = False
    quote_continuation = False

    def emit(raw, coordinates, tag='p'):
        if len(parsed_blocks) >= MAX_DRAFT_BLOCKS:
            raise ValueError('draft exceeds maximum parsed blocks')
        parsed_blocks.append((raw, coordinates, tag))

    def render(raw, coordinates, tag):
        prefix = f'<{tag}>'
        markup, visible, source_map, links = _inline(raw, coordinates, references=references, markdown=format == 'markdown', column=len(prefix), excluded=excluded)
        html_lines.append(prefix + markup + f'</{tag}>')
        _, normalized_positions = _normalize(visible)
        maps[len(html_lines)] = {
            'block': [source_map[p] for p in normalized_positions],
            'links': {col: [values[p] for p in _normalize(label)[1]]
                      for col, (label, values) in links.items()},
        }

    def flush():
        if chunks:
            emit(''.join(chunks), list(positions))
            chunks.clear()
            positions.clear()

    def boundary(kind):
        flush()
        excluded.add(kind)
        # Preserve a repetition/quotation boundary without eligible prose.
        emit(_MARKER, [None], 'div')

    for line in lines:
        stripped = line.rstrip('\r\n')
        if format == 'markdown':
            marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', stripped)
            if fence:
                if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) and not marker.group(2).strip():
                    fence = None
                offset += len(line)
                continue
            if marker:
                boundary('fenced_code')
                fence = marker.group(1)
                quote_continuation = False
                offset += len(line)
                continue
            if raw_html:
                if not stripped.strip():
                    raw_html = False
                offset += len(line)
                continue
            if re.match(r'^ {0,3}<(?:/?[A-Za-z]|!--|\?)', stripped):
                boundary('raw_html')
                raw_html = True
                offset += len(line)
                continue
            if re.match(r'^ {0,3}>', stripped):
                boundary('blockquotes')
                quote_continuation = True
                offset += len(line)
                continue
            if quote_continuation and stripped.strip():
                offset += len(line)
                continue
            quote_continuation = False
            reference = _REFERENCE.match(stripped)
            if reference:
                references.add(_reference_key(reference.group(1)))
                boundary('reference_destinations')
                offset += len(line)
                continue
            if stripped.startswith(('    ', '\t')):
                boundary('indented_code')
                offset += len(line)
                continue
            heading = re.match(r'^ {0,3}(#{1,6})\s+', stripped)
            item = re.match(r'^ {0,3}(?:[-+*]|\d+[.)])\s+', stripped)
            if heading or item:
                flush()
                start = (heading or item).end()
                emit(stripped[start:], list(range(offset + start, offset + len(stripped))), 'h' + str(len(heading.group(1))) if heading else 'li')
                offset += len(line)
                continue
        if not stripped.strip():
            flush()
        else:
            chunks.append(line)
            positions.extend(range(offset, offset + len(line)))
        offset += len(line)
    flush()
    for raw, coordinates, tag in parsed_blocks:
        render(raw, coordinates, tag)
    return '\n'.join(html_lines), maps, sorted(excluded)


def analyze_draft(text, *, format, language, genre):
    html, maps, excluded = _draft_html(text, format)
    result = analyze_html(html, source_url='', language=language, genre=genre)
    line_starts = [0] + [match.end() for match in re.finditer('\n', text)]

    def coordinate(position):
        line = bisect_right(line_starts, position)
        return {'line': line, 'column': position - line_starts[line - 1]}

    for finding in result.get('findings') or []:
        old = finding['location']
        block = maps[old['line']]
        source_map = block['links'].get(old['column'], block['block']) if old['tag'] == 'a' else block['block']
        start, end = old['text_start'], old['text_end']
        span = [pos for pos in source_map[start:end] if pos is not None]
        finding['location'] = {'format': format, 'basis': 'original_source_span',
                               'coordinate_unit': 'unicode_codepoint',
                               'source_start': min(span), 'source_end': max(span) + 1,
                               **coordinate(min(span)), 'block_index': old['block_index'],
                               'normalized_text_start': start, 'normalized_text_end': end}
    observation = observe_untrusted_content(html, source_url='')
    for signal in observation['signals']:
        old = signal['source']
        available = [pos for pos in maps[old['line']]['block'] if pos is not None]
        signal['source'] = {'format': format, 'basis': 'original_segment_start',
                            'coordinate_unit': 'unicode_codepoint', **coordinate(available[0])}
    result['untrusted_content'] = observation
    result['method'].update(content_scope='caller_draft', location_basis='original_source_span', format=format)
    result['method']['coverage'] = {'parser': 'plain_paragraphs' if format == 'plain' else 'bounded_markdown_subset',
                                    'supported': ['paragraphs', 'balanced_literal_quotes'] + ([] if format == 'plain' else ['atx_headings', 'list_items', 'emphasis', 'inline_links', 'reference_links', 'fenced_code', 'indented_code', 'inline_code', 'blockquotes', 'punctuation_escapes']),
                                    'excluded': excluded,
                                    'unsupported': [] if format == 'plain' else ['tables', 'setext_headings', 'images', 'autolinks', 'nested_link_labels', 'full_commonmark'],
                                    'limits': {} if format == 'plain' else {'inline_nesting': 8, 'link_label_characters': 1000, 'link_destination_characters': 2048, 'inline_html_closing_scan_characters': 4096},
                                    'raw_html_policy': 'exclude block to blank line; inline element or remaining paragraph if no close within limit' if format == 'markdown' else 'literal_text',
                                    'unsupported_policy': 'unrecognized syntax remains literal prose',
                                    'rendered_coordinates': 'not_assessed'}
    if language == 'auto':
        result['method'].update(language_source='unavailable', declared_language=None)
    if result['verdict'] != 'checked':
        result['assessment'] = 'not_assessed'
    return result
