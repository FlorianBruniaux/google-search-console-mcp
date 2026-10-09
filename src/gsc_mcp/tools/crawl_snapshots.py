"""Immutable, site-owned local inventories from the reviewed SiteOne adapter."""
from __future__ import annotations

from contextlib import closing
from datetime import date, datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import urlsplit

from platformdirs import user_data_dir

from gsc_mcp.meta import with_meta
from gsc_mcp.tools import crawl_import as adapter
from gsc_mcp.tools.crawl_logs import _scope
from gsc_mcp.tools.search_breakdown import _integer

_SCHEMA = 'gsc-crawl-snapshot-v1'
_STORE_DIR = Path(user_data_dir('gsc-mcp')) / 'crawl-snapshots'
_MAX_SNAPSHOTS = 64
_MAX_STORED_BYTES = 16 * 1024 * 1024


def _owner(site: str):
    if not isinstance(site, str) or len(site) > 1024 or any(ord(c) < 32 for c in site):
        raise ValueError('Invalid site')
    return _scope(site)


def _handle(site, snapshot_id):
    _owner(site)
    if not isinstance(snapshot_id, str) or not re.fullmatch('[a-f0-9]{64}', snapshot_id):
        raise ValueError('Invalid snapshot_id')


def _matches(url, scope):
    domain, owner = scope
    try:
        parsed = urlsplit(url)
        parsed.port
        if domain:
            return parsed.hostname == owner.hostname or parsed.hostname.endswith('.'+owner.hostname)
        return (parsed.scheme == owner.scheme and parsed.netloc == owner.netloc
                and parsed.path.startswith(owner.path))
    except (ValueError, AttributeError):
        return False


def _snapshot(report_json, site, producer):
    scope = _owner(site)
    if producer != 'siteone':
        raise adapter._Rejected('unsupported_producer')
    document, encoded = adapter._parse(report_json)
    preview = adapter._preview(document, encoded)
    rows, _, _, _ = adapter._rows(document, preview_rows=adapter._LIMITS['input_rows'])
    selected = [row for row in rows if _matches(row['raw_url'], scope)]
    sid = adapter._hash(adapter._canonical({'schema': _SCHEMA, 'site': site,
        'adapter': adapter._ADAPTER, 'source_sha256': preview['source']['sha256']}))
    return {'schema': _SCHEMA, 'snapshot_id': sid,
            'owner': {'site': site, 'association': 'caller_declared'},
            'adapter': preview['adapter'], 'source': preview['source'],
            'scope': preview['scope'], 'coverage': {key: value for key, value in preview['counts'].items()
                if key not in {'preview_rows', 'omitted_accepted_rows'}},
            'scope_excluded_rows': len(rows)-len(selected),
            'duplicate_url_rows': len(selected)-len({r['raw_url'] for r in selected}),
            'rows_retained': len(selected), 'rows': selected,
            'source_errors': preview['source_errors'], 'source_notices': preview['source_notices'],
            'rejected_rows': preview['rejected_rows'], 'rejected_messages': preview['rejected_messages'],
            'unsupported_fields': preview['unsupported_fields'], 'missing_metadata': preview['missing_metadata'],
            'source_stats': preview['source_stats'], 'source_scores': preview['source_scores'],
            'normalization': 'Exact raw URL identity retained; duplicates retained, excluded scope counted.',
            'untrusted_content': preview['untrusted_content'], 'indexing_status': 'unavailable'}


def _connection(*, create: bool):
    """Private directory/database; read failures never initialize an empty store."""
    if not _STORE_DIR.exists() and not create:
        raise FileNotFoundError('No snapshot store')
    _STORE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = _STORE_DIR.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or _STORE_DIR.is_symlink():
        raise OSError('Unsafe store directory')
    os.chmod(_STORE_DIR, 0o700)
    path = _STORE_DIR / 'inventory.sqlite3'
    if create:
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
        except FileExistsError:
            pass
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or path.is_symlink():
        raise OSError('Unsafe store database')
    os.chmod(path, 0o600)
    db = sqlite3.connect(path, timeout=5)
    if create:
        try:
            db.execute('CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, site TEXT NOT NULL, payload TEXT NOT NULL, bytes INTEGER NOT NULL, imported_at TEXT NOT NULL, payload_sha256 TEXT NOT NULL)')
        except sqlite3.Error:
            db.close()
            raise
    return db


