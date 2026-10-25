#!/usr/bin/env python3
"""Portable desktop countdowns reconstructed from DeadlineP5's shipped artifacts."""
import argparse
from dataclasses import asdict, dataclass, field, replace
from datetime import date, timedelta
import json
import math
from pathlib import Path
import sys

from PyQt5.QtCore import QDate, QLockFile, QPoint, QPointF, QRectF, QSaveFile, QIODevice, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QTransform
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QDateEdit, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFontComboBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMenu, QMessageBox,
    QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget,
)


@dataclass
class Task:
    deadline: str = field(default_factory=lambda: (date.today() + timedelta(days=10)).isoformat())
    line1: str = '納期'
    line2: str = 'おしごとたのしいな'
    sub1: str = ''
    sub2: str = ''
    font1: str = 'Noto Sans CJK JP'
    font2: str = 'Noto Sans CJK JP'
    color: str = '#fe0000'
    scale: float = 1.0
    ignore_click: bool = False
    stay_on_top: bool = True
    x: int = 80
    y: int = 80

    def remaining(self, today=None):
        return max(0, (date.fromisoformat(self.deadline) - (today or date.today())).days)

    @classmethod
    def from_dict(cls, values):
        if not isinstance(values, dict) or set(values) - cls.__dataclass_fields__.keys():
            raise ValueError('Unknown task settings')
        task = cls(**values)
        for name in ('deadline', 'line1', 'line2', 'sub1', 'sub2', 'font1', 'font2', 'color'):
            if not isinstance(getattr(task, name), str):
                raise ValueError(f'{name} must be text')
        if date.fromisoformat(task.deadline).isoformat() != task.deadline:
            raise ValueError('Deadline must use YYYY-MM-DD')
        if not QColor.isValidColor(task.color):
            raise ValueError('Invalid color')
        if type(task.scale) not in (int, float) or not math.isfinite(task.scale) or not 0.25 <= task.scale <= 3:
            raise ValueError('Scale must be between 0.25 and 3')
        if any(type(getattr(task, name)) is not bool for name in ('ignore_click', 'stay_on_top')):
            raise ValueError('Window options must be booleans')
        if any(type(getattr(task, name)) is not int or abs(getattr(task, name)) > 100000
               for name in ('x', 'y')):
            raise ValueError('Invalid window position')
        return task


def load_tasks(path):
    if not path.exists():
        return [Task()]
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('tasks'), list):
        raise ValueError('Expected a version 1 task file')
    return [Task.from_dict(values) for values in data['tasks']]


def save_tasks(path, tasks):
    payload = json.dumps({'version': 1, 'tasks': [asdict(task) for task in tasks]},
                         ensure_ascii=False, indent=2).encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    output = QSaveFile(str(path))
    if not output.open(QIODevice.WriteOnly):
        raise OSError(output.errorString())
    if output.write(payload) != len(payload):
        output.cancelWriting()
        raise OSError(output.errorString())
    if not output.commit():
        raise OSError(output.errorString())


def text_path(text, family, size, weight=QFont.Normal):
    font = QFont(family)
    font.setPixelSize(round(size))
    font.setWeight(weight)
    path = QPainterPath()
    path.addText(0, 0, font, text)
    bounds = path.boundingRect()
    return path.translated(-bounds.left(), -bounds.bottom())


