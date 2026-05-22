# Python 3 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate E-Tipitaka-PC from Python 2.7 to Python 3.12 with wxPython 4.2.x, managed by `uv`, working in an isolated git worktree.

**Architecture:** Hybrid migration. Scaffold the worktree and `uv` project first, run `2to3` as a reviewable baseline pass, then port layer-by-layer bottom-up — vendored `whoosh/` first (hardest, de-risked early), then core, data/logic, UI, entrypoint — verifying each layer before the next.

**Tech Stack:** Python 3.12, `uv`, wxPython 4.2.x, pony ORM, vendored Whoosh 1.4.1, xhtml2pdf, SQLite.

**Reference spec:** `docs/superpowers/specs/2026-05-22-python3-migration-design.md`

This is a port, not greenfield TDD. "Verify" steps run the code and observe behavior; that is the test. Commit after every task.

---

## File Structure

No new modules. Files are ported in place. Key groups:

- **Tooling:** `pyproject.toml` (new), `.python-version` (new); remove `Pipfile`, `Pipfile.lock`, `requirements.txt`.
- **Vendored:** `whoosh/` (~50 files) — ported in place.
- **Core:** `constants.py`, `utils.py`, `i18n.py`, `settings.py`, `images.py`.
- **Data/logic:** `read/model.py`, `read/interactor.py`, `search/model.py`, `search/interactor.py`, `formatters/__init__.py`, `threads/__init__.py`.
- **UI:** `read/view.py`, `read/presenter.py`, `search/view.py`, `search/presenter.py`, `dialogs/__init__.py`, `widgets/__init__.py`.
- **Entrypoint:** `run.py`, `tests/test_threads.py`.

---

## Task 1: Create worktree and uv project scaffold

**Files:**
- Create: `pyproject.toml`, `.python-version`

- [ ] **Step 1: Create the migration worktree**

From the main repo at `/Volumes/SeagateBackup/Works/watnapahpong/E-Tipitaka-PC`:

```bash
git worktree add ../E-Tipitaka-PC-py3 -b migrate/python3
cd ../E-Tipitaka-PC-py3
```

All subsequent tasks run inside `../E-Tipitaka-PC-py3`.

- [ ] **Step 2: Pin the Python version**

```bash
uv python install 3.12
uv python pin 3.12
```

Expected: `.python-version` created containing `3.12`.

- [ ] **Step 3: Initialize the uv project**

Create `pyproject.toml`:

```toml
[project]
name = "e-tipitaka"
version = "3.0.0"
description = "Thai Tipitaka reader"
requires-python = ">=3.12"
dependencies = [
    "wxPython>=4.2.1",
    "pony>=0.7.19",
    "xhtml2pdf>=0.2.16",
    "Pillow>=10.0",
    "appdirs>=1.4.4",
]

[dependency-groups]
dev = ["pylint>=3.0"]

[tool.uv]
package = false
```

`xhtml2pdf` pulls `reportlab`, `html5lib`, `pypdf` transitively. `pdfkit`,
`PyPDF2`, `numpy`, `six`, and the `py2app` toolchain are intentionally dropped
(packaging deferred; no direct imports found). Confirm in Task 8.

- [ ] **Step 4: Resolve and install the environment**

Run: `uv sync`
Expected: lockfile `uv.lock` created; `wxPython` 4.2.x wheel installs for
Python 3.12 without a source build. If wxPython has no 3.12 wheel for this
platform, stop and report — do not silently fall back to a source build.

- [ ] **Step 5: Remove the Python 2 dependency files**

```bash
git rm Pipfile Pipfile.lock requirements.txt
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .python-version uv.lock
git commit -m "build: scaffold uv project for Python 3.12"
```

---

## Task 2: Baseline automated 2to3 pass

**Files:**
- Modify: all `*.py` under `whoosh/` and the app source.

- [ ] **Step 1: Run 2to3 in preview mode**

Run: `uvx 2to3 -f all -f idioms . --exclude=graphify-out 2>&1 | tail -40`
Expected: a diff preview of mechanical changes (print, except, imports, dict
methods, `xrange`). Review for surprises.

- [ ] **Step 2: Apply 2to3 in place**

Run: `uvx 2to3 -f all -f idioms -w -n . --exclude=graphify-out`
`-w` writes changes, `-n` skips `.bak` backups (git is the backup).

- [ ] **Step 3: Delete stale Python 2 bytecode**

```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

- [ ] **Step 4: Verify the tree still parses**

Run: `uv run python -m compileall -q whoosh constants.py utils.py i18n.py settings.py read search dialogs widgets threads formatters run.py 2>&1 | tail -20`
Expected: remaining `SyntaxError`s are acceptable here — later tasks fix them.
Record the list; it scopes the manual work.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: apply 2to3 baseline pass"
```

