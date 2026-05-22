# E-Tipitaka-PC — Python 3 Migration Design

**Date:** 2026-05-22
**Status:** Approved design — ready for implementation plan

## Goal

Migrate E-Tipitaka-PC from Python 2.7 to Python 3.12, bump wxPython to the
latest 4.2.x, and adopt `uv` for project/dependency management. Work happens
in an isolated git worktree.

## Scope

**In scope**
- Python 2.7 → 3.12 source conversion (app code + vendored `whoosh/`).
- wxPython 4.0.7 → 4.2.x.
- `uv` project management: `pyproject.toml` replacing `Pipfile` / `requirements.txt`.
- Run-from-source verification.

**Out of scope (deferred)**
- OS packaging: `py2app` (`e-tipitaka.spec`), `pyinstaller`
  (`e-tipitaka-gtk.spec`, `run.spec`), `build_*.sh`, `package_*.sh`, `sign_app.sh`.
- Stale artifact cleanup (`*.pyc`, `__pycache__/`, `.eggs/`, `liblzma.5.dylib`).

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| Search engine | Port vendored Whoosh 1.4.1 to Py3 | Preserves the 2011 1.x index format and the `SpellChecker` API (removed in Whoosh 2.x). No index rebuild, lowest data risk. |
| Python target | 3.12 | Full wxPython 4.2.x wheels; pony/reportlab support. |
| Packaging | Deferred | Get the app running from source first; build specs in a later pass. |
| Migration strategy | Hybrid (Approach C) | `2to3` does bulk grunt work; manual layered porting owns correctness, especially `str`/`bytes`. |

## Current state

- ~16 app source files, ~9,500 lines: `run.py`, `constants.py`, `utils.py`,
  `i18n.py`, `images.py`, `settings.py`, and packages `read/`, `search/`,
  `dialogs/`, `widgets/`, `threads/`, `formatters/`, `tests/`.
- Vendored `whoosh/` 1.4.1 (~35 files), Python 2-only.
- Already on wxPython 4.0.7 (Phoenix), but 4.0→4.2 carries real API changes
  (see "wxPython 4.0→4.2 audit" below) — not a no-op.
- App imports of Whoosh are narrow: `highlight`, `HtmlFormatter`,
  `SimpleFragmenter`, `NgramTokenizer` (search/read views); `SpellChecker`,
  `FileStorage`, `open_dir` (spelling).
- Data: many SQLite databases under `resources/` via pony ORM; 2011 Whoosh
  spell index under `resources/spell_pali/` and `resources/spell_thai/`.

## Dependency mapping

| Py2 dep | Py3 plan |
|---|---|
| `wxPython==4.0.7` | `wxPython` 4.2.x |
| `pony` | `pony` (latest, Py3-compatible) |
| `xhtml2pdf` | `xhtml2pdf` (latest) — pulls `reportlab`, `html5lib`, `pypdf` transitively |
| `pdfkit` | keep only if used at runtime; otherwise drop |
| `PyPDF2==1.26.0` | drop — no direct import found; `xhtml2pdf` brings modern `pypdf` |
| `Pillow` | `Pillow` (latest) |
| `numpy`, `six` | drop — no direct import in app code |
| `py2app`, `macholib`, `altgraph`, `modulegraph` | drop from runtime deps (packaging deferred) |
| `appdirs` | keep if used; consider `platformdirs` |

Dependency usage to be confirmed during implementation before final removal.

## Migration approach (Hybrid / Approach C)

### Phase 0 — Worktree & tooling
- Create worktree `../E-Tipitaka-PC-py3` on branch `migrate/python3`.
- `uv init`; author `pyproject.toml` (`requires-python = ">=3.12"`), declare
  mapped dependencies, define a run entrypoint (`uv run python run.py`).
- Create the `uv` virtual environment; remove `Pipfile`, `Pipfile.lock`,
  `requirements.txt` once `pyproject.toml` is authoritative.

