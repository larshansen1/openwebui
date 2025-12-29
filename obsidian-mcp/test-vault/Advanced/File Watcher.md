---
title: File Watcher Implementation
tags:
  - advanced
  - technical
  - file-watching
created: 2025-12-29T10:20:00
---

# File Watcher Implementation

The MCP server uses `watchdog` to monitor file system changes in real-time.

## Features

- Automatic cache invalidation on file changes
- Monitors create, modify, delete, and move events
- Thread-safe cache updates

## How It Works

When a file changes externally (e.g., edited in Obsidian), the file watcher:

1. Detects the change event
2. Invalidates relevant cache entries
3. Ensures next read gets fresh data

This ensures the MCP server always has up-to-date information about your vault.

## Related Topics

- [[../Tags]] - Tag organization
- [[Advanced Features]] - More advanced features
- [[../Welcome]] - Back to welcome page

#technical #implementation
