#!/usr/bin/env python3
"""Acquire an explicit read-only request plan; optionally draft/review with a native CLI."""
import argparse
import json
import os
from pathlib import Path
import sys

from gsc_mcp.audit_runtime import AuditSession, AuditBudgetExceeded
from gsc_mcp.native_audit import run_native


def load(path):
    with open(path, 'rb') as handle: raw = handle.read(2_000_001)
    if len(raw) > 2_000_000: raise ValueError('Input exceeds byte budget')
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--requests', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--host', choices=['none', 'claude', 'codex'], default='none')
    parser.add_argument('--model')
    args = parser.parse_args()
    try:
        plan = load(args.requests)
        config = load(args.config)
        if not isinstance(plan, list) or not 1 <= len(plan) <= min(config['max_tool_calls'], 100):
            raise ValueError('Invalid request count')
        for row in plan:
            if not isinstance(row, dict) or set(row) != {'tool', 'arguments'} or not isinstance(row['arguments'], dict):
                raise ValueError('Invalid request shape')
        if args.host != 'none' and not args.model:
            raise ValueError('Native model must be explicitly selected')
        output = Path(args.output)
        if output.exists(): raise ValueError('Output already exists; choose a new file')
        session = AuditSession(config)
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
        packet = {'run': session.status(), 'observations': observations}
        if args.host != 'none':
            try:
                packet['draft'] = run_native(packet, host=args.host, model=args.model)
                packet['review'] = run_native(packet, host=args.host, model=args.model, role='reviewer')
                packet['native_status'] = 'draft_and_review_returned; semantic_quality_unverified'
            except (RuntimeError, ValueError):
                packet['native_status'] = 'unavailable; observations_retained'
        else: packet['native_status'] = 'not_requested'
        encoded = json.dumps(packet, ensure_ascii=False, allow_nan=False).encode()
        if len(encoded) > 8_000_000: raise ValueError('Output exceeds byte budget')
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as handle: handle.write(encoded)
        print(json.dumps({'output': str(output.resolve()), 'run': session.status(), 'native_status': packet['native_status']}))
    except (ValueError, TypeError, OSError, KeyError) as error:
        parser.exit(2, f'Audit failed: {type(error).__name__}\n')


if __name__ == '__main__': main()