### Phase 1 — Baseline automated pass
- Run `2to3` (or `pyupgrade`) across `whoosh/` and app code as a baseline diff:
  `print` statements, `except E, e` syntax, `dict.iteritems/has_key`, `xrange`,
  old-style imports. Commit this as a separate, reviewable baseline commit.

### Phase 2 — Layered manual porting (verify each layer before the next)
1. **`whoosh/`** — port the vendored library to Py3. Verify standalone: open the
   existing 2011 index, run a query, run `SpellChecker`. De-risks the hardest
   part first.
2. **Core** — `constants.py`, `utils.py`, `i18n.py`, `settings.py`, `images.py`.
3. **Data/logic** — `read/model.py`, `search/model.py`, interactors,
   `formatters/`, `threads/`.
4. **UI** — `read/` + `search/` view & presenter, `dialogs/`, `widgets/`;
   apply the wxPython 4.0→4.2 audit below.
5. **Entrypoint** — `run.py` and `tests/`.

### wxPython 4.0→4.2 audit

4.2.x is not source-compatible with 4.0.7. Audit every wx call site against the
official wxPython changelog (4.1.0, 4.1.1, 4.2.0, 4.2.1) before assuming a file
ports cleanly. Known watch items, to be verified — not assumed:

- **`wx.aui` vs `wx.lib.agw.aui`** — `widgets/__init__.py` imports both; AUI
  behavior and pane APIs shifted across 4.1/4.2.
- **`wx.ToolBar.AddTool`** — argument signature changed; positional calls break.
- **ID helpers** — `wx.NewId()` deprecated in favor of `wx.NewIdRef()`.
- **Tooltips** — `SetToolTipString()` removed; use `SetToolTip()`.
- **Removed constants/helpers** — e.g. `wx.EmptyString`, `wx.EmptyBitmap`.
- **`wx.lib.pubsub`** — removed; if used, move to the standalone `pypubsub`
  package or `wx.lib.newevent`.
- **`wx.grid` / `wx.richtext` / `wx.html`** — method renames and signature
  changes; the app imports all three.
- **Bitmap/image constructors** — some positional forms deprecated.
- **macOS** — DPI scaling and dark-mode behavior differ on 4.2.

Deliverable: a checklist of every wx API touched, its 4.2 status, and the fix.

### Cross-cutting concerns
- `print()`, `except E as e`, `dict` view methods, `xrange`, `unicode`/`basestring`,
  true vs floor division, absolute/relative imports.
- **`str`/`bytes` boundaries** — the highest-risk area, given heavy Thai/Pali text:
  SQLite reads/writes, file I/O, Whoosh indexing/highlighting, and pickle files
  (`*.pkl`) under `resources/`.

## Verification

Manual smoke test on Python 3.12 via `uv run`:
- App launches without error.
- Open a book in the read view; navigate pages.
- Run a Thai-script search and a Pali-script search; results render.
- Trigger spell-check / suggestions.
- Export a page to PDF.

Run `tests/` (`test_threads.py`) under Py3.

## Risks

- **Whoosh port effort** — ~35 vendored files; mechanical but tedious.
- **`str`/`bytes` regressions** in Thai/Pali handling — caught only at runtime;
  the layered verification order exists to localize these.
- **`*.pkl` resources** pickled under Python 2 — may need `encoding='latin-1'`
  on load, or regeneration from their `*.json` siblings.
- **wxPython 4.0→4.2 API drift** — real, not minor. Removed/renamed methods,
  AUI changes, deprecated ID and tooltip helpers. Failures are a mix of
  import-time errors and silent runtime breakage. Mitigated by the dedicated
  audit in Phase 2 step 4.

## Out-of-scope follow-ups

- Update / recreate packaging specs (`py2app`, `pyinstaller`) for Py3.
- Repository cleanup: drop committed `*.pyc`, `__pycache__/`, `.eggs/`.