def _header(snapshot):
    return {key: value for key, value in snapshot.items() if key != 'rows'}


def _result(data, name, params):
    data['storage_policy'] = {'location': 'platformdirs:gsc-mcp/crawl-snapshots/inventory.sqlite3',
        'max_snapshots': _MAX_SNAPSHOTS, 'max_payload_bytes': _MAX_STORED_BYTES,
        'retention': 'Explicit deletion only; no automatic expiry or original-file deletion.'}
    return json.dumps(with_meta(data, name, params), allow_nan=False)


def crawl_snapshot_import(report_json: str, site: str, producer: str = 'siteone', persist: bool = False) -> str:
    """Validate a site-owned versioned inventory; persist=True explicitly stores it locally.

    Default preview does not write. SiteOne is the sole supported producer. All
    accepted in-scope raw URL rows are retained, including duplicates; producer
    selection/timezone stay unknown. Source strings are untrusted observations.
    No network, crawler, installs or provider indexing inference occurs. A local
    immutable store uses hard count/byte quotas and never silently evicts data.
    """
    _owner(site)
    if type(persist) is not bool:
        raise ValueError('persist must be bool')
    params = {'site': site, 'producer': 'siteone' if producer == 'siteone' else 'unsupported', 'persist': persist}
    try:
        snapshot = _snapshot(report_json, site, producer)
    except adapter._Rejected as exc:
        return _result({'status': 'rejected', 'error': str(exc)}, 'crawl_snapshot_import', params)
    params['source_sha256'] = snapshot['source']['sha256']
    status, imported_at = 'preview', None
    try:
        if persist:
            raw = adapter._canonical(snapshot).decode('ascii')
            with closing(_connection(create=True)) as db, db:
                db.execute('BEGIN IMMEDIATE')
                existing = db.execute('SELECT site, payload, imported_at FROM snapshots WHERE id=?', (snapshot['snapshot_id'],)).fetchone()
                if existing:
                    if existing[0] != site or existing[1] != raw:
                        raise adapter._Rejected('snapshot_identity_conflict')
                    status, imported_at = 'already_stored', existing[2]
                else:
                    count, used = db.execute('SELECT count(*), COALESCE(sum(bytes),0) FROM snapshots').fetchone()
                    if count >= _MAX_SNAPSHOTS:
                        raise adapter._Rejected('snapshot_quota')
                    if used + len(raw.encode('ascii')) > _MAX_STORED_BYTES:
                        raise adapter._Rejected('snapshot_byte_quota')
                    imported_at = datetime.now(timezone.utc).isoformat()
                    db.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?)', (snapshot['snapshot_id'], site, raw, len(raw), imported_at, adapter._hash(raw.encode('ascii'))))
                    status = 'stored'
    except (OSError, sqlite3.Error, adapter._Rejected) as exc:
        return _result({'status': 'unavailable', 'error': str(exc) if isinstance(exc, adapter._Rejected) else type(exc).__name__,
                        'snapshot': _header(snapshot)}, 'crawl_snapshot_import', params)
    return _result({'status': status, 'snapshot': _header(snapshot), 'imported_at': imported_at}, 'crawl_snapshot_import', params)


def _load(site, snapshot_id):
    _handle(site, snapshot_id)
    with closing(_connection(create=False)) as db:
        row = db.execute('SELECT CASE WHEN length(payload)<=? THEN payload ELSE NULL END, imported_at, payload_sha256 FROM snapshots WHERE id=? AND site=?', (_MAX_STORED_BYTES, snapshot_id, site)).fetchone()
    if row is None:
        raise FileNotFoundError('Snapshot not found')
    if row[0] is None or adapter._hash(row[0].encode('utf-8')) != row[2]:
        raise ValueError('Stored payload integrity failure')
    adapter._check_nesting(row[0])
    snapshot = json.loads(row[0], object_pairs_hook=adapter._pairs, parse_constant=adapter._constant)
    adapter._check_values(snapshot)
    if (not isinstance(snapshot, dict) or snapshot.get('schema') != _SCHEMA
            or snapshot.get('snapshot_id') != snapshot_id or snapshot.get('owner', {}).get('site') != site
            or not isinstance(snapshot.get('rows'), list) or len(snapshot['rows']) > 5000):
        raise ValueError('Stored snapshot schema mismatch')
    return snapshot, row[1]


