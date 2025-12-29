---
title: API Documentation
tags:
  - documentation
  - api
  - reference
created: 2025-12-29T10:10:00
version: 1.0.0
---

# API Documentation

Complete reference for the Obsidian MCP Server API.

## Endpoints

### Health Check

`GET /health` - Returns vault statistics and server status.

### Vault Stats

`GET /vault/stats` - Detailed vault statistics (requires authentication).

### Cache Management

`POST /cache/clear` - Clear vault cache (requires authentication).

## MCP Tools

See [[Quick Start Guide]] for basic usage.

### Available Tools

- `create_note` - Create new notes
- `update_note` - Update existing notes
- `delete_note` - Delete notes
- `search_notes` - Search by content and [[Tags]]
- `list_notes` - List all notes
- `resolve_wiki_link` - Resolve [[Wiki Links]]

## Authentication

All protected endpoints require Bearer token authentication using the `MCP_API_KEY`.

#api #reference #documentation
