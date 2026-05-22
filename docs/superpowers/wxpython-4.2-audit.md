# wxPython 4.0 → 4.2 API Audit

## Purpose

This document inventories every wxPython API used in the UI modules of
E-Tipitaka-PC and classifies each against the **installed wxPython 4.2.5**.
It is the authoritative fix-list for Task 7 (Port UI modules).

## Scope

Modules audited:
- `read/view.py`
- `read/presenter.py`
- `search/view.py`
- `search/presenter.py`
- `dialogs/__init__.py`
- `widgets/__init__.py`

## How status was determined

Every status claim below was verified by direct introspection of the
installed wxPython 4.2.5 using `uv run python -c "import wx; ..."`.
Where an API existed but emitted a `wxPyDeprecationWarning` or
`DeprecationWarning`, it is marked **DEPRECATED**.  Where introspection
confirmed the API is present and produces no warnings, it is **OK**.

---

## API Status Table

### High-risk APIs

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `wx.NewId()` | `widgets/__init__.py:507`, `widgets/__init__.py:509` | **DEPRECATED** — emits `DeprecationWarning: NewId() is deprecated` | Replace `wx.NewId()` with `wx.ID_ANY` (preferred when the id is passed directly to a widget constructor, as is the case here). `wx.NewIdRef()` is the alternative but returns a `WindowIDRef` object, not a plain `int`, which can cause subtle issues. Since both ids (`lpID`, `tID`) are used as positional constructor args, use `wx.ID_ANY`. |
| `wx.Window.SetToolTipString(str)` | `widgets/__init__.py` (zero occurrences — not used) | **DEPRECATED in 4.2.5** (emits `wxPyDeprecationWarning: Use SetToolTip instead`) | Not present in these files; no action required. |
| `obj.SetToolTip(wx.ToolTip('...'))` | `widgets/__init__.py:480,1044,1048,1052,1056,1060,1064,1068,1072,1076,1080,1106,1109,1112,1253,1258,1263,1268,1273,1278,1283,1289,1295,1300,1624,1627,1630,1633,1636,1639,1642,1645,1648,1651,1654,1657,1958,1971,1975,1979,1984,1989,1992,1996,2000,2004,2008` | **OK** — `SetToolTip(wx.ToolTip(...))` is accepted without warnings. `SetToolTip(str)` also works in 4.2.5 (plain string overload). Current code using the `wx.ToolTip` wrapper is fine. | No change required. |
| `wx.lib.pubsub` | Not used anywhere in the project | **DEPRECATED** (present in 4.2.5 but emits `wxPyDeprecationWarning`; will be removed in a future version) | No action needed — not used. If added in future, use standalone `pypubsub` package (`from pubsub import pub`) and add `pypubsub` to `pyproject.toml`. |

### ToolBar APIs

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `wx.ToolBar.AddTool(...)` | Not directly called in audited files | **OK** — all three overloads present. Current signature: `AddTool(toolId, label, bitmap, shortHelp='', kind=ITEM_NORMAL)` or `AddTool(toolId, label, bitmap, bmpDisabled, kind, shortHelp, longHelp, clientData)` | No change needed. |
| `wx.ToolBar.AddLabelTool(...)` | Not called in audited files | **DEPRECATED** — emits `wxPyDeprecationWarning: Use AddTool instead` | Not used; no action. |
| `wx.ToolBar.AddSimpleTool(...)` | Not called in audited files | Present but deprecated | Not used; no action. |

### Legacy wx aliases

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `wx.EmptyBitmap` | Not used in audited files | **OK** (present, no removal) | No action. |
| `wx.EmptyImage` | Not used in audited files | **OK** | No action. |
| `wx.EmptyString` | Not used in audited files | **OK** | No action. |
| `wx.BitmapFromImage` | Not used in audited files | **OK** | No action. |
| `wx.ImageFromBitmap` | Not used in audited files | **OK** | No action. |
| `wx.StockCursor` | Not used in audited files | **OK** | No action. |

