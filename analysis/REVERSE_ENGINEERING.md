# DeadlineP5 artifact analysis

## Scope and method

Inspected the supplied Windows executable and macOS bundle locally. This is a behavioral reconstruction in Python, not recovered Delphi source or a claim of binary-equivalent rendering. The user initially selected a simpler interface, then requested that the appearance match the original. The countdown renderer now follows the original visual composition.

Evidence comes from the bundled Japanese instructions, binary headers, decoded Delphi `TPF0` component streams, Delphi Unicode string constants, retained method names, and focused i386 disassembly. Neither original executable was run: this Linux environment has no Wine/macOS runtime. The REA tool was not connected, and its CLI was not installed/cached; no analysis engine was installed. The analysis below uses ordinary Python and GNU binutils and does not claim REA evidence IDs.

[original_inventory.json](original_inventory.json) records executable hashes, sizes, form file offsets, parsed properties, and relevant string constants. [selected_disassembly.txt](selected_disassembly.txt) preserves the specific static instructions supporting the countdown and defaults. `tools/inspect_original.py` reproduces the form and string inventory without executing either original.

## Target identity

| Artifact | Observed format | SHA-256 |
| --- | --- | --- |
| `deadlinep5/Windows/DeadlineP5.exe` | Native 32-bit x86 PE GUI | `46b2408ec7640e59164449173eb342d1a64006a71efc723cc9c3094a9f7ac2d1` |
| `deadlinep5/macOS/DeadlineP5.app/Contents/MacOS/DeadlineP5` | Native 32-bit i386 Mach-O | `d620186006f43e70ddb3dace5e6b87bca3e197fb89976400b1a5d3120fdb59e2` |

The macOS executable contains the compiler identifier `Embarcadero Delphi for Mac OS X compiler version 31.0 (24.0.24468.8770)`, FireMonkey types, and named application methods. Both versions embed FireMonkey forms. The macOS plist identifies `sexy.lyna.DeadlineP5`, version `1.0.0`. The Windows bundled instructions list version 1.1 and its clone/click-through fixes; an exact Windows build version was not independently established from version resources.

## Recovered behavior

| Feature | Evidence | Python implementation |
| --- | --- | --- |
| Transparent, borderless, draggable display | Both decoded `TMainForm` streams: `BorderStyle=None`, `Transparency=true`, `Fill.Color=claNull`; bundled instructions describe dragging | Frameless transparent Qt tool windows containing tilted vector lettering, numeral blocks, and a task banner |
| Always-on-top | `TMainForm.FormStyle=StayOnTop`; `StayOnTop` config key and checkbox | Per-task checkbox |
| Countdown by date, minimum zero | macOS `TMainForm.UpdateRemainDays`, virtual addresses `0x5ea7a8–0x5ea87c`: calls `Today` at `0x2ec85c`, compares deadline, stores zero if overdue, otherwise calls `DaysBetween` at `0x2ecae0` | `max(0, (deadline - date.today()).days)` |
| Periodic refresh | Both main forms contain `Timer1` wired to `Timer1Timer`; named handler calls `UpdateRemainDays` then conditionally `UpdateImage` | One-second timer checks for a changed calendar date |
| Main title and task text | `Line1Text`, `Line2Text`; decoded edit controls limit these to 7 and 15 characters | Original Japanese defaults for new tasks, 200-character editing limit, shrink to fit |
| Two subtasks | `SubText1`, `SubText2`; forms contain two subtask edits, each originally limited to 15 characters | Two optional text lines |
| Fonts, color, size | `Line1Font`, `Line2Font`, `Color`, `Scale`; corresponding font/color/scale controls | System font selectors, color picker, scale 0.25–3 |
| Click-through | `IgnoreClick` key, checkbox, Windows 1.1 instructions | Qt transparent-input flag; editable through manager/tray |
| Multiple independent tasks | Bundled instructions; `LoadForms`, `TDummyForm.miNewClick`, configuration IDs | Independent cards in a task manager |
| Clone task | Windows 1.1 bundled instructions | Independent copy with a position offset |
| Live preview, cancel rollback | Windows history plus `UpdatePreview`, `FinishPreview`, `CurrentConfig` names | Settings dialog previews a copy; cancel restores the original |
| Persistent settings | Windows instructions specify adjacent INI and no registry; macOS instructions identify defaults domain | Separate portable JSON file; no original INI/preferences migration |