def crawl_snapshot_read(site: str, snapshot_id: str, offset: int = 0, limit: int = 50) -> str:
    """Read a bounded page of an immutable local inventory owned by the exact site.

    No storage is created on a missing read. Exact raw URL rows retain the source
    envelope, failures, unknown selection and imported rule-score boundaries.
    Unavailable lookup is not an empty inventory or a provider indexing verdict.
    """
    _handle(site, snapshot_id)
    _integer(offset, 'offset', 0, 5000)
    _integer(limit, 'limit', 1, 100)
    params = {'site': site, 'snapshot_id': snapshot_id, 'offset': offset, 'limit': limit}
    try:
        snapshot, imported_at = _load(site, snapshot_id)
    except (OSError, sqlite3.Error, ValueError) as exc:
        return _result({'status': 'unavailable', 'error': 'snapshot_not_found' if isinstance(exc, FileNotFoundError) else type(exc).__name__}, 'crawl_snapshot_read', params)
    selected = snapshot['rows'][offset:offset+limit]
    total = len(snapshot['rows'])
    return _result({'status': 'observed', 'snapshot': _header(snapshot), 'imported_at': imported_at,
                    'rows': selected, 'pagination': {'offset': offset, 'limit': limit, 'total': total,
                        'returned': len(selected), 'remaining': max(0, total-offset-len(selected))}}, 'crawl_snapshot_read', params)


def crawl_snapshot_delete(site: str, snapshot_id: str, confirm: bool = False) -> str:
    """Delete one local site-owned imported snapshot only with explicit confirm=True.

    Never deletes the original export, uploads data or changes a provider/site.
    There is no wildcard purge or automatic retention. Missing records are reported.
    """
    _handle(site, snapshot_id)
    if type(confirm) is not bool:
        raise ValueError('confirm must be bool')
    params = {'site': site, 'snapshot_id': snapshot_id, 'confirm': confirm}
    if not confirm:
        return _result({'status': 'confirmation_required'}, 'crawl_snapshot_delete', params)
    try:
        with closing(_connection(create=False)) as db, db:
            changed = db.execute('DELETE FROM snapshots WHERE id=? AND site=?', (snapshot_id, site)).rowcount
    except (OSError, sqlite3.Error) as exc:
        return _result({'status': 'unavailable', 'error': 'snapshot_not_found' if isinstance(exc, FileNotFoundError) else type(exc).__name__}, 'crawl_snapshot_delete', params)
    return _result({'status': 'deleted' if changed else 'unavailable', 'deleted_records': changed}, 'crawl_snapshot_delete', params)


def _supplied_report(raw, site, expected_tools):
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > adapter._LIMITS['input_bytes']:
        raise adapter._Rejected('input_bytes_limit')
    adapter._check_nesting(raw)
    try:
        data = json.loads(raw, object_pairs_hook=adapter._pairs, parse_constant=adapter._constant)
    except (ValueError, UnicodeError):
        raise adapter._Rejected('invalid_json') from None
    adapter._check_values(data)
    if not isinstance(data, dict) or data.get('site') != site or not isinstance(data.get('_meta'), dict):
        raise adapter._Rejected('source_site_mismatch')
    meta = data['_meta']
    if (meta.get('tool') not in expected_tools or not isinstance(meta.get('params'), dict)
            or meta['params'].get('site') != site or data.get('error')):
        raise adapter._Rejected('unsupported_source_contract')
    return data, adapter._hash(raw.encode('utf-8'))