class Card(QWidget):
    def __init__(self, manager, task):
        super().__init__()
        self.manager = manager
        self.task = task
        self.drag_offset = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle('DeadlineP5 countdown')
        self.setAccessibleName('Deadline countdown; right-click for settings')
        self.apply_settings()
        self.move(task.x, task.y)
        if not any(self.frameGeometry().intersects(s.availableGeometry())
                   for s in QApplication.screens()):
            self.move(QApplication.primaryScreen().availableGeometry().topLeft() + QPoint(80, 80))
            task.x, task.y = self.x(), self.y()

    def apply_settings(self):
        pos = self.pos()
        flags = Qt.Tool | Qt.FramelessWindowHint
        if self.task.stay_on_top:
            flags |= Qt.WindowStaysOnTopHint
        if self.task.ignore_click:
            flags |= Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
        self.setWindowFlags(flags)
        extra_lines = sum(bool(text) for text in (self.task.sub1, self.task.sub2))
        self.resize(round(600 * self.task.scale), round((200 + 34 * extra_lines) * self.task.scale))
        self.move(pos)
        self.show()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.task.scale, self.task.scale)
        p.setPen(Qt.NoPen)
        accent = QColor(self.task.color)
        shadow = QColor(0, 0, 0, 178)

        def draw_path(path, color, outline=0):
            if outline:
                p.strokePath(path, QPen(shadow, outline, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            p.fillPath(path, color)

        def lettering(text, family, size, x, y, angle=0, scale=1, weight=QFont.Normal):
            transform = QTransform().translate(x, y).rotate(angle).scale(scale, scale)
            return transform.map(text_path(text, family, size, weight))

        # Main shadow contour recovered from the macOS UpdateImage point construction.
        contour = [(5, 6), (35, 7), (58, 7), (79, 9), (152, 10), (404, 15),
                   (500, 21), (528, 22), (557, 21), (548, 52), (536, 53),
                   (530, 58), (539, 56), (539, 62), (545, 85), (519, 85),
                   (510, 84), (507, 87), (490, 87), (488, 85), (459, 83),
                   (458, 82), (452, 82), (453, 83), (439, 85), (462, 86),
                   (464, 93), (460, 94), (414, 95), (335, 97), (208, 97),
                   (41, 98), (19, 101), (16, 88), (15, 86), (17, 71),
                   (21, 69), (18, 55), (13, 51), (5, 6)]
        p.setBrush(shadow)
        p.drawPolygon(QPolygonF([QPointF(x + 23, y + 90) for x, y in contour]))

        digits = str(self.task.remaining())
        digit_scale = min(1, 270 / (54 * len(digits)))
        digit_left = 538 - 54 * len(digits) * digit_scale
        for index, digit in enumerate(digits):
            last = index == len(digits) - 1
            x = digit_left + 54 * index * digit_scale
            transform = QTransform().translate(x, 120 if last else 128)
            transform.rotate(-14 if last else -17).scale(digit_scale, digit_scale)
            plate = QPainterPath()
            plate.addRect(QRectF(-8, -94, 64, 102))
            draw_path(transform.map(plate), accent, 5)
            glyph = text_path(digit, self.task.font1, 100, QFont.Black)
            # shortcut: system fonts approximate Hiragino; use licensed originals for pixel parity.
            if digit == '1' and self.task.font1 in ('Noto Sans CJK JP', 'Sans Serif'):
                glyph = QPainterPath(QPointF(8, -63))
                glyph.cubicTo(3, -62, 1, -69, 7, -72)
                glyph.lineTo(22, -80)
                glyph.cubicTo(28, -83, 34, -79, 34, -73)
                glyph.lineTo(34, -7)
                glyph.cubicTo(34, 3, 17, 3, 17, -7)
                glyph.lineTo(17, -66)
                glyph.closeSubpath()
            bounds = glyph.boundingRect()
            width = 27 if digit == '1' else 44
            fit = QTransform().translate(3 + (44 - width) / 2, -5)
            fit.scale(width / max(1, bounds.width()), 78 / max(1, bounds.height()))
            draw_path(transform.map(fit.map(glyph)), QColor(Qt.black))

        draw_path(lettering('日', self.task.font1, 36, 550, 108, -20), accent, 3)
        label_x = digit_left - 85
        draw_path(lettering('まで', self.task.font1, 31, label_x, 91, -20), accent, 3)
        draw_path(lettering('あと', self.task.font1, 31, label_x + 15, 118, -20), accent, 3)

        paths = [text_path(char, self.task.font1, 72) for char in self.task.line1]
        title_width = sum(path.boundingRect().width() + 8 for path in paths)
        title_scale = min(1, max(1, label_x - 48) / max(1, title_width))
        x = label_x - 10 - title_width * title_scale
        for index, path in enumerate(paths):
            transform = QTransform().translate(x, 110 if index == len(paths) - 1 else 120)
            transform.rotate(-20 * title_scale**2).scale(title_scale, title_scale)
            draw_path(transform.map(path), accent, 4 * title_scale)
            x += (path.boundingRect().width() + 8) * title_scale

        p.setPen(Qt.NoPen)
        p.setBrush(accent)
        p.drawRect(QRectF(28, 137, 530, 50))
        main = text_path(self.task.line2, self.task.font2, 36)
        fit = min(1, 494 / max(1, main.boundingRect().width()))
        transform = QTransform().translate(293 - main.boundingRect().width() * fit / 2, 174)
        draw_path(transform.scale(fit, fit).map(main), QColor(Qt.black))

        for index, text in enumerate(filter(None, (self.task.sub1, self.task.sub2))):
            y = 200 + 34 * index
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 220))
            p.drawPolygon(QPolygonF([QPointF(115, y), QPointF(559, y - 3),
                                    QPointF(551, y + 29), QPointF(123, y + 27)]))
            path = text_path(text, self.task.font2, 22)
            fit = min(1, 400 / max(1, path.boundingRect().width()))
            draw_path(QTransform().translate(138, y + 21).scale(fit, fit).map(path),
                      QColor(Qt.white))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_offset)

    def mouseReleaseEvent(self, event):
        if self.drag_offset is not None:
            self.drag_offset = None
            self.task.x, self.task.y = self.x(), self.y()
            self.manager.persist()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.manager.edit_card(self)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction('Settings…', lambda: self.manager.edit_card(self))
        menu.addAction('Clone', lambda: self.manager.add_task(self.task))
        menu.addAction('New task', self.manager.add_task)
        menu.addAction('Remove task…', lambda: self.manager.confirm_remove(self))
        menu.addSeparator()
        menu.addAction('Manage tasks', self.manager.show_manager)
        menu.addAction('Quit', self.manager.quit)
        menu.exec_(event.globalPos())


