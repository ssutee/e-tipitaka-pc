---
description: Save a session log to the Obsidian vault and commit/push the repo
---

Save the current work session to the Obsidian vault using the Obsidian MCP tools.

Steps:

1. Create a session log note at `etipitaka-pc/logs/YYYY-MM-DD-description.md` in the
   Obsidian vault (use today's date and a short kebab-case description of the session).
   Use the Obsidian MCP tools to write the note.

2. Record in the note:
   - **What was done** — concrete changes, files touched, features added/fixed
   - **Decisions made** — design or implementation choices and their rationale
   - **Pending items** — unfinished work, follow-ups, known issues

3. Add `[[wikilinks]]` to any vault notes created or modified during the session
   so the log is connected to the rest of the vault.

4. If the project directory is a git repository, run `git commit` and `git push`
   for the work done this session. Follow the repo's existing commit message style.
   If there is nothing to commit, skip this step.

Scope: this project (E-Tipitaka-PC) only.