---

## Task 3: Port the vendored whoosh/ library

**Files:**
- Modify: `whoosh/**/*.py` (~50 files).

This is the highest-effort task. Whoosh 1.4.1 predates Python 3; `2to3` handled
the syntax, but `str`/`bytes` and integer-division semantics need manual review.

- [ ] **Step 1: Compile-check the whoosh package**

Run: `uv run python -m compileall -q whoosh 2>&1`
Expected: lists remaining `SyntaxError`s. Fix each (common: leftover Py2
`print`, tuple-unpacking in function args, `<>` operator, octal literals).

- [ ] **Step 2: Fix str/bytes in the file-storage layer**

Review and fix in this order — the index format is binary:
`whoosh/filedb/structfile.py`, `filetables.py`, `filepostings.py`,
`filestore.py`, `fileindex.py`, `filereading.py`, `filewriting.py`.

Guidance: data read from / written to disk is `bytes`; text/terms are `str`.
`struct.pack/unpack` returns/consumes `bytes`. Pickle loads of Py2 data need
`encoding='latin-1'`. Replace `/` with `//` wherever an integer offset or count
is computed. Where Py2 used `unicode`, use `str`; where it used `str` for raw
bytes, use `bytes`.

- [ ] **Step 3: Fix the remaining whoosh modules**

Apply the same str/bytes and division review to `whoosh/util.py`,
`system.py`, `analysis.py`, `formats.py`, `highlight.py`, `index.py`,
`spelling.py`, `searching.py`, `reading.py`, `writing.py`, `query.py`,
`scoring.py`, and `whoosh/support/*.py`.

- [ ] **Step 4: Write a standalone whoosh smoke script**

Create `whoosh_smoke.py` (temporary, deleted in Step 7):

```python
from whoosh.spelling import SpellChecker
from whoosh.filedb.filestore import FileStorage
from whoosh.analysis import NgramTokenizer
from whoosh.highlight import highlight, HtmlFormatter, SimpleFragmenter

st = FileStorage("resources/spell_thai")
sp = SpellChecker(st)
print("thai suggestions:", sp.suggest(u"ธรรม"))

st2 = FileStorage("resources/spell_pali")
sp2 = SpellChecker(st2)
print("pali suggestions:", sp2.suggest(u"dhamma"))

tok = NgramTokenizer(2)
print("ngram ok:", [t.text for t in tok(u"ธรรม")][:3])
print("ALL WHOOSH SMOKE CHECKS PASSED")
```

- [ ] **Step 5: Run the smoke script**

Run: `uv run python whoosh_smoke.py`
Expected: prints suggestion lists and `ALL WHOOSH SMOKE CHECKS PASSED`.
If it raises (typically a `bytes`/`str` mix or a struct error), fix the named
module and re-run. Do not proceed until it passes — this proves the 2011 index
format still loads.

- [ ] **Step 6: Compile-check the whole package**

Run: `uv run python -m compileall -q whoosh`
Expected: no output (clean).

- [ ] **Step 7: Remove the smoke script and commit**

```bash
rm whoosh_smoke.py
git add whoosh
git commit -m "refactor: port vendored Whoosh to Python 3"
```

---

## Task 4: Port the core modules

**Files:**
- Modify: `constants.py`, `utils.py`, `i18n.py`, `settings.py`, `images.py`.

- [ ] **Step 1: Compile-check the core modules**

Run: `uv run python -m compileall -q constants.py utils.py i18n.py settings.py images.py 2>&1`
Fix each `SyntaxError`.

- [ ] **Step 2: Port constants.py and settings.py**

Fix any remaining Py2 idioms. Verify path handling: `os.path` results are
already `str` in Py3. Check encoding declarations are unnecessary (Py3 source
is UTF-8 by default) but harmless.

- [ ] **Step 3: Port utils.py**

`utils.py` (384 lines) has `UpdateDatabases()` called at startup. Watch for:
file `open()` calls — add explicit `encoding='utf-8'` for text, `'rb'`/`'wb'`
for binary; `unicode()` → `str()`; `basestring` → `str`; SQLite rows return
`str` not `bytes` in Py3 — remove any `.decode('utf-8')` on already-`str` data.

- [ ] **Step 4: Port i18n.py and images.py**

`i18n.py` (45 lines) — gettext API is Py3-compatible; remove `ugettext` →
`gettext`. `images.py` (511 KB) is generated base64 image data; confirm it
imports cleanly — `2to3` should have handled it.

