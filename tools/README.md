# tools/

Tool implementations registered with the Tool Runtime — see [`docs/architecture/06-tool-architecture.md`](../docs/architecture/06-tool-architecture.md) for the full catalogue, permission model, and common contract (typed I/O, timeouts, retries, citation verification).

Every tool here is invoked through the extracted OpenHands sandbox (`openhands/app_server/sandbox`) or the MCP host (`openhands/app_server/mcp`) — never called directly by an agent bypassing the Tool Runtime's permission check. New tools are added as MCP servers under `mcp_servers/` wherever practical (§6.5).

The `search/` tool carries a mandatory, non-optional control: query sanitization before any external call (§6.6, ACCB Mandatory Change 1) — this is a launch precondition for the Market Agent, not a follow-on hardening task.
