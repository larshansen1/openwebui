---
title: Advanced Features
tags:
  - advanced
  - features
created: 2025-12-29T10:25:00
priority: high
---

# Advanced Features

Learn about advanced capabilities of the Obsidian MCP Server.

## Wiki Link Resolution

The server automatically resolves [[File Watcher|wiki-links]] including:

- Case-insensitive matching
- Alias support: `[[note name|display text]]`
- Section links: `[[note#section]]`
- Relative paths from subdirectories

## Cache Strategy

- LRU (Least Recently Used) eviction
- Configurable TTL per entry type
- Thread-safe concurrent access
- Pattern-based invalidation

## Security Features

- Path traversal protection
- Symlink attack prevention
- Constant-time API key comparison
- Sanitized error messages

See [[../API Documentation]] for API details.

#advanced #security #performance
