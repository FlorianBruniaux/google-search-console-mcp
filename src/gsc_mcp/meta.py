from gsc_mcp.evidence import evidence_for


def with_meta(data: dict, tool: str, params: dict, *, sources: dict | None = None) -> dict:
    """Keep caller inputs separate from optional effective source identities."""
    meta = {"tool": tool, "params": params}
    if sources is not None:
        meta["sources"] = sources
    meta["evidence"] = evidence_for(data, tool)
    return {**data, "_meta": meta}
