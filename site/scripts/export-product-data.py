#!/usr/bin/env python3
import argparse
import importlib
import inspect
import json
import os
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def require_string(mapping: dict[str, Any], key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def load_registry(source_root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(source_root.resolve()))
    try:
        registry = importlib.import_module("gsc_mcp.registry")
    finally:
        sys.path.pop(0)
    tools = getattr(registry, "TOOLS", None)
    if not isinstance(tools, dict) or not tools:
        raise ValueError("TOOLS must be a non-empty dictionary")
    return tools


def build_payload(pyproject_path: Path, source_root: Path) -> dict[str, Any]:
    document = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = document.get("project")
    if not isinstance(project, dict):
        raise ValueError("project must be a table")
    urls = project.get("urls")
    if not isinstance(urls, dict):
        raise ValueError("project.urls.Repository must be a non-empty string")

    tools = load_registry(source_root)
    from gsc_mcp.tool_selection import _MODULE_FAMILIES
    catalogue = []
    for name, fn in sorted(tools.items()):
        implementation = inspect.unwrap(fn)
        source = inspect.getsourcefile(implementation)
        if source is None:
            raise ValueError(f"No source for tool {name}")
        catalogue.append({
            "name": name,
            "family": _MODULE_FAMILIES[fn.__module__.rsplit('.', 1)[-1]],
            "description": (inspect.getdoc(fn) or name).split("\n\n", 1)[0].replace("\n", " "),
            "signature": str(inspect.signature(fn)),
            "source": "src/" + Path(source).resolve().relative_to(source_root.resolve()).as_posix(),
            "line": inspect.getsourcelines(implementation)[1],
        })
    return {
        "package": require_string(project, "name", "project.name"),
        "pythonRequires": require_string(
            project, "requires-python", "project.requires-python"
        ),
        "repository": require_string(
            urls, "Repository", "project.urls.Repository"
        ),
        "toolCount": len(tools),
        "tools": catalogue,
        "version": require_string(project, "version", "project.version"),
    }


def write_atomic(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pyproject", type=Path, default=REPO_ROOT / "pyproject.toml")
    parser.add_argument("--source-root", type=Path, default=REPO_ROOT / "src")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "site" / "src" / "generated" / "product.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_atomic(args.output, build_payload(args.pyproject, args.source_root))
    except (ImportError, OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"product data export failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