def _search_input(raw, site):
    data, digest = _supplied_report(raw, site, {'get_search_analytics', 'get_advanced_search_analytics'})
    if data['_meta']['params'].get('dimensions') != ['page'] or data.get('dimensions', ['page']) != ['page']:
        raise adapter._Rejected('page_only_dimensions_required')
    window = data.get('date_range')
    try:
        if not isinstance(window, dict) or set(window) != {'start', 'end'} or date.fromisoformat(window['start']) > date.fromisoformat(window['end']):
            raise ValueError
    except (ValueError, TypeError, KeyError):
        raise adapter._Rejected('invalid_source_window') from None
    rows = data.get('rows')
    if not isinstance(rows, list) or len(rows) > 5000:
        raise adapter._Rejected('source_row_limit')
    indexed = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not adapter._valid_url(row.get('page')) or not _matches(row['page'], _owner(site)):
            raise adapter._Rejected('invalid_source_row')
        metrics = {}
        for field in ('clicks', 'impressions', 'ctr', 'position'):
            value = row.get(field)
            if value is not None and (type(value) not in (float, int) or not math.isfinite(value) or value < 0
                                      or (field == 'ctr' and value > 1)):
                raise adapter._Rejected('invalid_source_metric')
            # Legacy parser zero CTR/position with zero impressions is not a measurement.
            metrics[field] = None if field in {'ctr', 'position'} and row.get('impressions') in (None, 0) else value
        indexed.setdefault(row['page'], []).append({'metrics': metrics, 'source_pointer': f'/rows/{index}'})
    return indexed, {'sha256': digest, 'tool': data['_meta']['tool'], 'site': site,
        'requested_window': window, 'observed_window': 'unknown', 'returned_rows': len(rows),
        'completeness': 'unknown', 'search_type': data.get('search_type', 'web'),
        'data_state': data.get('data_state', 'unknown'), 'authenticated_origin': 'unverified'}


def _link_input(raw, site):
    data, digest = _supplied_report(raw, site, {'link_equity_map'})
    indexed = {}
    categories = ('orphan_candidates', 'underlinked_striking_distance', 'footer_only_targets')
    for category in categories:
        rows = data.get(category, [])
        if not isinstance(rows, list) or len(rows) > 100:
            raise adapter._Rejected('source_row_limit')
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not adapter._valid_url(row.get('url')) or not _matches(row['url'], _owner(site)):
                raise adapter._Rejected('invalid_source_row')
            if not isinstance(row.get('path'), str):
                raise adapter._Rejected('invalid_source_row')
            counts = {}
            for field in ('body_inbound', 'demoted_inbound'):
                value = row.get(field)
                if value is not None and (type(value) is not int or value < 0):
                    raise adapter._Rejected('invalid_source_metric')
                counts[field] = value
            indexed.setdefault(row['url'], []).append({'category': category, 'path': row['path'],
                'source_pointer': f'/{category}/{index}', **counts})
    coverage = {}
    for field in ('pages_in_gsc', 'pages_targeted', 'pages_crawled', 'pages_failed'):
        value = data.get(field)
        if value is not None and (type(value) is not int or value < 0):
            raise adapter._Rejected('invalid_source_metric')
        coverage[field] = value
    return indexed, {'sha256': digest, 'tool': 'link_equity_map', 'site': site,
        'coverage': coverage, 'collected_at': None, 'observed_window': 'unknown',
        'normalization': 'Path only; query/fragment discarded and trailing slash stripped by producer.',
        'authenticated_origin': 'unverified'}


