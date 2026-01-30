# Available Tools

This file documents the tools available through Claude Code.

## File Operations

| Tool | Description |
|------|-------------|
| Read | Read file contents |
| Write | Create or overwrite files |
| Edit | Make precise string replacements in files |
| Glob | Find files by glob pattern |

## Search Tools

| Tool | Description |
|------|-------------|
| Grep | Search file contents with regex |
| WebSearch | Search the web for information |
| WebFetch | Fetch and analyze web page content |

## Execution Tools

| Tool | Description |
|------|-------------|
| Bash | Execute shell commands |
| Task | Launch specialized sub-agents |

## Best Practices

1. **Always read before editing**: Use Read tool before making changes
2. **Prefer Edit over Write**: Use Edit for modifications, Write only for new files
3. **Use Glob for file discovery**: Find files by pattern instead of guessing paths
4. **Verify before destructive ops**: Always confirm before deleting or overwriting

## Limitations

- Bash commands have a 2-minute default timeout
- File reads are limited to 2000 lines by default
- Web fetches may fail for authenticated pages
