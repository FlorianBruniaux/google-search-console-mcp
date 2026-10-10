import sys
import json
from functools import wraps

if sys.version_info < (3, 11):
    raise RuntimeError("gsc-mcp requires Python 3.11+")

from mcp.server.fastmcp import FastMCP

from gsc_mcp.registry import TOOLS
from gsc_mcp.tool_selection import select_tools
from gsc_mcp.tools.properties import _capabilities_for
from gsc_mcp.audit_runtime import session_from_environment

# Resolve once so discovery and capabilities describe the same startup surface.
MCP_TOOLS, TOOL_SELECTION = select_tools(TOOLS)
AUDIT_SESSION = session_from_environment()
if AUDIT_SESSION is not None:
    MCP_TOOLS = {name: TOOLS[name] for name in AUDIT_SESSION.config['allowed_tools']}
    TOOL_SELECTION = {**TOOL_SELECTION, 'mode': 'read_only_audit', 'run_id': AUDIT_SESSION.config['run_id']}
mcp = FastMCP("gsc-mcp")


@wraps(TOOLS["get_capabilities"])
def _configured_capabilities() -> str:
    data = json.loads(_capabilities_for(list(MCP_TOOLS), TOOL_SELECTION))
    if AUDIT_SESSION is not None:
        data['audit_run'] = AUDIT_SESSION.status()
    return json.dumps(data)


def _audit_tool(name, fn):
    @wraps(fn)
    def call(**arguments):
        return AUDIT_SESSION.call(name, arguments)
    return call


for name, fn in MCP_TOOLS.items():
    configured = _configured_capabilities if name == "get_capabilities" else (_audit_tool(name, fn) if AUDIT_SESSION is not None else fn)
    mcp.tool()(configured)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
