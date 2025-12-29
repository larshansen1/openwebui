# Case Sensitivity Issue - FIXED ✅

## Problem Summary

Syncthing was refusing to sync due to case mismatch:
```
Failed to sync: remote "tech" uses different upper or lowercase
characters than local "Tech"
```

**Root cause:**
- macOS/Windows: case-insensitive (`Tech/` = `tech/`)
- Linux: case-sensitive (`Tech/` ≠ `tech/`)
- Syncthing detected mismatch and refused to sync

## Solution Implemented

### 1. ✅ Built-in Lowercase Normalization

The Obsidian MCP server now **automatically normalizes all paths to lowercase**.

**Test results:**
```bash
Input:  "Projects/Archive/MyNote.md"
Output: "projects/archive/mynote.md" ✅
```

**Configuration:**
- Enabled by default (`NORMALIZE_PATHS_LOWERCASE=true`)
- Applies to all operations (create, move, update)
- Works transparently - no user action needed

### 2. ✅ Scripts Provided

Two scripts to fix existing case issues:

**A) Quick fix for immediate issue:**
```bash
./scripts/fix-tech-folder-case.sh
```
- Renames `Tech/` → `tech/`
- Safe for case-insensitive filesystems
- Can run in production or container

**B) Full vault normalization:**
```bash
./scripts/fix-case-sensitivity.sh /path/to/vault
```
- Normalizes ALL directories to lowercase
- Shows plan before executing
- Handles nested directories correctly

## How It Works

### Before (Without Normalization)

```
User request: "Create note in Tech/Obsidian"
    ↓
MCP Server: Creates Tech/Obsidian/ (capital T)
    ↓
Syncthing: ❌ ERROR - conflicts with existing tech/
```

### After (With Normalization) ✅

```
User request: "Create note in Tech/Obsidian"
    ↓
MCP Server: Normalizes to tech/obsidian/ (lowercase)
    ↓
Syncthing: ✅ SUCCESS - matches existing path
```

## What Changed

### Code Changes

**1. Added config setting (`app/config.py`):**
```python
normalize_paths_lowercase: bool = Field(
    default=True,
    description="Normalize directory paths to lowercase"
)
```

**2. Added normalization function (`app/vault/manager.py`):**
```python
def _normalize_path_case(self, path: str) -> str:
    """Normalize path to lowercase if configured"""
    if settings.normalize_paths_lowercase:
        return "/".join(part.lower() for part in Path(path).parts)
    return path
```

**3. Applied to all path operations:**
- ✅ `_get_safe_path()` - Used by all file operations
- ✅ `move_note()` - Returns normalized path
- ✅ `create_note()` - Creates with normalized path

### Test Results

```bash
✅ Input:  "Tech/Obsidian/Note.md"
   Output: "tech/obsidian/note.md"

✅ Input:  "Projects/2025/January.md"
   Output: "projects/2025/january.md"

✅ Input:  "Meeting-Notes/URGENT.md"
   Output: "meeting-notes/urgent.md"
```

## For Your Syncthing Issue

### Immediate Fix

**On your production server:**

```bash
# SSH to production
ssh your-server

# Navigate to vault
cd /path/to/syncthing/vault

# Fix the Tech/ folder
mv Tech tech_temp
mv tech_temp tech

# Restart Syncthing
systemctl restart syncthing@yourusername

# Force rescan
curl -X POST http://localhost:8384/rest/db/scan?folder=vault-folder-id
```

### Verification

After fixing:

1. **Check Syncthing logs:**
```bash
# Should see no more case errors
journalctl -u syncthing@yourusername -f | grep -i case
```

2. **Create test note via Open WebUI:**
```
Ask Claude: "Create a note called 'Test Case Sync' in tech/obsidian"
```

**Expected result:**
- ✅ Note created at `tech/obsidian/test case sync.md` (all lowercase)
- ✅ Syncs successfully to production
- ✅ No case mismatch errors

## Prevention

### Going Forward

With the updated MCP server, case issues are **prevented automatically**:

**User says:** "Move note to folder Tech/Projects"
**MCP creates:** `tech/projects/` ✅

**User says:** "Create folder ARCHIVE"
**MCP creates:** `archive/` ✅

**Result:**
- ✅ No case mismatches
- ✅ Cross-platform compatibility
- ✅ Syncthing works reliably

### Best Practices

1. **Let MCP handle folder creation** - Don't create folders manually
2. **Use lowercase in prompts** - Though not required, it's clearer
3. **Run normalization script** - After importing existing vaults

## Configuration

### Enable/Disable Normalization

Add to your `.env` file:

```bash
# Enable (recommended for cross-platform sync)
NORMALIZE_PATHS_LOWERCASE=true

# Disable (not recommended)
NORMALIZE_PATHS_LOWERCASE=false
```

**Default:** `true` (enabled)

### Rebuild After Config Change

```bash
docker compose build obsidian-mcp
docker compose up -d obsidian-mcp
```

## Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `app/config.py` | Added `normalize_paths_lowercase` setting | Configure normalization |
| `app/vault/manager.py` | Added `_normalize_path_case()` | Apply normalization |
| `app/vault/manager.py` | Updated `_get_safe_path()` | Use normalization |
| `app/vault/manager.py` | Updated `move_note()` | Return normalized paths |
| `scripts/fix-tech-folder-case.sh` | New script | Quick fix for Tech/ |
| `scripts/fix-case-sensitivity.sh` | New script | Full vault normalization |

## Documentation

- **Full guide:** `SYNCTHING-CASE-SENSITIVITY.md`
- **This summary:** `CASE-SENSITIVITY-FIXED.md`

## Status

✅ **FIXED** - Automatic lowercase normalization enabled by default
✅ **TESTED** - Verified with multiple test cases
✅ **DOCUMENTED** - Scripts and guides provided
✅ **DEPLOYED** - Running in container now

**Your next note creation will automatically use lowercase paths!**
