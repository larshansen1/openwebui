# Syncthing Case Sensitivity Issues - Guide & Solutions

## The Problem

Syncthing is refusing to sync with error:
```
Failed to sync: remote "tech" uses different upper or lowercase characters
than local "Tech"; change the casing on either side to match the other
```

### Root Cause

**Filesystem Case Sensitivity:**
- **macOS/Windows**: Case-insensitive by default (`Tech/` = `tech/`)
- **Linux**: Case-sensitive (`Tech/` ≠ `tech/`)

**What happened:**
1. Your production vault (Linux) had `Tech/` (capital T)
2. Obsidian MCP tool created `tech/obsidian/` (lowercase)
3. On Linux, these are different directories
4. Syncthing detects mismatch and refuses to sync

## Solutions

### 🚀 Option 1: Quick Fix (Immediate)

Fix just the `Tech/` → `tech/` issue:

#### On Production Server:
```bash
# SSH into production server
cd /path/to/vault

# Rename using temp intermediate (required for case-insensitive FS)
mv Tech tech_temp
mv tech_temp tech
```

#### Using the Script:
```bash
# Run in production
./scripts/fix-tech-folder-case.sh

# Or in container
docker compose exec obsidian-mcp /app/fix-tech-folder-case.sh container
```

### 🔧 Option 2: Full Normalization (Comprehensive)

Normalize ALL directories to lowercase:

```bash
# Run the case normalization script
./scripts/fix-case-sensitivity.sh /path/to/vault
```

This script:
- ✅ Finds all directories with capital letters
- ✅ Shows a plan before executing
- ✅ Safely renames using temp names
- ✅ Handles nested directories correctly

**Before:**
```
Vault/
├── Tech/
│   └── Obsidian/
├── Projects/
│   └── Archive/
└── Notes/
```

**After:**
```
vault/
├── tech/
│   └── obsidian/
├── projects/
│   └── archive/
└── notes/
```

### 🛡️ Option 3: Prevention (Built-in)

**Enable automatic path normalization in the MCP server:**

The Obsidian MCP server now has built-in case normalization:

```bash
# In your .env file (already enabled by default):
NORMALIZE_PATHS_LOWERCASE=true
```

With this enabled:
- ✅ All new paths are automatically lowercased
- ✅ `Tech/Obsidian` → `tech/obsidian`
- ✅ `My Project/Notes` → `my project/notes`
- ✅ Works transparently for all MCP operations

**This is already active** - the MCP server will now create lowercase paths by default.

## Best Practices

### 1. **Always Use Lowercase** (Recommended)

Follow Unix conventions:
- ✅ `tech/obsidian/`
- ✅ `projects/archive/`
- ✅ `meeting-notes/`
- ❌ `Tech/Obsidian/`
- ❌ `Projects/Archive/`
- ❌ `Meeting-Notes/`

### 2. **Check Before Creating**

When manually creating folders, use lowercase:
```bash
# Good
mkdir -p tech/obsidian

# Bad
mkdir -p Tech/Obsidian
```

### 3. **Configure Syncthing Correctly**

In your Syncthing config:
```json
{
  "caseSensitiveFS": true,
  "ignoreCase": false
}
```

This makes Syncthing respect Linux case-sensitivity.

### 4. **Use the MCP Server**

Let the MCP server create folders automatically:
- ✅ Always uses lowercase (with `NORMALIZE_PATHS_LOWERCASE=true`)
- ✅ Handles path creation correctly
- ✅ No manual mistakes

## Fixing Your Current Issue

### Step 1: Stop Syncthing Temporarily
```bash
# On production server
systemctl stop syncthing@yourusername
```

### Step 2: Fix the Case Issue

Choose one:

**A) Quick fix (just Tech/):**
```bash
cd /vault
mv Tech tech_temp && mv tech_temp tech
```

**B) Full normalization (all folders):**
```bash
./scripts/fix-case-sensitivity.sh /vault
```

### Step 3: Restart Syncthing
```bash
systemctl start syncthing@yourusername
```

### Step 4: Force Rescan
```bash
# In Syncthing UI or via API
curl -X POST http://localhost:8384/rest/db/scan?folder=<folder-id>
```

### Step 5: Verify
Check Syncthing logs - should see:
```
INFO: Folder synced successfully
```

## Environment Variables

Add to your `.env` file:

```bash
# Obsidian MCP Server - Path Normalization
# Automatically converts all paths to lowercase (recommended for Linux sync)
NORMALIZE_PATHS_LOWERCASE=true

# Syncthing (if you have these)
SYNCTHING_CASE_SENSITIVE=true
SYNCTHING_IGNORE_CASE=false
```

## Testing

After applying fixes, test:

### 1. Create a Note in a Subfolder
```bash
# Using Open WebUI, ask Claude:
"Create a note called 'Test Case' in the folder 'tech/testing'"
```

**Expected result:**
- ✅ Creates: `tech/testing/Test Case.md`
- ✅ Syncs successfully to production
- ✅ No case mismatch errors

### 2. Move a Note
```bash
# Ask Claude:
"Move the note 'Test Case' to 'archive/tests/'"
```

**Expected result:**
- ✅ Moves to: `archive/tests/Test Case.md`
- ✅ Lowercase directory preserved
- ✅ Syncs successfully

### 3. Check Syncthing Logs
```bash
# Should see no warnings
docker compose logs syncthing | grep -i "case\|failed"
```

## Troubleshooting

### "Directory already exists" errors

**Cause:** Both `Tech/` and `tech/` exist on case-sensitive filesystem

**Fix:**
```bash
# Remove one (backup first!)
rsync -av Tech/ tech/  # Merge contents
rm -rf Tech            # Remove capital version
```

### Syncthing still shows conflicts

**Cause:** Syncthing cache out of date

**Fix:**
```bash
# Clear Syncthing index
rm -rf ~/.config/syncthing/index-*
systemctl restart syncthing@yourusername
```

### MCP still creating capital letters

**Cause:** `NORMALIZE_PATHS_LOWERCASE` not set or set to `false`

**Fix:**
```bash
# In .env
NORMALIZE_PATHS_LOWERCASE=true

# Rebuild container
docker compose build obsidian-mcp
docker compose up -d obsidian-mcp
```

## Summary

✅ **Immediate fix:** Rename `Tech/` → `tech/` manually
✅ **Full fix:** Run `fix-case-sensitivity.sh` script
✅ **Prevention:** Enable `NORMALIZE_PATHS_LOWERCASE=true` (already enabled)
✅ **Best practice:** Always use lowercase directory names

**The MCP server now prevents this issue automatically!**

## Scripts Provided

1. **`scripts/fix-tech-folder-case.sh`** - Quick fix for Tech/ issue
2. **`scripts/fix-case-sensitivity.sh`** - Full vault normalization
3. **Built-in normalization** - Automatic in MCP server (enabled by default)