### AUI (Advanced User Interface)

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `import wx.aui as aui` (with fallback to `wx.lib.agw.aui`) | `widgets/__init__.py:6-8` | **OK** — `wx.aui` (C extension, `wx._aui`) imports successfully in 4.2.5 on all platforms tested; the `try/except` fallback to `wx.lib.agw.aui` is never triggered on this platform but is harmless. Both modules exist. | No change required. |
| `aui.AuiMDIChildFrame` | `widgets/__init__.py:780` | **OK** — present in both `wx.aui` and `wx.lib.agw.aui` | No action. |
| `aui.AuiManager(self, flags=auiFlags)` | `widgets/__init__.py:789` | **OK** — constructor signature is `AuiManager(managed_wnd=None, flags=AUI_MGR_DEFAULT)` | No change needed for the constructor call itself. |
| `aui.AuiManager(self)` (duplicate, line 790) | `widgets/__init__.py:790` | **LOGIC BUG** — line 789 creates `AuiManager` with custom `auiFlags`, then line 790 immediately overwrites `self._mgr` with a new `AuiManager(self)` using default flags. The GTK transparency-hint adjustment on lines 786-788 is discarded. | **Fix in Task 7**: Delete line 790 (`self._mgr = aui.AuiManager(self)`). |
| `aui.AUI_MGR_DEFAULT`, `aui.AUI_MGR_TRANSPARENT_HINT`, `aui.AUI_MGR_VENETIAN_BLINDS_HINT` | `widgets/__init__.py:785-788` | **OK** — all constants present in `wx.aui` 4.2.5 | No action. |
| `aui.AuiPaneInfo()` and chained calls (`.Center()`, `.Name()`, `.Dockable()`, `.CloseButton()`, `.CaptionVisible()`) | `widgets/__init__.py:814-816` | **OK** — all `AuiPaneInfo` methods present in 4.2.5 | No action. |
| `self._mgr.SavePerspective()`, `self._mgr.LoadPerspective()`, `self._mgr.UnInit()`, `self._mgr.AddPane()`, `self._mgr.Update()`, `self._mgr.GetPane()` | `widgets/__init__.py:801-824` | **OK** — all `AuiManager` methods present | No action. |

### wx.richtext

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `import wx.richtext as rt` | `read/presenter.py:4`, `search/presenter.py:7`, `dialogs/__init__.py:5`, `widgets/__init__.py:13` | **OK** | No action. |
| `rt.RichTextCtrl`, `rt.RichTextAttr`, `rt.RichTextBuffer` | Multiple locations | **OK** | No action. |
| `wx.TEXT_ATTR_TEXT_COLOUR`, `wx.TEXT_ATTR_FONT`, `wx.TEXT_ATTR_LEFT_INDENT` | Used in presenter/widget | **OK** | No action. |
| `wx.TEXT_ALIGNMENT_LEFT`, `wx.TEXT_ALIGNMENT_CENTRE`, `wx.TEXT_ALIGNMENT_RIGHT` | Used in presenter/widget | **OK** | No action. |
| `from wx.html import HtmlEasyPrinting` | `read/presenter.py:5` | **OK** | No action. |

### wx.html

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `import wx.html` | `widgets/__init__.py:11` | **OK** | No action. |
| `wx.html.HtmlWindow` | `widgets/__init__.py:1221,1224,1226,2019,2055`, `read/view.py:521,538,555`, `read/presenter.py:602` | **OK** | No action. |
| `wx.html.HW_SCROLLBAR_NEVER` | `widgets/__init__.py:1221,1224,1226` | **OK** | No action. |

### wx.grid

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `import wx.grid` | `widgets/__init__.py:15` | **OK** | No action. |
| `wx.grid.Grid`, `wx.grid.GridTableBase` | `widgets/__init__.py:34,54` | **OK** | No action. |
| `wx.grid.GRID_VALUE_STRING` | `widgets/__init__.py:101` | **OK** | No action. |
| `wx.grid.EVT_GRID_CELL_LEFT_DCLICK` | `widgets/__init__.py:48` | **OK** | No action. |

### wx.lib third-party modules

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `import wx.lib.buttons as buttons` | `widgets/__init__.py:10` **and** `widgets/__init__.py:14` (duplicate) | **OK** (but duplicated) | **Fix in Task 7**: Remove the duplicate import at line 14. |
| `buttons.GenBitmapTextButton` | `widgets/__init__.py:1935` | **OK** | No action. |
| `from wx.lib.combotreebox import ComboTreeBox` | `dialogs/__init__.py:4` | **OK** | No action. |
| `from wx.lib.splitter import MultiSplitterWindow` | `widgets/__init__.py` | **OK** | No action. |