- [ ] **Step 5: Verify imports**

Run: `uv run python -c "import constants, utils, i18n, settings, images; print('CORE IMPORTS OK')"`
Expected: `CORE IMPORTS OK`. `UpdateDatabases()` is not called by a bare
import; if an import-time error appears, fix it.

- [ ] **Step 6: Commit**

```bash
git add constants.py utils.py i18n.py settings.py images.py
git commit -m "refactor: port core modules to Python 3"
```

---

## Task 5: Port the data and logic modules

**Files:**
- Modify: `read/model.py`, `read/interactor.py`, `search/model.py`, `search/interactor.py`, `formatters/__init__.py`, `threads/__init__.py`.

- [ ] **Step 1: Compile-check**

Run: `uv run python -m compileall -q read/model.py read/interactor.py search/model.py search/interactor.py formatters/__init__.py threads/__init__.py 2>&1`
Fix each `SyntaxError`.

- [ ] **Step 2: Port the model modules**

`read/model.py` (1067 lines) and `search/model.py` (877 lines) hold pony ORM
entities and SQLite access. Watch for: `print` debug lines, `dict.iteritems` →
`.items()`, `xrange` → `range`, integer division in pagination math (`/` →
`//`), `cmp=` sort args → `key=`, and `sorted()`/`.sort()` with `cmp`.

- [ ] **Step 3: Port the whoosh-consuming search code**

`search/model.py` imports `whoosh.highlight` and `whoosh.analysis`. Confirm the
calls match the now-ported whoosh API (unchanged — same vendored version).

- [ ] **Step 4: Port threads/__init__.py**

`threads/__init__.py` (555 lines): `import Queue` → `import queue`; thread
classes are `threading`-based and Py3-compatible. Check `print` and any
`str`/`unicode` on search keywords.

- [ ] **Step 5: Port formatters and interactors**

`formatters/__init__.py` (39 lines) and the two `interactor.py` files are
small — apply the same idiom fixes.

- [ ] **Step 6: Verify imports**

Run: `uv run python -c "import threads, formatters; import read.model, read.interactor, search.model, search.interactor; print('LOGIC IMPORTS OK')"`
Expected: `LOGIC IMPORTS OK`.

- [ ] **Step 7: Commit**

```bash
git add read/model.py read/interactor.py search/model.py search/interactor.py formatters/__init__.py threads/__init__.py
git commit -m "refactor: port data and logic modules to Python 3"
```

---

## Task 6: wxPython 4.0->4.2 audit

**Files:**
- Create: `docs/superpowers/wxpython-4.2-audit.md`

- [ ] **Step 1: Inventory every wx API used**

Run: `grep -rhoE "wx\.[A-Za-z_]+(\.[A-Za-z_]+)*" read/view.py read/presenter.py search/view.py search/presenter.py dialogs/__init__.py widgets/__init__.py | sort -u`
Save the list.

- [ ] **Step 2: Classify each API against wxPython 4.2**

Create `docs/superpowers/wxpython-4.2-audit.md` with a table: `API | used in | 4.2 status | fix`. Check each against the wxPython changelog (4.1.0, 4.1.1, 4.2.0, 4.2.1). Known watch items:

- `wx.aui` vs `wx.lib.agw.aui` — both imported in `widgets/__init__.py`.
- `wx.ToolBar.AddTool` — argument signature changed.
- `wx.NewId()` — deprecated; use `wx.NewIdRef()`.
- `SetToolTipString()` — removed; use `SetToolTip()`.
- `wx.EmptyString`, `wx.EmptyBitmap` — removed.
- `wx.lib.pubsub` — removed; move to `pypubsub` or `wx.lib.newevent`.
- `wx.grid`, `wx.richtext`, `wx.html` — method renames.
- Bitmap/image constructors — some positional forms deprecated.

- [ ] **Step 3: Commit the audit**

```bash
git add docs/superpowers/wxpython-4.2-audit.md
git commit -m "docs: wxPython 4.0->4.2 API audit"
```

---

## Task 7: Port the UI modules

**Files:**
- Modify: `read/view.py`, `read/presenter.py`, `search/view.py`, `search/presenter.py`, `dialogs/__init__.py`, `widgets/__init__.py`.

- [ ] **Step 1: Compile-check**

Run: `uv run python -m compileall -q read/view.py read/presenter.py search/view.py search/presenter.py dialogs/__init__.py widgets/__init__.py 2>&1`
Fix each `SyntaxError`.

- [ ] **Step 2: Port widgets/__init__.py**

`widgets/__init__.py` (2081 lines) is the largest UI file and imports both
`wx.aui` and `wx.lib.agw.aui`. Apply every fix from the Task 6 audit table for
APIs used here.