def crawl_snapshot_join(site: str, snapshot_id: str, search_report_json: str | None = None,
                        link_report_json: str | None = None, offset: int = 0, limit: int = 50) -> str:
    """Reconcile one local inventory page with bounded caller-supplied MCP reports.

    GSC inputs must be page-only Search Analytics results with the same exact site
    and explicit requested window. Raw URL strings match exactly; duplicate search
    keys are ambiguous, absent rows unavailable, and zero never means unindexed.
    Link-map inputs retain their path-only aggregation and bounded candidate scope;
    absence from that list is not a site-wide orphan verdict. Incoming metadata is
    caller-supplied and cannot authenticate provider origin. No acquisition occurs.
    """
    _handle(site, snapshot_id)
    _integer(offset, 'offset', 0, 5000)
    _integer(limit, 'limit', 1, 100)
    params = {'site': site, 'snapshot_id': snapshot_id, 'offset': offset, 'limit': limit}
    try:
        snapshot, imported_at = _load(site, snapshot_id)
        search, search_source = _search_input(search_report_json, site) if search_report_json is not None else ({}, None)
        links, link_source = _link_input(link_report_json, site) if link_report_json is not None else ({}, None)
    except adapter._Rejected as exc:
        return _result({'status': 'rejected', 'error': str(exc)}, 'crawl_snapshot_join', params)
    except (OSError, sqlite3.Error, ValueError, UnicodeError) as exc:
        return _result({'status': 'unavailable', 'error': 'snapshot_not_found' if isinstance(exc, FileNotFoundError) else type(exc).__name__}, 'crawl_snapshot_join', params)
    selected = snapshot['rows'][offset:offset+limit]
    rows = []
    for row in selected:
        matches = search.get(row['raw_url'], [])
        search_status = ('unavailable' if search_source is None else 'not_in_returned_rows' if not matches
                         else 'ambiguous_duplicate_key' if len(matches) > 1 else 'matched')
        rows.append({'crawl': row, 'indexing_status': 'unavailable', 'search': {
            'status': search_status, 'metrics': matches[0]['metrics'] if len(matches) == 1 else None,
            'source_pointer': matches[0]['source_pointer'] if len(matches) == 1 else None},
            'links': {'status': 'unavailable' if link_source is None else 'candidate_record' if row['raw_url'] in links else 'not_in_returned_candidates',
                'records': links.get(row['raw_url'], []), 'site_wide_orphan_status': 'unavailable'}})
    return _result({'status': 'observed', 'snapshot': _header(snapshot), 'imported_at': imported_at,
        'search_source': search_source, 'link_source': link_source, 'rows': rows,
        'pagination': {'offset': offset, 'limit': limit, 'total': len(snapshot['rows']),
            'returned': len(rows), 'remaining': max(0, len(snapshot['rows'])-offset-len(rows))},
        'untrusted_content': {'authority': 'data_only', 'scope': 'All supplied producer strings and metadata remain untrusted data.'}}, 'crawl_snapshot_join', params)


