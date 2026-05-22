# Theme — Apply to All Components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the theme function so a theme change recolors every widget of the Read and Search views, not just the body text.

**Architecture:** A recursive helper in `utils.py` walks the widget tree from a view's frame and applies the theme background/foreground colours to every `wx.Window`, with a restyle special-case for `wx.TextCtrl`. Each view's `SelectTheme` calls it after saving; each view also calls it once on startup so a saved theme applies on launch.

**Tech Stack:** Python 3.12, wxPython 4.2, `unittest`.

---

## File Structure

- `utils.py` — add `ApplyTheme` + `_ApplyThemeRecursive` (theme-apply logic lives with the other `*Theme*` helpers).
- `read/presenter.py` — `SelectTheme` calls `ApplyTheme`; drop the manual body-restyle loop.
- `read/view.py` — `Start()` calls `ApplyTheme` once after the UI is built.
- `search/presenter.py` — `SelectTheme` calls `ApplyTheme`.
- `search/view.py` — `__init__` calls `ApplyTheme` once after the UI is built.
- `tests/test_theme.py` — new unit test file for the recursive helper.
- `test.py` — register the new test suite.

---

## Task 1: Recursive theme-apply helper in `utils.py`

**Files:**
- Create: `tests/test_theme.py`
- Modify: `utils.py` (add after `LoadThemeBackgroundColour`, around line 202)
- Modify: `test.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_theme.py`:

```python
#-*- coding:utf-8 -*-

import unittest
import wx
import utils


class TestApplyThemeRecursive(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = wx.App()

    def setUp(self):
        self.frame = wx.Frame(None)
        self.bg = wx.Colour(0xF9, 0xEF, 0xD8, 0xFF)
        self.fg = wx.Colour(0x5E, 0x49, 0x33, 0xFF)

    def tearDown(self):
        self.frame.Destroy()

    def testRecolorsTopWindow(self):
        utils._ApplyThemeRecursive(self.frame, self.bg, self.fg)
        self.assertEqual(self.bg, self.frame.GetBackgroundColour())
        self.assertEqual(self.fg, self.frame.GetForegroundColour())

    def testRecolorsNestedChildren(self):
        outer = wx.Panel(self.frame)
        inner = wx.Panel(outer)
        label = wx.StaticText(inner, label='x')
        utils._ApplyThemeRecursive(self.frame, self.bg, self.fg)
        for w in (outer, inner, label):
            self.assertEqual(self.bg, w.GetBackgroundColour())
            self.assertEqual(self.fg, w.GetForegroundColour())

    def testRecolorsTextCtrlDefaultStyle(self):
        ctrl = wx.TextCtrl(self.frame, style=wx.TE_MULTILINE)
        ctrl.SetValue('some existing text')
        utils._ApplyThemeRecursive(self.frame, self.bg, self.fg)
        attr = ctrl.GetStyle(0, wx.TextAttr())[1]
        self.assertEqual(self.bg, attr.GetBackgroundColour())
        self.assertEqual(self.fg, attr.GetTextColour())


def suite():
    s = unittest.TestSuite()
    s.addTest(TestApplyThemeRecursive('testRecolorsTopWindow'))
    s.addTest(TestApplyThemeRecursive('testRecolorsNestedChildren'))
    s.addTest(TestApplyThemeRecursive('testRecolorsTextCtrlDefaultStyle'))
    return s


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_theme -v`
Expected: FAIL — `AttributeError: module 'utils' has no attribute '_ApplyThemeRecursive'`

- [ ] **Step 3: Write the implementation**

In `utils.py`, immediately after `LoadThemeBackgroundColour` (ends at line 202), add:

