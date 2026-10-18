#!/usr/bin/env python3
"""Acquire a read-only plan or reuse saved sources; optionally draft/review with a native CLI."""
import argparse
import json
import os
from pathlib import Path
import sys

from gsc_mcp.audit_runtime import AuditSession, AuditBudgetExceeded
from gsc_mcp.native_audit import run_specialists, validate_native_options
from gsc_mcp.native_roles import ROLE_PROFILES


def load(path, limit=2_000_000):
    with open(path, 'rb') as handle: raw = handle.read(limit + 1)
    if len(raw) > limit: raise ValueError('Input exceeds byte budget')
    return json.loads(raw)


def write_private(path, packet):
    encoded = json.dumps(packet, ensure_ascii=False, allow_nan=False).encode()
    if len(encoded) > 8_000_000: raise ValueError('Output exceeds byte budget')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def restore_sources(saved, session):
    current = session.status()
    if not isinstance(saved, dict) or saved.get('config_digest') != session.digest:
        raise ValueError('Saved sources require the original audit configuration')
    previous = saved.get('run')
    if not isinstance(previous, dict) or any(previous.get(k) != current[k] for k in ('run_id', 'site')):
        raise ValueError('Saved sources belong to another run')
    for key in ('provider_attempts', 'tool_calls', 'native_attempts'):
        if type(previous.get(key)) is not int or not 0 <= previous[key] <= current[key]:
            raise ValueError('Saved sources require the original attempt ledger')
    observations = saved.get('observations')
    if not isinstance(observations, list) or not 1 <= len(observations) <= min(session.config['max_tool_calls'], 100):
        raise ValueError('Invalid saved observations')
    for row in observations:
        if not isinstance(row, dict) or set(row) != {'tool', 'arguments', 'result'} or not isinstance(row['arguments'], dict):
            raise ValueError('Invalid saved observation')
        session.validate_request(row['tool'], row['arguments'])
    # Previous generated drafts/reviews are not source evidence for this new attempt.
    return {'run': current, 'config_digest': session.digest, 'observations': observations,
            'source_run': saved.get('source_run', previous)}


def main():
    os.environ['GSC_NO_BROWSER'] = '1'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--requests')
    source.add_argument('--resume-from', help='Saved source checkpoint or report; reuse the original config and ledger')
    parser.add_argument('--output', required=True)
    parser.add_argument('--host', choices=['none', 'claude', 'codex'], default='none')
    parser.add_argument('--model')
    parser.add_argument('--specialist', action='append', choices=sorted(ROLE_PROFILES), default=[],
                        help='Source-only role; repeat this flag to select several roles')
    parser.add_argument('--max-native-concurrency', type=int, default=1,
                        help='Concurrent specialist invocations, 1 to 4; synthesis/review stay sequential')
    args = parser.parse_args()
    try:
        config = load(args.config)
        if args.requests:
            plan = load(args.requests)
            if not isinstance(plan, list) or not 1 <= len(plan) <= min(config['max_tool_calls'], 100):
                raise ValueError('Invalid request count')
            for row in plan:
                if not isinstance(row, dict) or set(row) != {'tool', 'arguments'} or not isinstance(row['arguments'], dict):
                    raise ValueError('Invalid request shape')
        else:
            saved = load(args.resume_from, limit=8_000_000)
            if not Path(config['ledger_path']).is_file():
                raise ValueError('Recovery requires the existing attempt ledger')
        if args.host != 'none':
            validate_native_options(host=args.host, model=args.model, roles=args.specialist,
                                    max_workers=args.max_native_concurrency)
        elif args.specialist or args.max_native_concurrency != 1:
            raise ValueError('Specialists require an explicit native host and model')
        output = Path(args.output)
        checkpoint = Path(str(output) + '.sources.json') if args.requests and args.host != 'none' else None
        for path in [output, *([checkpoint] if checkpoint else [])]:
            if path.exists() or path.is_symlink(): raise ValueError('Output already exists; choose a new file')
            if not path.parent.is_dir(): raise ValueError('Output requires an existing parent directory')
        session = AuditSession(config)
        if args.resume_from:
            packet = restore_sources(saved, session)
        else:
            plan = [{**row, 'arguments': session.validate_request(row['tool'], row['arguments'])} for row in plan]
            observations = []
            for row in plan:
                try:
                    result = json.loads(session.call(row['tool'], row['arguments']))
                except AuditBudgetExceeded as error:
                    result = {'status': 'unavailable', 'reason': str(error)}
                except Exception as error:
                    result = {'status': 'unavailable', 'reason': 'source_call_failed', 'error_type': type(error).__name__}
                observations.append({**row, 'result': result})
            packet = {'run': session.status(), 'config_digest': session.digest, 'observations': observations}
            if checkpoint:
                write_private(checkpoint, dict(packet, native_status='not_started'))
        if args.host != 'none':
            try:
                packet = run_specialists(packet, session=session, host=args.host, model=args.model,
                                         roles=args.specialist, max_workers=args.max_native_concurrency)
            except (RuntimeError, ValueError):
                packet['native_status'] = 'unavailable; observations_retained'
        else: packet['native_status'] = 'not_requested'
        packet['run'] = session.status()
        write_private(output, packet)
        print(json.dumps({'output': str(output.resolve()), 'run': session.status(), 'native_status': packet['native_status']}))
    except (ValueError, TypeError, OSError, KeyError) as error:
        parser.exit(2, f'Audit failed: {type(error).__name__}\n')


if __name__ == '__main__': main()