Original forms: Windows configuration at file offset `0x616358`, hidden manager at `0x617350`, main display at `0x617438`; macOS main at `0x8dafcb`, hidden manager at `0x8db1b4`, configuration at `0x8db29b`. Both main forms have a design size of 600×200. Those dimensions do not establish the final runtime drawing bounds.

## Defaults recovered from macOS configuration loading

The loader preceding the `TConfig.Load` method-name marker at file offset `0x5ceb8c` supplies these fallbacks:

| Setting | Recovered default | Basis |
| --- | --- | --- |
| Deadline | Today + 240 hours = 10 calendar days | `0x5de764` calls `Today`; pushes 240; calls `IncHour` at `0x2eccc0`. The latter's body and trailing name confirm hours, not days. |
| Color | `#fe0000`, opaque | Integer `0x00fe0000`, then OR with `0xff000000` |
| Title | `納期` (deadline) | Unicode literal at file offset `0x5ce9e4` |
| Main task | `おしごとたのしいな` (work is fun) | Unicode literal at file offset `0x5cea18` |
| Fonts | `Hiragino Kaku Gothic Pro` | Unicode literal at file offset `0x5cea98` passed for both fonts |
| Click-through | False | Zero default argument at `0x5de8e3` |
| Always-on-top | True | Default argument 1 at `0x5de8fc` |
| Scale | 1.0 | IEEE single `0x3f800000` at `0x5de915` |

The Python implementation preserves the date, color, text, flags, and scale defaults for new tasks and substitutes available system fonts. Existing saved text and fonts are preserved. Original runtime menu construction, every configuration serialization detail, and the complete drawing algorithm were not decompiled.

## Rendering and platform limits

A focused second pass inspected the actual `UpdateImage` instructions and compared the composition with published original screenshots. The renderer now uses:

- The original 600-pixel base width with a 200-pixel main display height.
- Numerals spaced by 54 units from a right anchor of 538, with the original -14/-17 degree digit tilts and 120/128 vertical anchors.
- Red/selected-accent numeral plates with black numerals, an outlined heading, and the original fixed Japanese labels `まで`, `あと`, and `日`.
- A solid accent task banner with dark text, transparent surroundings, and the 40-point irregular shadow contour recovered from the macOS instructions at virtual addresses `0x5edb28–0x5ee23f` (offset by 23, 90).
- Smaller black panels for optional subtasks; these extend the window rather than clipping text.

The 40-point contour and numeric anchors are recovered static data; [drawing_disassembly.txt](drawing_disassembly.txt) retains the relevant numeric-layout and contour-offset instructions. Qt glyph metrics, title shrink-to-fit, the numeral-one fallback outline, numeral plate padding, task-banner dimensions, and the subtask panels remain reconstruction choices. This is a closer visual reconstruction, not an exact port of all FireMonkey clipping and path-union operations. Hiragino Kaku Gothic Pro is not bundled; available system fonts provide approximate glyph shapes. Selected custom fonts remain supported.

Visual reference: [original DeadlineP5 screenshot](https://i.gzn.jp/img/2016/09/27/persona5-dead-line/a06_m.png), published in [GIGAZINE's original review](https://gigazine.net/news/20160927-persona5-dead-line/). It depicts an older release and is used for visual comparison, not as code or algorithm evidence. The local supplied binary remains the source for numeric constants and the shadow contour. The author's [download page](https://lyna.space/) lists DeadlineP5 version 1.1. The reference images are not bundled with the Python application.

The manager window is an added recovery interface for environments with limited tray support. Click-through changes apply on confirmation rather than during preview. JSON settings remain separate from the original application's files.

Python rendering, settings rollback, cloning, input flag toggling, Unicode persistence, invalid-data handling, and countdown edge cases are exercised by automated tests. An X11/Xvfb test run also passed. Screenshots were rendered and inspected. Actual clicks reaching a separate underlying application, system-tray integration, desktop-compositor stacking, and Wayland/Windows/macOS operation have not been interactively verified. No sound/alarm behavior was added; the inspected instructions describe a visual countdown widget.