```python
def _ApplyThemeRecursive(window, bg, fg):
    window.SetBackgroundColour(bg)
    window.SetForegroundColour(fg)
    if isinstance(window, wx.TextCtrl):
        attr = window.GetDefaultStyle()
        attr.SetBackgroundColour(bg)
        attr.SetTextColour(fg)
        window.SetDefaultStyle(attr)
        window.SetStyle(0, window.GetLastPosition(), attr)
    for child in window.GetChildren():
        _ApplyThemeRecursive(child, bg, fg)
    window.Refresh()

def ApplyTheme(window, prefix):
    bg = LoadThemeBackgroundColour(prefix)
    fg = LoadThemeForegroundColour(prefix)
    _ApplyThemeRecursive(window, bg, fg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_theme -v`
Expected: PASS — 3 tests OK.

- [ ] **Step 5: Register the suite in `test.py`**

Replace the contents of `test.py` with:

```python
import unittest
import tests.test_threads
import tests.test_theme

suite1 = tests.test_threads.suite()
suite2 = tests.test_theme.suite()
alltests = unittest.TestSuite([suite1, suite2])

runner = unittest.TextTestRunner()
runner.run(alltests)
```

- [ ] **Step 6: Commit**

```bash
git add utils.py tests/test_theme.py test.py
git commit -m "feat: add recursive ApplyTheme helper"
```

---

## Task 2: Wire the Read view to ApplyTheme

**Files:**
- Modify: `read/presenter.py:1095-1115` (`SelectTheme`)
- Modify: `read/view.py:603-605` (`Start`)

- [ ] **Step 1: Replace the body of `SelectTheme` in `read/presenter.py`**

Current code (lines 1095-1115):

```python
    def SelectTheme(self, theme):
        utils.SaveTheme(theme, constants.READ)
        background = utils.LoadThemeBackgroundColour(constants.READ)
        foreground = utils.LoadThemeForegroundColour(constants.READ)
        for key in [None]+list(self._compareVolume.keys()):
            code, index = utils.SplitKey(key)
            body = self._view.FocusBody(code, index)
            body.SetBackgroundColour(background)
            body.SetForegroundColour(foreground)
            # Also update the rich text style so re-rendered content uses the
            # new colours; SetBackgroundColour alone leaves the text styled
            # with the previous theme.
            attr = body.GetDefaultStyle()
            attr.SetBackgroundColour(background)
            attr.SetTextColour(foreground)
            body.SetDefaultStyle(attr)
            body.SetStyle(0, body.GetLastPosition(), attr)
            if code is None:
                self.OpenBook(self._currentVolume, self._currentPage, self._model.GetSection(self._currentVolume, self._currentPage))        
            else:
                self.OpenAnotherBook(code, index, self._compareVolume[key], self._comparePage[key])            
```

Replace with:

```python
    def SelectTheme(self, theme):
        utils.SaveTheme(theme, constants.READ)
        utils.ApplyTheme(self._view, constants.READ)
        for key in [None]+list(self._compareVolume.keys()):
            code, index = utils.SplitKey(key)
            if code is None:
                self.OpenBook(self._currentVolume, self._currentPage, self._model.GetSection(self._currentVolume, self._currentPage))
            else:
                self.OpenAnotherBook(code, index, self._compareVolume[key], self._comparePage[key])
```

The per-body restyle is now done by `ApplyTheme`'s recursion (`_ApplyThemeRecursive` handles every `wx.TextCtrl`, which the read Body is). The `OpenBook` / `OpenAnotherBook` calls remain — they re-render HTML content with the new background.

- [ ] **Step 2: Add the startup call in `read/view.py`**

Current `Start` (lines 603-610):

```python
    def Start(self):
        self._PostInit()
        self._components.Filter(self)

        if wx.__version__[:3]<='2.8':
            self.Show()
        else:
            self.Activate()
```

Change to:

```python
    def Start(self):
        self._PostInit()
        self._components.Filter(self)
        utils.ApplyTheme(self, constants.READ)

        if wx.__version__[:3]<='2.8':
            self.Show()
        else:
            self.Activate()
```

Verify `utils` and `constants` are already imported at the top of `read/view.py` (they are — used elsewhere in the file). No new import needed.