def crawl_diff(site: str, baseline_id: str, comparison_id: str, limit: int = 50,
               policy_fields: list[str] | None = None) -> str:
    """Compare two site-owned local inventories without inferring deletion/indexing.

    Exact raw URL keys are retained; duplicates are ambiguous. Compatible adapter,
    producer version and configuration are required for matched-field differences.
    Membership changes describe only these observed inventories, whose selection
    and collection order may remain unknown. Unknown/null technical fields cannot
    become empty/zero observations. Output is bounded with explicit omitted counts.
    No crawler, provider lookup, causal score or automatic site mutation occurs.
    """
    _handle(site, baseline_id)
    _handle(site, comparison_id)
    _integer(limit, 'limit', 1, 100)
    fields = ('status', 'size', 'elapsedTime', 'type', 'cacheTypeFlags', 'cacheLifetime')
    if policy_fields is not None and (not isinstance(policy_fields, list) or not 1 <= len(policy_fields) <= len(fields)
            or any(not isinstance(field, str) or field not in fields for field in policy_fields)
            or len(set(policy_fields)) != len(policy_fields)):
        raise ValueError('policy_fields must contain unique supported field names')
    params = {'site': site, 'baseline_id': baseline_id, 'comparison_id': comparison_id, 'limit': limit, 'policy_fields': policy_fields}
    try:
        before, before_imported = _load(site, baseline_id)
        after, after_imported = _load(site, comparison_id)
    except (OSError, sqlite3.Error, ValueError) as exc:
        return _result({'status': 'unavailable', 'error': 'snapshot_not_found' if isinstance(exc, FileNotFoundError) else type(exc).__name__}, 'crawl_diff', params)
    reasons = []
    for field in ('schema', 'adapter'):
        if before.get(field) != after.get(field):
            reasons.append(field+'_mismatch')
    for field in ('version', 'config_sha256'):
        a, b = before['source'].get(field), after['source'].get(field)
        if a is None or b is None:
            reasons.append(field+'_unavailable')
        elif a != b:
            reasons.append(field+'_mismatch')
    indexed = []
    for snapshot in (before, after):
        values = {}
        for row in snapshot['rows']:
            values.setdefault(row['raw_url'], []).append(row)
        indexed.append(values)
    left, right = indexed
    ambiguous = {u for u in left.keys() | right.keys() if len(left.get(u, [])) > 1 or len(right.get(u, [])) > 1}
    changes = []
    counts = {'only_in_comparison_inventory': 0, 'absent_from_comparison_inventory': 0,
              'observed_field_differences': 0, 'matched_raw_urls': 0, 'ambiguous_raw_urls': len(ambiguous),
              'unavailable_matched_field_pairs': 0, 'omitted_changes': 0}

    def add(kind, url, **values):
        counts[kind if kind != 'observed_field_difference' else 'observed_field_differences'] += 1
        if len(changes) < limit:
            changes.append({'kind': kind, 'raw_url': url, 'baseline_snapshot_id': baseline_id,
                'comparison_snapshot_id': comparison_id, **values})
        else:
            counts['omitted_changes'] += 1

    unavailable_fields, changed_fields = set(), set()
    for url in sorted(left.keys() | right.keys()):
        if url in ambiguous:
            continue
        a, b = left.get(url), right.get(url)
        if a is None:
            add('only_in_comparison_inventory', url, before=None, after=b[0], before_row_index=None, after_row_index=b[0]['row_index'])
        elif b is None:
            add('absent_from_comparison_inventory', url, before=a[0], after=None, before_row_index=a[0]['row_index'], after_row_index=None)
        else:
            counts['matched_raw_urls'] += 1
            if reasons:
                continue
            if any(not isinstance(r.get('status'), str) or not re.fullmatch('[1-5][0-9]{2}', r['status']) for r in (a[0], b[0])):
                # No received HTTP response: numeric default fields do not describe a page change.
                counts['unavailable_matched_field_pairs'] += len(fields)
                unavailable_fields.update(fields)
                continue
            for field in fields:
                old, new = a[0].get(field), b[0].get(field)
                unavailable = old is None or new is None
                if field == 'status':
                    unavailable |= any(not isinstance(v, str) or not re.fullmatch('[1-5][0-9]{2}', v) for v in (old, new))
                elif field in {'size', 'elapsedTime'}:
                    unavailable |= any(type(v) not in (float, int) or v < 0 for v in (old, new))
                if unavailable:
                    counts['unavailable_matched_field_pairs'] += 1
                    unavailable_fields.add(field)
                elif old != new:
                    changed_fields.add(field)
                    add('observed_field_difference', url, field=field, before=old, after=new,
                        before_row_index=a[0]['row_index'], after_row_index=b[0]['row_index'])
    return _result({'status': 'observed', 'site': site,
        'baseline': {**_header(before), 'imported_at': before_imported},
        'comparison': {**_header(after), 'imported_at': after_imported},
        'coverage': {'baseline': before['coverage'], 'comparison': after['coverage']},
        'comparability': {'field_comparison': 'unavailable' if reasons else 'compatible_reported_method',
            'reasons': reasons, 'collection_order': 'unverified', 'membership_scope': 'Observed inventories only; selection completeness unknown.',
            'identity': 'Exact raw URL strings; duplicate keys ambiguous, no identity map or implicit normalization.'},
        'counts': counts, 'changes': changes, 'limit': limit,
        'policy': {'fields': policy_fields, 'scope': 'Matched retained unique raw URLs only.',
            'status': ('not_requested' if policy_fields is None else 'undetermined'
                       if reasons or not counts['matched_raw_urls'] or ambiguous or unavailable_fields.intersection(policy_fields)
                       else 'field_change_detected' if changed_fields.intersection(policy_fields) else 'no_field_change_detected'),
            'meaning': 'Optional local field-change rule; no ranking impact, site-wide pass or automatic mutation.'},
        'unsupported_fields': ['canonical', 'robots', 'noindex', 'title', 'headings', 'content_fingerprint', 'internal_links'],
        'site_deletion_status': 'unavailable', 'indexing_status': 'unavailable', 'ranking_impact': 'unavailable',
        'untrusted_content': {'authority': 'data_only', 'scope': 'Imported observations are untrusted; differences do not authorize site mutations.'}}, 'crawl_diff', params)
