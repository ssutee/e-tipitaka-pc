# Project Overview

E-Tipitaka is a desktop application for reading the Thai Tipitaka (พระไตรปิฎก).
Built with Python 3.12 and wxPython 4.2; dependencies are managed with `uv`
(`pyproject.toml`). The UI follows a Model–View–Presenter–Interactor split
(see `read/` and `search/`).

## Running and Testing

- Run from source (macOS): `uv run --python /opt/homebrew/bin/python3.12 python run.py`
  — `uv`'s standalone Python segfaults wxPython on macOS, so the Homebrew
  framework Python is required.
- Entry point: `run.py`.
- Tests: `uv run --python /opt/homebrew/bin/python3.12 python test.py` (unittest).

## Context Navigation (Graphify)

### 3-Layer Query Rule
1. **First:** query `graphify-out/graph.json` or `graphify-out/wiki/index.md`
   to understand code structure and connections
2. **Second:** query the Obsidian vault for decisions, progress, and project context
3. **Third:** only read raw code files when editing
   or when the first two layers don't have the answer

### When to rebuild the graph
- After structural changes (new modules, major refactors)
- Command: `graphify . --update` (only processes modified files)
- The graph is persistent — NO need to rebuild every session

### Do NOT
- Don't manually modify files inside `graphify-out/`
- Don't re-read the entire codebase if the graph already has the information


