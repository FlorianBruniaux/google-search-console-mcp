from typing import Any


def with_meta(data: dict, tool: str, params: dict) -> dict:
    return {
        **data,
        "_meta": {
            "tool": tool,
            "params": params,
        },
    }
