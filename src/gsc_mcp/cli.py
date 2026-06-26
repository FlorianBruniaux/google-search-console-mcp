"""gsc-cli: shell frontend for the 47 gsc-mcp tools.

Generates all subcommands by introspecting registry.TOOLS at startup. Both the MCP
server and this CLI share the same tool functions; the CLI adds nothing and hides
nothing from the core.

Usage:
    gsc-cli list                            list all 47 commands
    gsc-cli <command> [--flag value ...]    run a tool
    gsc-cli <command> --help                show flags for a command
    gsc-cli auth login --allow-browser      interactive OAuth flow

Exit codes:
    0   success
    1   Google API error (HttpError / google.api_core.exceptions)
    2   credential/config error (RuntimeError) or invalid arguments
"""

import argparse
import inspect
import json
import os
import sys
import traceback
import types
import typing

from gsc_mcp.registry import TOOLS


# ---------------------------------------------------------------------------
# Type classification
# ---------------------------------------------------------------------------

def _type_kind(ann) -> str:
    """Return a normalised tag for a parameter type annotation.

    Tags: "str", "int", "float", "bool", "list_str", "list_dict", "unknown".
    """
    if ann is inspect.Parameter.empty or ann is str:
        return "str"
    if ann is int:
        return "int"
    if ann is float:
        return "float"
    if ann is bool:
        return "bool"
    # typing.Optional[X] == typing.Union[X, None] — old-style Optional annotation
    origin = typing.get_origin(ann)
    if origin is typing.Union:
        args = typing.get_args(ann)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            inner = non_none[0]
            if inner is str:
                return "str"
            if inner is int:
                return "int"
            if inner is float:
                return "float"
            if inner is bool:
                return "bool"
            # Optional[list[str]] or Optional[list[dict]]
            if isinstance(inner, types.GenericAlias) and inner.__origin__ is list:
                item = typing.get_args(inner)
                if item and item[0] is str:
                    return "list_str"
                if item and item[0] is dict:
                    return "list_dict"
    # Union types built with X | Y syntax (Python 3.10+)
    if isinstance(ann, types.UnionType):
        args = typing.get_args(ann)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            inner = non_none[0]
            if inner is str:
                return "str"
            if isinstance(inner, types.GenericAlias) and inner.__origin__ is list:
                item = typing.get_args(inner)
                if item and item[0] is str:
                    return "list_str"
    # Generic aliases: list[str], list[dict]
    if isinstance(ann, types.GenericAlias) and ann.__origin__ is list:
        item = typing.get_args(ann)
        if item:
            if item[0] is str:
                return "list_str"
            if item[0] is dict:
                return "list_dict"
    return "unknown"


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------

def _build_subparser(subparsers, fn) -> argparse.ArgumentParser:
    """Add a subparser for fn with one --flag per parameter (all-flags, no positionals)."""
    cmd_name = fn.__name__.replace("_", "-")
    doc = fn.__doc__ or ""
    help_text = doc.strip().splitlines()[0] if doc.strip() else ""
    sub = subparsers.add_parser(cmd_name, help=help_text)

    sig = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        hints = {}

    for pname, param in sig.parameters.items():
        ann = hints.get(pname, inspect.Parameter.empty)
        default = param.default
        required = default is inspect.Parameter.empty
        flag = f"--{pname.replace('_', '-')}"
        kind = _type_kind(ann)

        if kind == "str":
            kw: dict = {"type": str, "required": required}
            if not required:
                kw["default"] = default
        elif kind == "int":
            kw = {"type": int, "required": required}
            if not required:
                kw["default"] = default
        elif kind == "float":
            kw = {"type": float, "required": required}
            if not required:
                kw["default"] = default
        elif kind == "bool":
            # Bool params always have a default and use store_true / store_false.
            kw = {"action": "store_false" if default is True else "store_true",
                  "default": False if default is inspect.Parameter.empty else default}
        elif kind == "list_str":
            kw = {"action": "append", "required": required}
            if not required:
                kw["default"] = default
        elif kind == "list_dict":
            kw = {
                "type": str,
                "required": required,
                "metavar": "JSON",
                "help": (
                    'JSON array of dicts, e.g. \'[{"name":"step1","event":"purchase"}]\'. '
                    "Must be a valid JSON string."
                ),
            }
            if not required:
                kw["default"] = None
        else:
            print(
                f"FATAL: tool {fn.__name__!r} has unsupported annotation {ann!r} "
                f"for parameter {pname!r}. Cannot build CLI flag.",
                file=sys.stderr,
            )
            sys.exit(1)

        sub.add_argument(flag, dest=pname, **kw)

    sub.add_argument(
        "--meta",
        action="store_true",
        default=False,
        help="include _meta block in JSON output (hidden by default)",
    )
    return sub


