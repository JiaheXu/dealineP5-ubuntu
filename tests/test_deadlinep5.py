import json
import os
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import deadlinep5 as dp
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QApplication


class CountdownTests(unittest.TestCase):
    def test_calendar_days_and_overdue_clamping(self):
        today = date(2026, 10, 25)
        for deadline, expected in [('2026-10-24', 0), ('2026-10-25', 0),
                                   ('2026-10-26', 1), ('2027-01-01', 68)]:
            with self.subTest(deadline=deadline):
                self.assertEqual(dp.Task(deadline=deadline).remaining(today), expected)

    def test_leap_day(self):
        self.assertEqual(dp.Task(deadline='2028-03-01').remaining(date(2028, 2, 28)), 2)

    def test_new_task_defaults(self):
        task = dp.Task()
        self.assertEqual(task.deadline, (date.today() + timedelta(days=10)).isoformat())
        self.assertFalse(task.ignore_click)
        self.assertTrue(task.stay_on_top)

    def test_invalid_settings_rejected(self):
        for field, value in [('deadline', '2026-02-30'), ('scale', 0),
                             ('scale', float('nan')), ('color', 'garbage'),
                             ('ignore_click', 'false'), ('x', 1.5)]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    dp.Task.from_dict({field: value})

    def test_unicode_and_multiple_tasks_roundtrip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'tasks.json'
            tasks = [dp.Task(line1='納期', sub1='提交报告'), dp.Task(line1='Another', x=-120)]
            dp.save_tasks(path, tasks)
            self.assertEqual(dp.load_tasks(path), tasks)
            dp.save_tasks(path, [])
            self.assertEqual(dp.load_tasks(path), [])

    def test_bad_data_not_silently_replaced(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'tasks.json'
            path.write_text('{broken')
            with self.assertRaises(ValueError):
                dp.load_tasks(path)
            self.assertEqual(path.read_text(), '{broken')


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.manager = dp.Manager(Path(self.tmp.name) / 'tasks.json')

    def tearDown(self):
        for card in self.manager.cards:
            card.close()
        self.manager.close()
        self.tmp.cleanup()

    def test_clone_is_independent_and_saved(self):
        original = self.manager.cards[0]
        self.manager.add_task(original.task)
        clone = self.manager.cards[1]
        clone.task.line1 = 'Changed'
        self.assertNotEqual(original.task.line1, clone.task.line1)
        self.assertNotEqual(original.pos(), clone.pos())
        self.manager.persist()
        self.assertEqual(len(dp.load_tasks(self.manager.path)), 2)

    def test_preview_cancel_and_accept(self):
        card = self.manager.cards[0]
        old = card.task.line1
        dialog = dp.SettingsDialog(card)
        dialog.line1.setText('Preview')
        self.assertEqual(card.task.line1, 'Preview')
        dialog.reject()
        self.assertEqual(card.task.line1, old)
        dialog = dp.SettingsDialog(card)
        dialog.line1.setText('Saved')
        dialog.accept()
        self.assertEqual(dp.load_tasks(self.manager.path)[0].line1, 'Saved')

    def test_render_clickthrough_recovery_and_remove(self):
        card = self.manager.cards[0]
        self.app.processEvents()
        self.assertFalse(card.grab().isNull())
        card.task.ignore_click = True
        card.apply_settings()
        self.assertTrue(card.windowFlags() & Qt.WindowTransparentForInput)
        self.manager.unlock_all()
        self.assertFalse(card.task.ignore_click)
        self.assertFalse(card.windowFlags() & Qt.WindowTransparentForInput)
        self.manager.remove_card(card)
        self.assertEqual(dp.load_tasks(self.manager.path), [])

    def test_save_failure_keeps_task_selection_in_sync(self):
        self.manager.cards[0].task.line1 = 'First'
        self.manager.add_task()
        self.manager.cards[1].task.line1 = 'Second'
        first = self.manager.cards[0]
        with patch.object(dp, 'save_tasks', side_effect=OSError('Disk full')), \
                patch.object(dp.QMessageBox, 'critical'):
            self.manager.remove_card(first)
        self.assertEqual(self.manager.list.count(), 1)
        self.assertIn('Second', self.manager.list.item(0).text())
        self.assertEqual(self.manager.selected().task.line1, 'Second')

    def test_original_style_has_transparent_surroundings_and_accent_banner(self):
        card = self.manager.cards[0]
        card.task.color = '#32b4ff'
        card.apply_settings()
        image = card.grab().toImage()
        self.assertEqual((image.width(), image.height()), (600, 200))
        self.assertEqual(image.pixelColor(10, 10).alpha(), 0)
        self.assertEqual(image.pixelColor(35, 150).name(), '#32b4ff')

    def test_original_style_keeps_long_titles_and_subtasks_inside_window(self):
        card = self.manager.cards[0]
        card.task.line1 = 'A much longer deadline title'
        card.task.sub1 = 'First subtask'
        card.task.sub2 = 'Second subtask'
        card.task.scale = 0.5
        card.apply_settings()
        image = card.grab().toImage()
        self.assertEqual((image.width(), image.height()), (300, 134))
        self.assertTrue(any(image.pixelColor(x, 125).alpha() for x in range(20, 280)))


if __name__ == '__main__':
    unittest.main()
