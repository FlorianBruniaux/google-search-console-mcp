def with_meta(data: dict, tool: str, params: dict, *, sources: dict | None = None) -> dict:
    """Keep caller inputs separate from optional effective source identities."""
    meta = {"tool": tool, "params": params}
    if sources is not None:
        meta["sources"] = sources
    return {**data, "_meta": meta}