class SettingsDialog(QDialog):
    def __init__(self, card):
        super().__init__(card.manager)
        self.card = card
        self.original = replace(card.task)
        self.setWindowTitle('Countdown settings — live preview')
        form = QFormLayout(self)
        self.deadline = QDateEdit(QDate.fromString(card.task.deadline, 'yyyy-MM-dd'))
        self.deadline.setDisplayFormat('yyyy-MM-dd')
        self.deadline.setCalendarPopup(True)
        form.addRow('Deadline', self.deadline)
        self.deadline.dateChanged.connect(self.preview)
        for name, label in [('line1', 'Title'), ('line2', 'Second line'),
                            ('sub1', 'Subtask 1'), ('sub2', 'Subtask 2')]:
            edit = QLineEdit(getattr(card.task, name))
            edit.setMaxLength(200)
            setattr(self, name, edit)
            form.addRow(label, edit)
            edit.textChanged.connect(self.preview)
        for name, label in [('font1', 'Title / number font'), ('font2', 'Text font')]:
            combo = QFontComboBox()
            combo.setCurrentFont(QFont(getattr(card.task, name)))
            setattr(self, name, combo)
            form.addRow(label, combo)
            combo.currentFontChanged.connect(self.preview)
        self.color = QPushButton(card.task.color)
        self.color.clicked.connect(self.pick_color)
        form.addRow('Accent color', self.color)
        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.25, 3)
        self.scale.setSingleStep(0.25)
        self.scale.setValue(card.task.scale)
        form.addRow('Scale', self.scale)
        self.scale.valueChanged.connect(self.preview)
        self.ignore_click = QCheckBox('Clicks pass through to windows underneath')
        self.ignore_click.setChecked(card.task.ignore_click)
        form.addRow('Click-through', self.ignore_click)
        self.stay_on_top = QCheckBox('Always on top')
        self.stay_on_top.setChecked(card.task.stay_on_top)
        form.addRow(self.stay_on_top)
        self.stay_on_top.toggled.connect(self.preview)
        form.addRow(QLabel('Use the control window or tray to edit click-through cards.'))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.color.text()), self)
        if color.isValid():
            self.color.setText(color.name())
            self.preview()

    def preview(self, *args):
        values = asdict(self.original)
        for name in ('line1', 'line2', 'sub1', 'sub2'):
            values[name] = getattr(self, name).text()
        values.update(deadline=self.deadline.date().toString('yyyy-MM-dd'),
                      font1=self.font1.currentFont().family(), font2=self.font2.currentFont().family(),
                      color=self.color.text(), scale=self.scale.value(),
                      stay_on_top=self.stay_on_top.isChecked())
        # Apply click-through only on OK so the preview stays draggable.
        self.card.task = Task.from_dict(values)
        self.card.apply_settings()

    def accept(self):
        self.preview()
        self.card.task.ignore_click = self.ignore_click.isChecked()
        self.card.apply_settings()
        if self.card.manager.persist():
            super().accept()

    def reject(self):
        self.card.task = self.original
        self.card.apply_settings()
        super().reject()