### wx.PyAssertionError

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `wx.PyAssertionError` | `widgets/__init__.py:564,573` | **OK** — present in 4.2.5 (class name internally is `wxAssertionError`, subclasses `AssertionError`). No deprecation warning emitted. | No action required. |

### wx.PySimpleApp

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `wx.PySimpleApp` | Not used in audited files (only `wx.App` subclass in `run.py`) | **OK** (present, no deprecation warning) | No action in UI modules. |

### Font construction

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `wx.Font(size, wx.DEFAULT, wx.NORMAL, wx.NORMAL)` | `search/view.py:172`, `dialogs/__init__.py:174,299,428,451,974`, `widgets/__init__.py:561,566,574,636,660,866,1216,1917` | **OK** — `wx.DEFAULT`, `wx.NORMAL` constants are present in 4.2.5 with no deprecation warnings. The old 5-argument positional font constructor is still accepted. | No action required. However, Task 7 may optionally migrate to the modern `wx.Font(wx.FontInfo(size).FaceName(...))` style for clarity. |

### Clipboard API

| API | Used in (file:line) | 4.2.5 status | Required fix |
|-----|---------------------|--------------|--------------|
| `wx.TheClipboard.Open()` / `.SetData()` / `.Close()` | `read/presenter.py:607-609`, `read/view.py:524-526` | **OK** — `wx.TheClipboard` is a lazily-initialized proxy; `.Open()`, `.SetData()`, `.Close()` all work correctly in 4.2.5. | No action. |
| `wx.TextDataObject` | Same locations | **OK** | No action. |

### Miscellaneous constants and events

All of the following were verified present in wxPython 4.2.5 with no
deprecation warnings:

`wx.ALIGN_*`, `wx.ALL`, `wx.ART_*`, `wx.ArtProvider.GetBitmap`,
`wx.BITMAP_TYPE_*`, `wx.BoxSizer`, `wx.Button`, `wx.BitmapButton`,
`wx.CAPTION`, `wx.CB_DROPDOWN`, `wx.CB_READONLY`, `wx.CheckBox`,
`wx.CheckListBox`, `wx.Colour`, `wx.ColourData`, `wx.ColourDialog`,
`wx.ComboBox`, `wx.CommandEvent`, `wx.Config`, `wx.DD_*`, `wx.Dialog`,
`wx.DirDialog`, `wx.EVT_BUTTON`, `wx.EVT_CHAR`, `wx.EVT_CHECKBOX`,
`wx.EVT_CHECKLISTBOX`, `wx.EVT_CLOSE`, `wx.EVT_CONTEXT_MENU`,
`wx.EVT_FIND*`, `wx.EVT_KILL_FOCUS`, `wx.EVT_LEFT_*`, `wx.EVT_LISTBOX*`,
`wx.EVT_LIST_ITEM_SELECTED`, `wx.EVT_MENU*`, `wx.EVT_MOTION`,
`wx.EVT_RIGHT_DOWN`, `wx.EVT_SET_FOCUS`, `wx.EVT_SLIDER`, `wx.EVT_SPIN`,
`wx.EVT_TEXT*`, `wx.EVT_UPDATE_UI`, `wx.EXPAND`, `wx.FD_*`,
`wx.FONTWEIGHT_BOLD`, `wx.FR_NOMATCHCASE`, `wx.FR_NOWHOLEWORD`,
`wx.FileDialog`, `wx.FindReplaceData`, `wx.FindReplaceDialog`,
`wx.Font`, `wx.FontData`, `wx.FontDialog`, `wx.FontEnumerator`,
`wx.Frame`, `wx.GetApp`, `wx.GetDisplaySize`, `wx.GridBagSizer`,
`wx.HORIZONTAL`, `wx.HSCROLL`, `wx.ICON_*`, `wx.ID_*`, `wx.IconBundle`,
`wx.Image`, `wx.ImageList`, `wx.LB_*`, `wx.LC_*`, `wx.LIGHT_GREY`,
`wx.ListBox`, `wx.ListCtrl`, `wx.Menu`, `wx.MenuItem`, `wx.MessageBox`,
`wx.MessageDialog`, `wx.NO_BORDER`, `wx.BORDER_NONE`, `wx.NullColour`,
`wx.Panel`, `wx.Platform`, `wx.PlatformInfo`, `wx.Port`,
`wx.RESIZE_BORDER`, `wx.RadioBox`, `wx.SHAPED`, `wx.SL_*`,
`wx.STAY_ON_TOP`, `wx.SYS_COLOUR_WINDOW`, `wx.SearchCtrl`,
`wx.SingleChoiceDialog`, `wx.Slider`, `wx.SpinButton`,
`wx.SplitterWindow`, `wx.StaticBox`, `wx.StaticBoxSizer`, `wx.StaticText`,
`wx.SystemSettings.GetColour`, `wx.TAB_TRAVERSAL`, `wx.TE_*`,
`wx.TEXT_ALIGNMENT_*`, `wx.TEXT_ATTR_*`, `wx.TextAttr`, `wx.TextCtrl`,
`wx.TextEntryDialog`, `wx.ToolTip`, `wx.TR_*`,
`wx.TreeCtrl`, `wx.TreeEvent`, `wx.TreeItemIcon_*`, `wx.VERTICAL`,
`wx.VSCROLL`, `wx.Validator`, `wx.WXK_LEFT`, `wx.WXK_RIGHT`,
`wx.YES_NO`, `wx.__version__`.

