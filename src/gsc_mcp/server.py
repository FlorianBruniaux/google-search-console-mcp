import sys
from functools import wraps

if sys.version_info < (3, 11):
    raise RuntimeError("gsc-mcp requires Python 3.11+")

from mcp.server.fastmcp import FastMCP

from gsc_mcp.registry import TOOLS
from gsc_mcp.tool_selection import select_tools
from gsc_mcp.tools.properties import _capabilities_for

# Resolve once so discovery and capabilities describe the same startup surface.
MCP_TOOLS, TOOL_SELECTION = select_tools(TOOLS)
mcp = FastMCP("gsc-mcp")


@wraps(TOOLS["get_capabilities"])
def _configured_capabilities() -> str:
    return _capabilities_for(list(MCP_TOOLS), TOOL_SELECTION)


for name, fn in MCP_TOOLS.items():
    mcp.tool()(_configured_capabilities if name == "get_capabilities" else fn)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