- [ ] **Step 3: Port dialogs/__init__.py**

`dialogs/__init__.py` (1073 lines). Apply audit fixes; check `wx.grid` and
`wx.html` usage.

- [ ] **Step 4: Port the view and presenter modules**

`read/view.py`, `read/presenter.py`, `search/view.py`, `search/presenter.py`.
Apply audit fixes; `richtext` is used here. Watch integer division in layout/
font-size math.

- [ ] **Step 5: Verify imports**

Run: `uv run python -c "import widgets, dialogs; print('UI IMPORTS OK')"`
Expected: `UI IMPORTS OK`. View/presenter modules import wx subpackages at
module load — fix any `ImportError`/`AttributeError`.

- [ ] **Step 6: Commit**

```bash
git add read/view.py read/presenter.py search/view.py search/presenter.py dialogs/__init__.py widgets/__init__.py
git commit -m "refactor: port UI modules to Python 3 and wxPython 4.2"
```

---

## Task 8: Port the entrypoint and tests

**Files:**
- Modify: `run.py`, `tests/test_threads.py`.

- [ ] **Step 1: Port run.py**

`run.py` (195 lines). Check the `traceback`/`error.log` handling and any
`print` statements. Confirm `constants.DATA_PATH` directory creation works.

- [ ] **Step 2: Port tests/test_threads.py**

`import Queue as queue` → `import queue`; `import threads` is unchanged. Fix
any `u''` literals (valid in Py3, harmless) and `assertEquals` → `assertEqual`.

- [ ] **Step 3: Run the test suite**

Run: `uv run python -m pytest tests/ -v`
Expected: `test_threads.py` tests pass. If a test needs index/database fixtures
that are absent, record it and proceed — the smoke test in Task 9 is the
authoritative check.

- [ ] **Step 4: Confirm dependency trimming**

Run: `grep -rlE "import (numpy|six|pdfkit)|import PyPDF2" --include=*.py . | grep -v graphify-out`
Expected: no output. If any match appears, add that package back to
`pyproject.toml` and run `uv sync`.

- [ ] **Step 5: Commit**

```bash
git add run.py tests/test_threads.py
git commit -m "refactor: port entrypoint and tests to Python 3"
```

---

## Task 9: Full application smoke test

**Files:** none (verification only).

- [ ] **Step 1: Launch the application**

Run: `uv run python run.py`
Expected: the main window opens with no traceback in the terminal or
`error.log`. If `data_path.cfg` points at a missing path, set it to a valid
data directory first.

- [ ] **Step 2: Exercise the read view**

Open a book; navigate forward/back several pages. Text renders in Thai script
with no mojibake.

- [ ] **Step 3: Exercise search**

Run a Thai-script search and a Pali-script search. Results list populates;
highlighted fragments render. This exercises the ported Whoosh `highlight` and
`NgramTokenizer`.

- [ ] **Step 4: Exercise spell-check**

Trigger spell-check / suggestions on a misspelled query. Suggestions appear —
this exercises the ported `SpellChecker` against the 2011 index.

- [ ] **Step 5: Exercise PDF export**

Export a page to PDF. The file opens and renders correctly.

- [ ] **Step 6: Record results and commit**

If all steps pass, the migration is functionally complete. Note any deferred
issues in the commit body.

```bash
git commit --allow-empty -m "test: verify Python 3 migration smoke test passes"
```

- [ ] **Step 7: Hand off**

Migration branch `migrate/python3` is ready for review/merge. Deferred
follow-ups (per spec): update `py2app`/`pyinstaller` specs for Py3; remove
committed `*.pyc`/`__pycache__`/`.eggs` from the repo.

---

## Notes for the implementer

- **Worktree:** all work happens in `../E-Tipitaka-PC-py3` on branch `migrate/python3`.
- **str/bytes is the recurring hazard.** The app handles Thai and Pali text
  everywhere. When in doubt: disk and socket data is `bytes`, in-memory text is
  `str`, and the boundary is an explicit `.encode('utf-8')` / `.decode('utf-8')`.
- **`*.pkl` files** under `resources/` were pickled by Python 2. If a load
  fails, retry with `pickle.load(f, encoding='latin-1')`, or regenerate the
  `.pkl` from its `.json` sibling (both exist for `book_*`, `maps`, `mc_map`).
- **Do not rebuild the Whoosh index.** Porting the vendored library preserves
  the 1.x format; rebuilding is out of scope and would change the chosen path.
- Commit after every task. Keep the `2to3` baseline commit (Task 2) separate so
  manual fixes are reviewable against it.
