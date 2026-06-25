import sys

if sys.version_info < (3, 11):
    raise RuntimeError("gsc-mcp requires Python 3.11+")

from mcp.server.fastmcp import FastMCP

from gsc_mcp.registry import TOOLS

mcp = FastMCP("gsc-mcp")

for fn in TOOLS.values():
    mcp.tool()(fn)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