- [ ] **Step 3: Run the existing test suite**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_theme tests.test_threads -v`
Expected: PASS — no regressions (theme tests still 3 OK).

- [ ] **Step 4: Commit**

```bash
git add read/presenter.py read/view.py
git commit -m "feat: apply theme to all Read view components"
```

---

## Task 3: Wire the Search view to ApplyTheme

**Files:**
- Modify: `search/presenter.py:195-197` (`SelectTheme`)
- Modify: `search/view.py:153-154` (`__init__`, after `_CreateHistoryListPane`)

- [ ] **Step 1: Update `SelectTheme` in `search/presenter.py`**

Current code (lines 195-197):

```python
    def SelectTheme(self, index):
        utils.SaveTheme(index, constants.SEARCH)
        self._view.ResultsWindow.SetPage('<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))
```

Replace with:

```python
    def SelectTheme(self, index):
        utils.SaveTheme(index, constants.SEARCH)
        utils.ApplyTheme(self._view, constants.SEARCH)
        self._view.ResultsWindow.SetPage('<html><body bgcolor="%s"></body></html>'%(utils.LoadThemeBackgroundHex(constants.SEARCH)))
```

The `SetPage` call stays — it re-renders the HTML results pane content with the new background. `ApplyTheme` handles every other widget.

- [ ] **Step 2: Add the startup call in `search/view.py`**

In `__init__`, the last statement is `self._CreateHistoryListPane()` (line 154). Add immediately after it:

```python
        self._CreateHistoryListPane()
        utils.ApplyTheme(self, constants.SEARCH)
```

Verify `utils` and `constants` are already imported at the top of `search/view.py` (they are — `utils.LoadFont` / `utils.LoadThemeBackgroundHex` are used in `__init__`). No new import needed.

- [ ] **Step 3: Run the test suite**

Run: `uv run --python /opt/homebrew/bin/python3.12 python -m unittest tests.test_theme tests.test_threads -v`
Expected: PASS — no regressions.

- [ ] **Step 4: Commit**

```bash
git add search/presenter.py search/view.py
git commit -m "feat: apply theme to all Search view components"
```

---

## Task 4: Manual GUI verification

Not runtime-verifiable from tests — a human must confirm.

- [ ] **Step 1: Launch the app**

Run: `uv run --python /opt/homebrew/bin/python3.12 python run.py`

- [ ] **Step 2: Verify Read view theme switch**

In the Read view, change the theme combo box (สีพื้นหลัง) from ขาว to น้ำตาลอ่อน. Confirm the body text, toolbar panel, navigation panel, book-list panel, and frame background all switch to the light-brown theme. Switch back to ขาว and confirm everything returns to white.

- [ ] **Step 3: Verify Search view theme switch**

In the Search view, change its theme combo box. Confirm the results pane, top toolbar, and history panel all recolor.

- [ ] **Step 4: Verify theme persists on restart**

With the light-brown theme selected in both views, close and relaunch the app. Confirm both views open already themed light-brown (not just the body text).

- [ ] **Step 5: Note the known limitation**

On macOS, native `wx.Button` and `wx.ComboBox` backgrounds may stay default — this is expected (best-effort, per the spec). Confirm panels/text/static areas recolor; native control quirks are acceptable.

---

## Self-Review Notes

- **Spec coverage:** recursive helper (Task 1) covers spec §1; TextCtrl restyle special-case (Task 1) covers spec §2; Read wiring (Task 2) covers spec §3; Search wiring (Task 3) covers spec §4; startup calls in Tasks 2 & 3 cover spec §5; testing covered by Task 1 unit tests + Task 4 manual GUI check.
- **HtmlWindow special case:** spec §2 lists `wx.html.HtmlWindow` — handled by the generic `SetBackgroundColour` in the recursion plus the existing content re-render (`OpenBook`, `SetPage`) kept in Tasks 2 & 3. No extra code needed.
- **Out of scope confirmed:** dictionary windows and standalone dialogs are separate top-level windows, not descendants of the view frames — not reached by the walk, as intended.
