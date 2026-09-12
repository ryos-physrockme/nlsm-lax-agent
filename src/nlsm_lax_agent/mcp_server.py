"""An optional stdio MCP server; importing the physics library needs no MCP."""

from typing import Any

from .tools import REGISTRY, call_tool, list_tools


def create_server(*, timeout_seconds=30.0, memory_mb=None):
    from mcp.server.fastmcp import FastMCP
    server = FastMCP("nlsm-lax-agent")

    @server.tool()
    def available_calculations() -> list[dict]:
        """Return exact argument schemas and descriptions for all registered calculations."""
        return list_tools()

    def wrap(tool_name):
        def calculate(arguments: dict[str, Any]) -> dict[str, Any]:
            return call_tool(tool_name, arguments, timeout_seconds=timeout_seconds, memory_mb=memory_mb)
        return calculate

    for tool in REGISTRY.values():
        server.add_tool(wrap(tool.name), name=tool.name,
                        description=tool.description+" Pass arguments matching available_calculations().")
    return server


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Serve exact PCM tools over MCP stdio.")
    parser.add_argument("--tool-seconds", type=float, default=30.0)
    parser.add_argument("--memory-mb", type=int)
    args = parser.parse_args()
    create_server(timeout_seconds=args.tool_seconds, memory_mb=args.memory_mb).run(transport="stdio")


if __name__ == "__main__":
    main()
