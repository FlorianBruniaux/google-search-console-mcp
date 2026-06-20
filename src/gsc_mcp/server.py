import sys

if sys.version_info < (3, 11):
    raise RuntimeError("gsc-mcp requires Python 3.11+")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gsc-mcp")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