def _build_parser() -> tuple[argparse.ArgumentParser, dict]:
    """Build the root parser with `list`, `auth`, and 47 tool subcommands."""
    parser = argparse.ArgumentParser(
        prog="gsc-cli",
        description=(
            "Shell frontend for gsc-mcp: Google Search Console, GA4, and CrUX. "
            "Run `gsc-cli list` to see all 47 available commands."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")
    subparsers.required = True

    # Utility: list
    subparsers.add_parser(
        "list",
        help="List all 47 available commands with a one-line description.",
    )

    # Utility: auth
    auth_parser = subparsers.add_parser("auth", help="Authentication utilities.")
    auth_sub = auth_parser.add_subparsers(dest="auth_command", metavar="auth_command")
    auth_sub.required = True
    login_parser = auth_sub.add_parser(
        "login",
        help="Trigger the OAuth browser flow interactively to cache credentials.",
    )
    login_parser.add_argument(
        "--allow-browser",
        action="store_true",
        default=False,
        help="Confirm you want to open a browser window for OAuth.",
    )

    # One subparser per tool function
    fn_parsers: dict[str, argparse.ArgumentParser] = {}
    for fn in TOOLS.values():
        fn_parsers[fn.__name__] = _build_subparser(subparsers, fn)

    return parser, fn_parsers


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def _call_tool(fn_name: str, namespace: argparse.Namespace, keep_meta: bool) -> int:
    """Call TOOLS[fn_name] with args from the parsed namespace. Return exit code."""
    fn = TOOLS[fn_name]
    sig = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        hints = {}

    kwargs: dict = {}
    for pname, param in sig.parameters.items():
        ann = hints.get(pname, inspect.Parameter.empty)
        value = getattr(namespace, pname, inspect.Parameter.empty)
        if value is inspect.Parameter.empty:
            continue
        kind = _type_kind(ann)
        if kind == "list_dict" and isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                print(
                    f"Error: --{pname.replace('_', '-')} is not valid JSON: {exc}",
                    file=sys.stderr,
                )
                return 2
        kwargs[pname] = value

    try:
        raw = fn(**kwargs)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        try:
            from googleapiclient.errors import HttpError
            if isinstance(exc, HttpError):
                print(f"Google API error ({exc.status_code}): {exc.reason}", file=sys.stderr)
                return 1
        except ImportError:
            pass
        try:
            import google.api_core.exceptions as _gexc
            if isinstance(exc, _gexc.GoogleAPICallError):
                print(f"Google API error: {exc}", file=sys.stderr)
                return 1
        except ImportError:
            pass
        traceback.print_exc(file=sys.stderr)
        return 1

    data = json.loads(raw)
    if not keep_meta:
        data.pop("_meta", None)
    print(json.dumps(data))
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    """Entry point for gsc-cli. Returns an int exit code."""
    args_list = list(argv) if argv is not None else sys.argv[1:]

    # Detect auth login early (before setting GSC_NO_BROWSER)
    is_auth_login = (
        len(args_list) >= 2
        and args_list[0] == "auth"
        and args_list[1] == "login"
    )
    allow_browser = "--allow-browser" in args_list

    # Block accidental OAuth browser popups in non-interactive contexts.
    # Only the explicit `auth login --allow-browser` path bypasses this.
    if not (is_auth_login and allow_browser):
        os.environ["GSC_NO_BROWSER"] = "1"

    # Build parsers — may call sys.exit(1) if an unsupported type is found
    parser, fn_parsers = _build_parser()

    # Parse args — argparse calls sys.exit(2) on missing required args or bad values
    namespace = parser.parse_args(args_list)

    cmd = namespace.command

    if cmd == "list":
        for fn_name, fn in TOOLS.items():
            cmd_display = fn_name.replace("_", "-")
            doc = fn.__doc__ or ""
            first_line = doc.strip().splitlines()[0] if doc.strip() else "(no description)"
            print(f"  {cmd_display:<35} {first_line}")
        return 0

    if cmd == "auth":
        if namespace.auth_command == "login":
            if not allow_browser:
                print(
                    "Error: `gsc-cli auth login` requires --allow-browser to confirm "
                    "you want to open a browser window.",
                    file=sys.stderr,
                )
                return 2
            # Remove the block so the OAuth flow can proceed
            os.environ.pop("GSC_NO_BROWSER", None)
            try:
                from gsc_mcp.auth import get_searchconsole_service
                get_searchconsole_service()
                print("Authentication successful. Token cached.")
                return 0
            except RuntimeError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 2
        return 2

    # Tool dispatch
    fn_name = cmd.replace("-", "_")
    keep_meta = getattr(namespace, "meta", False)
    return _call_tool(fn_name, namespace, keep_meta)
