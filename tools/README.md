# tools/

Tool implementations registered with the Tool Runtime — see [`docs/architecture/06-tool-architecture.md`](../docs/architecture/06-tool-architecture.md) for the full catalogue, permission model, and common contract (typed I/O, timeouts, retries, citation verification).

Every tool here is invoked through the extracted OpenHands sandbox (`openhands/app_server/sandbox`) or the MCP host (`openhands/app_server/mcp`) — never called directly by an agent bypassing the Tool Runtime's permission check. New tools are added as MCP servers under `mcp_servers/` wherever practical (§6.5).

**A tool never writes its own caller allow-list.** Declare the grant once in [`shared/agent_profiles/`](../shared/agent_profiles/) and derive it here:

```python
TOOL_NAME = 'ocr'
ALLOWED_CALLERS = callers_allowed_for_tool(TOOL_NAME)
```

Hand-writing a `frozenset` of caller names instead — the pattern that let an agent's declared tools and a tool's accepted callers drift apart — fails `tests/unit/mara/test_agent_profiles.py`, which walks this package and checks every `ALLOWED_CALLERS` is the registry's own object rather than a copy that happens to agree. See [`05-agent-architecture.md`](../docs/architecture/05-agent-architecture.md) §5.15.

The `search/` tool carries a mandatory, non-optional control: query sanitization before any external call (§6.6, ACCB Mandatory Change 1) — this is a launch precondition for the Market Agent, not a follow-on hardening task.