class Manager(QWidget):
    def __init__(self, path):
        super().__init__()
        self.path = path
        tasks = load_tasks(path)
        self.cards = []
        self.editing = False
        self.setWindowTitle('DeadlineP5 — Tasks')
        self.resize(560, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Drag a countdown to move it. Double-click or right-click to edit.'))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self.edit_selected())
        layout.addWidget(self.list)
        row = QHBoxLayout()
        for label, callback in [('New', self.add_task), ('Settings', self.edit_selected),
                                ('Clone', self.clone_selected), ('Remove', self.remove_selected),
                                ('Unlock all', self.unlock_all), ('Quit', self.quit)]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, cb=callback: cb())
            row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(QLabel('Closing this control window hides it when a tray is available.'))
        for task in tasks:
            self.cards.append(Card(self, task))
        self.refresh_list()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.last_day = date.today()
        self.tray = QSystemTrayIcon(self)
        icon = QPixmap(32, 32)
        icon.fill(QColor('#fe0000'))
        self.tray.setIcon(QIcon(icon))
        self.setWindowIcon(QIcon(icon))
        menu = QMenu(self)
        menu.addAction('Manage tasks', self.show_manager)
        menu.addAction('New task', self.add_task)
        menu.addAction('Unlock all cards', self.unlock_all)
        menu.addSeparator()
        menu.addAction('Quit', self.quit)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip('DeadlineP5')
        self.tray.activated.connect(lambda _: self.show_manager())
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def tick(self):
        if date.today() != self.last_day:
            self.last_day = date.today()
            for card in self.cards:
                card.update()
            self.refresh_list()

    def refresh_list(self):
        selected = self.list.currentRow()
        self.list.clear()
        for card in self.cards:
            t = card.task
            self.list.addItem(f'{t.line1 or "Untitled"} — {t.remaining()} days — {t.deadline}')
        if self.cards:
            self.list.setCurrentRow(max(0, min(selected, len(self.cards) - 1)))

    def persist(self):
        self.refresh_list()
        try:
            save_tasks(self.path, [card.task for card in self.cards])
        except OSError as exc:
            QMessageBox.critical(self, 'Could not save settings', str(exc))
            return False
        return True

    def add_task(self, template=None):
        task = replace(template, x=template.x + 32, y=template.y + 32) if template else Task()
        self.cards.append(Card(self, task))
        self.persist()

    def selected(self):
        row = self.list.currentRow()
        return self.cards[row] if 0 <= row < len(self.cards) else None

    def edit_selected(self):
        card = self.selected()
        if card:
            self.edit_card(card)

    def clone_selected(self):
        card = self.selected()
        if card:
            self.add_task(card.task)

    def edit_card(self, card):
        if self.editing:
            return
        self.editing = True
        try:
            SettingsDialog(card).exec_()
        finally:
            self.editing = False

    def confirm_remove(self, card):
        if QMessageBox.question(self, 'Remove task', f'Remove “{card.task.line1}”?',
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.remove_card(card)

    def remove_selected(self):
        card = self.selected()
        if card:
            self.confirm_remove(card)

    def remove_card(self, card):
        self.cards.remove(card)
        card.close()
        self.persist()

    def unlock_all(self):
        for card in self.cards:
            card.task.ignore_click = False
            card.apply_settings()
        self.persist()
        self.show_manager()

    def show_manager(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self.tray.isVisible():
            self.hide()
        else:
            self.showMinimized()
        event.ignore()

    def quit(self):
        if self.persist():
            QApplication.instance().quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path(__file__).with_name('deadlinep5.json'),
                        help='JSON settings file (default: beside this script)')
    args = parser.parse_args()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('DeadlineP5 Python')
    try:
        args.data = args.data.expanduser().resolve()
        args.data.parent.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(args.data) + '.lock')
        if not lock.tryLock(0):
            QMessageBox.critical(None, 'Settings file in use',
                                 'Another instance is using this settings file, or its lock cannot be created.')
            return 1
        manager = Manager(args.data)
    except (OSError, ValueError, TypeError) as exc:
        QMessageBox.critical(None, 'Cannot load countdowns', f'{args.data}\n\n{exc}\n\nThe file was left unchanged.')
        return 1
    manager.show_manager()
    if not manager.persist():
        return 1
    app.aboutToQuit.connect(manager.persist)
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
