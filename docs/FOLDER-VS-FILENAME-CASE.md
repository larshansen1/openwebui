# Folder vs Filename Case Handling - Explained

## Your Concern: "Won't I have the same problem with folder names?"

**Answer: Not anymore!** Here's how it works now:

## The Solution

### Directories: Always Lowercase ✅

```
Tech/Projects/ → tech/projects/
Meeting-Notes/ → meeting-notes/
ARCHIVE/2025/  → archive/2025/
```

**Why?** Cross-platform compatibility with Syncthing (Linux case-sensitive, macOS/Windows case-insensitive)

### Filenames: Preserve Original Case ✅

```
Meeting Notes.md      → Meeting Notes.md      ✅ Preserved
Ode to Claude Code.md → Ode to Claude Code.md ✅ Preserved
Important Report.md   → Important Report.md   ✅ Preserved
```

**Why?** Readability and Obsidian UI conventions

## Examples

### Example 1: Create Note
**User asks Claude:**
> "Create a note called 'Project Plan' in the folder Tech/Planning"

**MCP Server:**
```
Input:  "Tech/Planning/Project Plan.md"
Output: "tech/planning/Project Plan.md"
         ↑ lowercase    ↑ preserved
```

**Result on filesystem:**
```
tech/
└── planning/
    └── Project Plan.md  ✅
```

### Example 2: Move Note
**User asks Claude:**
> "Move 'Meeting Notes' to Archive/2025/January"

**MCP Server:**
```
Input:  "Meeting Notes.md" → "Archive/2025/January/Meeting Notes.md"
Output: "meeting notes.md" → "archive/2025/january/Meeting Notes.md"
                              ↑ lowercase           ↑ preserved
```

**Result:**
```
archive/
└── 2025/
    └── january/
        └── Meeting Notes.md  ✅
```

### Example 3: Existing Vault
Your production vault:
```
vault/
├── testmappe/          ✅ lowercase folder
│   ├── Ode to Claude Code.md      ✅ capitals preserved
│   ├── Welcome.md                 ✅ capitals preserved
│   └── Very noty.md               ✅ lowercase preserved
└── velkommen/          ✅ lowercase folder
```

**When Claude creates a new note in `testmappe/`:**
```
Input:  "testmappe/New Important Note.md"
Output: "testmappe/New Important Note.md"
         ↑ already lowercase  ↑ preserved capitals
```

## Why This Approach?

### Problem: Full Lowercase
```
❌ Tech/Projects/Meeting Notes.md
   → tech/projects/meeting notes.md
     └─ filename hard to read
```

### Solution: Directories Only
```
✅ Tech/Projects/Meeting Notes.md
   → tech/projects/Meeting Notes.md
     ↑ compatible    ↑ readable
```

## Your Vault Structure

Based on what you showed:

**Before (manual fix):**
```
vault/
├── Testmappe/    ❌ Capital T causes sync issues
├── Velkommen/    ❌ Capital V causes sync issues
└── tech/         ✅ Already lowercase
```

**After (manual fix):**
```
vault/
├── testmappe/    ✅ Lowercase
├── velkommen/    ✅ Lowercase
└── tech/         ✅ Lowercase
```

**Files inside keep their case:**
```
testmappe/
├── Ode to Claude Code.md    ✅ Capitals preserved
├── Welcome.md                ✅ Capitals preserved
└── Very noty.md              ✅ Original case kept
```

## What the MCP Server Does

### When Creating Notes

**Scenario 1: Root level**
```
Input:  "My New Note.md"
Output: "My New Note.md"  (no directories to normalize)
```

**Scenario 2: In subdirectories**
```
Input:  "Tech/Obsidian/Setup Guide.md"
Output: "tech/obsidian/Setup Guide.md"
```

### When Moving Notes

**Scenario: Move to new folder**
```
Input:  old="test.md", new="Projects/Archive/Test.md"
Output: "projects/archive/Test.md"
```

## Test Results

```bash
✅ Input:  "Projects/Archive/Important Document.md"
   Output: "projects/archive/Important Document.md"

✅ Input:  "Tech/2025/January/Meeting Notes.md"
   Output: "tech/2025/january/Meeting Notes.md"

✅ Input:  "ARCHIVE/OLD/Notes.md"
   Output: "archive/old/Notes.md"
```

## Syncthing Compatibility

### ✅ No Conflicts

**Before:**
```
Production: Tech/           (capital T)
Local:      tech/           (lowercase)
Result:     ❌ Conflict - won't sync
```

**After:**
```
Production: tech/           (lowercase)
Local:      tech/           (lowercase)
Result:     ✅ Syncs perfectly
```

### ✅ Filename Case Doesn't Matter

Filenames can have any case - they're treated the same on macOS/Windows/Linux:
```
Meeting Notes.md    ✅ Works everywhere
meeting notes.md    ✅ Works everywhere
MEETING NOTES.md    ✅ Works everywhere
```

**Why?** Even on Linux, filenames with different cases don't conflict:
- `vault/Meeting Notes.md` ← unique filename
- `vault/MEETING NOTES.md` ← different filename (both can exist)

But **directories** must match exactly on Linux:
- `vault/Tech/` ≠ `vault/tech/` ← conflict!

## Configuration

The setting controls **directory normalization only**:

```bash
# .env file
NORMALIZE_PATHS_LOWERCASE=true   # Lowercase directories, preserve filenames
```

**What it does:**
- ✅ Lowercases: `Tech/Projects/` → `tech/projects/`
- ✅ Preserves: `Meeting Notes.md` → `Meeting Notes.md`

## Script Usage

### Fixed Script for Production

```bash
# On production server
cd ~/docker/openwebui
./scripts/fix-case-sensitivity.sh ~/docker/syncthing/vault
```

The script now:
- ✅ Accepts full path (not just `/vault`)
- ✅ Auto-detects common locations
- ✅ Only renames directories
- ✅ Preserves all filenames

## Summary

| Item | Normalization | Reason |
|------|---------------|--------|
| **Directories** | Lowercase | Cross-platform compatibility |
| **Filenames** | Preserved | Readability & Obsidian conventions |

**Your manual fix was correct!** You lowercased the folder names:
- ✅ `Testmappe` → `testmappe`
- ✅ `Velkommen` → `velkommen`

And all files inside keep their original case:
- ✅ `Ode to Claude Code.md` (preserved)
- ✅ `Welcome.md` (preserved)

**Going forward, the MCP server will automatically:**
- ✅ Create lowercase directories
- ✅ Preserve filename case
- ✅ Prevent Syncthing conflicts
