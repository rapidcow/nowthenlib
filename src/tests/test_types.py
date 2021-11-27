import datetime
import unittest
from ntlib import Task, Event


class TestTask(unittest.TestCase):
    def test_basics(self):
        # p for "parent" and c for "child"
        p1 = Task('Fruit')
        c1 = Task('Apple')
        p1.add_subtask(c1)
        self.assertIs(c1.parent, p1)
        self.ensure_subtasks(p1, [c1])

        c2 = Task('Banana')
        p1.add_subtask(c2)
        self.ensure_subtasks(p1, [c1, c2])

        p2 = Task('Sustenance')
        p2.add_subtask(c1)
        self.ensure_subtasks(p1, [c2])
        self.ensure_subtasks(p2, [c1])
        p2.add_subtask(c2)
        self.ensure_no_subtasks(p1)
        self.ensure_subtasks(p2, [c1, c2])

    def ensure_subtasks(self, parent, subtasks):
        """Ensure that subtasks of 'parent' contain precisely items of
        'subtasks'.  Order may be implementation-defined, but the length
        of the iterator and also missing and extra subtasks are checked.
        """
        expected = len(subtasks)
        # Prevent infinite iterator... somehow?
        n = 0
        tasks = []
        subs = parent.get_subtasks()
        while n < expected:
            try:
                task = next(subs)
                self.assertIn(task, subtasks,
                              '{!r} should not be a subtask of {!r}'
                              .format(task, parent))
            except StopIteration:
                # Throw the exception later
                break
            tasks.append(task)
            n += 1
        self.assertCountEqual(tasks, subtasks,
                              '{!r} should have more subtasks '
                              '(expected {})'.format(parent, expected))
        try:
            next(subs)
        except StopIteration:
            return
        self.assertTrue(False,
                        '{!r} should have fewer subtasks '
                        '(expected {})'.format(parent, expected))

    def ensure_no_subtasks(self, parent):
        """Ensure that 'parent' has no subtasks.  That is, get_subtasks()
        returns an empty iterator.
        """
        subs = parent.get_subtasks()
        try:
            next(subs)
        except StopIteration:
            return
        self.assertTrue(False, '{!r} should have no subtasks'.format(parent))


class TestEvent(unittest.TestCase):
    # I don't know what to test... yet??
    # XXX: This test has basically no point
    def test_basics(self):
        # I hate myself typing pointless code at this point of time
        expected_s = self.get_time('2021-11-20 22:34+08:00')
        expected_e = self.get_time('2021-11-21 01:02:02+08:00')

        # I hate myself but i like Among Us memes... oooh
        task = Task('Sus!')
        event = Event(task, start=expected_s, end=expected_e)

        self.assertIs(event.task, task)
        self.assertEqual(event.start.timetuple(), expected_s.timetuple())
        self.assertEqual(event.end.timetuple(), expected_e.timetuple())

    def get_time(self, timestr):
        return datetime.datetime.fromisoformat(timestr)
