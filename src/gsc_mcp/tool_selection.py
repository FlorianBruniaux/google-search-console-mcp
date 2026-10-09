"""Select the MCP discovery surface without changing the full CLI registry."""
import os
from collections.abc import Callable, Mapping

ENV = 'GSC_MCP_TOOL_FAMILIES'
_MODULE_FAMILIES = {
    'properties': 'core', 'analytics': 'analytics', 'search_breakdown': 'analytics',
    'traffic_reference': 'analytics', 'crawl_import': 'technical',
    'crawl_logs': 'technical',
    'crawl_snapshots': 'technical',
    'indexing_matrix': 'inspection',
    'seo': 'seo', 'change_impact': 'seo', 'inspection': 'inspection',
    'indexing': 'indexing', 'sitemaps': 'sitemaps', 'ga4': 'ga4',
    'cross': 'cross', 'search_compare': 'cross', 'crux': 'crux',
    'technical': 'technical', 'drift': 'drift', 'content': 'content',
    'editorial': 'editorial', 'rewrite': 'editorial',
    'links': 'links', 'link_targets': 'links',
    'bing_analytics': 'bing', 'bing_webmaster': 'bing',
}


def select_tools(catalogue: Mapping[str, Callable]) -> tuple[dict, dict]:
    """Resolve configured families once; callers own the returned snapshot."""
    families = {}
    for name, fn in catalogue.items():
        module = fn.__module__.rsplit('.', 1)[-1]
        if module not in _MODULE_FAMILIES:
            raise ValueError(f'{ENV}: no family declared for tool {name}')
        families[name] = _MODULE_FAMILIES[module]
    available = sorted(set(families.values()))
    raw = os.environ.get(ENV)
    if raw is None or raw.strip().lower() == 'all':
        enabled = set(available)
        mode = 'all'
    else:
        parts = [part.strip().lower() for part in raw.split(',')]
        if any(not part for part in parts):
            raise ValueError(f'{ENV}: empty family; use a comma-separated list or all')
        unknown = set(parts) - set(available)
        if unknown:
            raise ValueError(f'{ENV}: unknown families {sorted(unknown)}; available: {available}')
        enabled = set(parts) | {'core'}
        mode = 'allowlist'
    selected = {name: fn for name, fn in catalogue.items() if families[name] in enabled}
    return selected, {'mode': mode, 'families': sorted(enabled),
                      'available_families': available, 'catalogue_total': len(catalogue),
                      'scope': 'mcp_startup', 'cli_catalogue': 'all'}
