# raiju-dtek

DTEK power outage schedule for Kyiv, right in your terminal. Pick your street and house with fuzzy search, get today's outage intervals.

Also ships an [MCP](https://modelcontextprotocol.io) server, so AI assistants (Claude, opencode, Cursor, ...) can look up the schedule for you.

## Install

```bash
uv tool install raiju-dtek
```

On the first run `raiju` downloads Chromium via Playwright (one time, a few hundred MB).

## CLI

```bash
raiju
```

Type to filter, `Enter` to select, `Esc` to cancel.

## MCP server

The package provides a second command, `raiju-mcp`, which runs an MCP server over stdio.

Tools:

- `find_streets(query)` - find Kyiv streets by part of the name
- `get_outages(street, house)` - today's outage schedule for an address

Example question for your assistant: *"When is the power out today at Khreshchatyk 22?"*

Run `raiju` once before connecting the server, so the browser download does not happen inside your assistant and cause a timeout.

### Claude Code

```bash
claude mcp add raiju -- uvx --from raiju-dtek raiju-mcp
```

### opencode

`~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "raiju": {
      "type": "local",
      "command": ["uvx", "--from", "raiju-dtek", "raiju-mcp"]
    }
  }
}
```

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "raiju": {
      "command": "uvx",
      "args": ["--from", "raiju-dtek", "raiju-mcp"]
    }
  }
}
```

## Requirements

- Python 3.13+
- Chromium via Playwright, downloaded automatically (used to pass the DTEK site protection). On Linux you may also need Chromium's system libraries, see the Playwright docs.

## License

MIT
