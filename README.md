# DeadlineP5 Python

A Python desktop reconstruction of the DeadlineP5 binaries in `deadlinep5/`, with a Persona 5 style countdown and a simple settings interface. Uses PyQt5 and local files; no server or account required.

## Run

From this directory:

```bash
python3 deadlinep5.py
```

PyQt5 is already installed in the current environment. For another machine:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python deadlinep5.py
```

This targets Python 3.9+ with a graphical desktop. On Ubuntu, an X11/Xorg session provides the most predictable positioning, always-on-top, and click-through behavior. Wayland behavior depends on the compositor. On Windows, use `python` and `.venv\Scripts\python` as appropriate.

## Use

- **New** adds an independent countdown. **Clone** copies the selected task and offsets its position.
- Drag a card with the left mouse button. Double-click it for settings, or use its right-click menu.
- Set the deadline, title, second line, two optional subtask lines, fonts, accent color, scale, always-on-top, and click-through behavior.
- Text, date, color, font, scale, and always-on-top changes preview immediately. **Cancel** restores the previous settings. Click-through takes effect on **OK** so the preview remains usable.
- Click-through cards can be edited from the control window or tray. **Unlock all** restores mouse interaction.
- The counter uses local calendar dates and updates after midnight, including after sleep. Due today and overdue both show **0**. This is a persistent visual reminder; it does not play alarms.
- Remove asks for confirmation. Removing every task leaves an empty list, including after restarting.
- The tray opens the task manager and provides New, Unlock all, and Quit actions. Closing the control window hides it when the tray is available; otherwise it minimizes. Use **Quit** to exit.

Settings are saved automatically to `deadlinep5.json` beside the Python script. Writes use atomic file replacement, malformed files are reported without overwriting them, and a lock prevents two application instances from writing the same settings file. Use a different location with:

```bash
python3 deadlinep5.py --data ~/countdowns/tasks.json
```

The JSON format is separate from the original Windows INI/macOS preferences. Existing original settings are not imported. Cards saved outside the current screens are moved back into view on startup. New tasks use the original Japanese default text and the available Noto Sans CJK JP font. Existing saved text and fonts are preserved. Japanese and Chinese task text work when the selected font supports them. Long titles and task lines shrink to fit. The countdown uses tilted accent blocks, outlined vector text, a task banner, and transparent surroundings. Optional subtasks extend the display downward. The deadline date is available in settings rather than printed beside the counter.

## Verification and analysis

```bash
python3 -m unittest discover -s tests -v
# On Linux, exercise the X11 backend in an isolated display:
QT_QPA_PLATFORM=xcb xvfb-run -a python3 -m unittest discover -s tests -v
# Repeat the original executable inventory without executing it:
python3 tools/inspect_original.py > analysis/original_inventory.json
```

See [the reverse-engineering report](analysis/REVERSE_ENGINEERING.md) for evidence, recovered defaults, and differences from the original. Rendered previews: [original-style countdown](analysis/python_countdown.png), [English tasks and subtasks](analysis/python_countdown_english.png), and [settings](analysis/python_settings.png).