---

## Python 3 cross-cutting issues found in UI modules

These are not wxPython API changes but are Python 3 bugs discovered during
the audit that Task 7 must also fix:

| Issue | Location | Description | Fix |
|-------|----------|-------------|-----|
| Float division in `size` argument | `widgets/__init__.py:1215`, `widgets/__init__.py:1221` | `58/divider` where `divider=2.0` produces `29.0` (float) in Python 3. wxPython 4.2.5 accepts float sizes silently, so this is **not** a crash risk but produces a float where an int is expected. | Optionally change to `int(58/divider)` or `58//2` for clarity. Low priority. |
| Duplicate `import wx.lib.buttons as buttons` | `widgets/__init__.py:10` and `widgets/__init__.py:14` | Harmless but should be cleaned up. | Remove the duplicate at line 14. |

---

## Action Items for Task 7

The following are all the concrete edits Task 7 must make to the UI modules,
grouped by file.

### `widgets/__init__.py`

1. **Replace `wx.NewId()` with `wx.ID_ANY`** (2 occurrences):
   - Line 507: `lpID = wx.NewId()` → `lpID = wx.ID_ANY`
   - Line 509: `tID = wx.NewId()` → `tID = wx.ID_ANY`

   Rationale: both IDs are used as positional widget constructor arguments
   immediately after assignment; `wx.ID_ANY` is the correct replacement.

2. **Delete the duplicate `AuiManager` construction** (logic bug):
   - Line 790: delete `self._mgr = aui.AuiManager(self)`
   
   Rationale: line 789 already creates `AuiManager` with the correctly
   adjusted `auiFlags`; line 790 silently overwrites it with default flags,
   discarding the GTK transparency-hint adjustment.

3. **Remove duplicate import**:
   - Line 14: delete `import wx.lib.buttons as buttons`
   (the identical import already exists at line 10)

### No changes required in these files

- `read/view.py` — all wx APIs verified OK in 4.2.5.
- `read/presenter.py` — all wx APIs verified OK in 4.2.5.
- `search/view.py` — all wx APIs verified OK in 4.2.5.
- `search/presenter.py` — all wx APIs verified OK in 4.2.5.
- `dialogs/__init__.py` — all wx APIs verified OK in 4.2.5.

### `pyproject.toml`

No new dependencies required. `wx.lib.pubsub` is **not used** in the
codebase; if it were, `pypubsub` would need to be added to `[project.dependencies]`.

---

## Summary

- **DEPRECATED (in use):** 1 API — `wx.NewId()` in `widgets/__init__.py` (×2)
- **LOGIC BUG (pre-existing, not API-related):** 1 — duplicate `AuiManager`
  construction in `widgets/__init__.py`
- **CODE QUALITY:** 1 — duplicate `import wx.lib.buttons` in `widgets/__init__.py`
- **REMOVED APIs found:** 0
- **SIGNATURE-CHANGED APIs found:** 0 (all toolbar/AUI signatures verified compatible)
- **New dependencies needed:** 0
- **Total action items for Task 7:** 3 edits, all in `widgets/__init__.py`
