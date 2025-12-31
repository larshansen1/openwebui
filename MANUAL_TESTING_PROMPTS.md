# Manual Testing Script for OpenWebUI

Use these natural language prompts to verify the Obsidian MCP fixes in OpenWebUI.

## 1. Search Verification

**Test Singular Tag:**
> "Search for notes with the tag 'architecture'."

*Expected*: Should return notes without error (supports 'tag' alias).

**Test Plural Tags:**
> "Find all notes tagged with 'architecture' and 'tech'."

*Expected*: Should return notes (supports 'tags' array).

---

## 2. Note Creation (Alias Test)

**Test creation with 'name' alias:**
> "Create a new note named 'Project Beta' with the content '# Project Beta\nInitial draft.'."

*Expected*: Should create 'Project Beta.md' (supports 'name' as alias for 'title').

---

## 3. Update Verification (Flexibility Test)

**Test Update by Title (No path needed):**
> "Update the note titled 'Project Beta'. Add the tag 'active' to the frontmatter."

*Expected*: Should resolve 'Project Beta' to 'Project Beta.md' and update it successfully.

**Test Append via Update (New Feature):**
> "Update the note titled 'Project Beta' by appending '\n- [ ] Phase 1 complete' to the content."

*Expected*: Should append content instead of overwriting (uses `append_content` flag).

**Test Update by Path Alias:**
> "Update the note at path 'Project Beta.md'. Change the content to '# Project Beta\nPhase 2 started.'."

*Expected*: Should work using 'path' parameter.

---

## 4. Reading Verification

**Test Read by Name:**
> "Read the content of the note named 'Project Beta'."

*Expected*: Should return content (supports 'name' alias).

**Test Read by Path (New Feature):**
> "Read the content of the note at path 'Project Beta.md'."

*Expected*: Should return content (supports 'path' alias).

---

## 5. Deletion Verification

**Test Delete by Title:**
> "Delete the note titled 'Project Beta'."

*Expected*: Should delete the note (resolves title to path).
