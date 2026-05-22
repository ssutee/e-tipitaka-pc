# Theme — Apply to All Components

Date: 2026-05-22

## Problem

The "change theme" function currently recolors only the body text view.
The rest of each window — toolbars, navigation bars, surrounding panels,
frame background, child controls — keeps default colours, so switching to
the light-brown theme leaves the UI visually inconsistent.

## Goal

Extend the existing theme so it applies to **every component** of both the
Read view and the Search view.

## Scope decisions

- **Views covered:** Read view and Search view, every panel.
- **Depth:** every widget that is a descendant of the Read or Search frame
  — panels, toolbars, navigation bars, embedded note panels, and individual
  controls (buttons, combo boxes, list controls). Separate top-level windows
  (dictionary windows, standalone dialogs) are *not* reached by the recursive
  walk and are out of scope for this change.
- **Theme state:** kept per-view separate. Read uses the `READ` prefix
  (`read_theme.cfg`), Search uses the `SEARCH` prefix (`search_theme.cfg`).
  Each view has its own theme combo box; they are not synced.
- **Theme count:** unchanged — 2 themes (white, light-brown). No dark theme.
- **Native controls:** best-effort. On macOS native `wx.Button` /
  `wx.ComboBox` ignore `SetBackgroundColour`; those are accepted as-is.
  No widget swaps.

## Approach

Recursive widget-tree walk. A single helper recurses every `wx.Window`
under a given top window and applies the theme background/foreground
colours, with type-specific handling for a few widget classes.

Chosen over an explicit per-component list (tedious, new widgets silently
missed) and themed base classes (large refactor, overkill for 2 static
themes).

## Components

### 1. `utils.ApplyTheme` helper (`utils.py`)

```python
def ApplyTheme(window, prefix):
    bg = LoadThemeBackgroundColour(prefix)
    fg = LoadThemeForegroundColour(prefix)
    _apply(window, bg, fg)

def _apply(window, bg, fg):
    window.SetBackgroundColour(bg)
    window.SetForegroundColour(fg)
    # special-case handling — see below
    for child in window.GetChildren():
        _apply(child, bg, fg)
    window.Refresh()
```

Existing `LoadTheme`, `LoadThemeForegroundColour`, `LoadThemeBackgroundColour`
functions are reused unchanged.

### 2. Special-case widgets (inside `_apply`)

| Widget | Handling |
|---|---|
| `wx.TextCtrl` / `rt.RichTextCtrl` (read Body, note ctrl) | bg/fg, plus restyle existing text: `SetDefaultStyle` + `SetStyle(0, GetLastPosition(), attr)` so already-rendered text recolors |
| `wx.html.HtmlWindow` (`_title`/`_page`/`_item`, `ResultsWindow`, `ReferencesWindow`) | `SetBackgroundColour` for the border/scroll area; rendered HTML body colour comes from the generated `<body bgcolor>` and is covered by the existing re-render path |
| `wx.StaticBox` / `wx.StaticText` / plain `wx.Panel` | plain bg/fg via recursion default |
| `wx.Button` / `wx.ComboBox` | best-effort; native macOS may ignore, accepted |

The body restyle currently done by a manual loop in `read/presenter.py`
`SelectTheme` moves into `_apply` (via an isinstance check), so the
recursion covers it and the manual loop is dropped.

### 3. Read view wiring (`read/presenter.py` `SelectTheme`, line ~1095)

- After `utils.SaveTheme(...)`, call `utils.ApplyTheme(self._view, constants.READ)`.
- Keep the `OpenBook` / `OpenAnotherBook` re-render calls (HTML content).
- Remove the manual per-body rich-text restyle loop (now handled by `_apply`).

### 4. Search view wiring (`search/presenter.py` `SelectTheme`, line ~195)

- After `utils.SaveTheme(...)`, call `utils.ApplyTheme(self._view, constants.SEARCH)`.
- Keep the existing `ResultsWindow.SetPage(...)` re-render.

### 5. Startup application

The saved theme currently applies on launch at body level only. Add one
`utils.ApplyTheme(self, constants.READ)` call at the end of the Read view
`__init__` and `utils.ApplyTheme(self, constants.SEARCH)` at the end of the
Search view `__init__`, so the saved theme covers every component on launch.

## Data flow

```
theme combo box change
  -> interactor OnThemeComboBoxSelect
  -> presenter SelectTheme(index)
       -> utils.SaveTheme(index, prefix)
       -> utils.ApplyTheme(view_frame, prefix)   # recursive recolor
       -> existing HTML/body re-render            # content colours
```

On launch: `view.__init__` -> `utils.ApplyTheme(self, prefix)`.

## Error handling

- `LoadTheme` already defaults to theme 0 (white) when the cfg file is
  missing or unreadable — no change.
- `_apply` runs over a live widget tree; no new failure modes. Native
  controls that ignore the colour change fail silently by design.

## Testing

- **Unit:** `utils.ApplyTheme` recursion — with a `wx.App` and a small
  constructed panel/child tree, assert children receive the theme colours.
- **GUI smoke (manual):** launch the app; switch the theme combo in the
  Read view and the Search view; confirm panels, toolbars, navigation bars
  recolor; relaunch and confirm the saved theme is applied on startup.

## Out of scope

- Dark theme or any new theme.
- Syncing theme state between the two views.
- Swapping native controls for generic/owner-drawn widgets.
- Theming dialogs not spawned from the two main views.
