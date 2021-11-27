"""Ooh what's this"""
__all__ = [
    'Task', 'Event',
]

import datetime


# Since we're accepting input from the Now Then archives directly
# I think it's fair that we implement canonical methods to load info
# from literal strings?  (Answer: NO.  Make it programming-friendly and
# not... easy for processing.)

# Task cannot be immutable since that would make adding/removing tasks
# basically HELL
class Task:
    """A task that serves as the type of an event."""
    # Order of the columns in tasks.csv:
    # Primary Key,Name,Abbreviation,Colour,Hidden,Order,ParentKey
    __slots__ = ('_name', '_parent', '_subtasks', '_abbr', '_color')

    def __init__(self, name, abbr=None, color=None, parent=None):
        self.name = name
        self.abbr = abbr
        self.color = color
        # Skip validation
        self._subtasks = []
        # Set it to some value anyway.  We'll leave everything off to
        # add_subtask() after that.
        self._parent = None
        if self.__check_task_type(parent, 'parent'):
            parent.add_subtask(self)

    @classmethod
    def __check_task_type(cls, parent, name):
        if parent is None:
            return False
        if isinstance(parent, cls):
            return True
        raise TypeError('{} should be a Task or None, not {!r}'
                        .format(name, parent))

    # TODO: Add docstrings for the properties
    @property
    def name(self):
        """description for 'name'"""
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError('name should be a str or None, not {!r}'
                            .format(value))
        self._name = value

    @property
    def parent(self):
        """description for 'parent'"""
        return self._parent

    # "There should be one --- and preferably only one --- obvious way
    # to do it"
    # @parent.setter
    # def parent(self, value):
    #     self.__check_parent_type(value)
    #     self._parent = value

    @property
    def abbr(self):
        """description for 'abbr'"""
        return self._abbr

    @abbr.setter
    def abbr(self, value):
        if not (value is None or isinstance(value, str)):
            raise TypeError('abbr should be a str or None, not {!r}'
                            .format(value))
        self._abbr = value

    @property
    def color(self):
        """description for 'color'"""
        return self._color

    @color.setter
    def color(self, value):
        if value is None:
            self._color = None
            return
        # Since strings are iterables, prevent such usage by throwing
        # a more meaningful message
        if isinstance(value, str):
            raise TypeError('color should not be a str')
        try:
            red, green, blue, alpha = value
            red = float(red)
            green = float(green)
            blue = float(blue)
            alpha = float(alpha)
        except (ValueError, TypeError) as exc:
            raise TypeError('color should be able to be unpacked into '
                            'four float-compatible objects') from exc
        self._color = (red, green, blue, alpha)

    def get_subtasks(self):
        """An iterator of all the subtasks of the current task."""
        yield from self._subtasks

    def has_subtasks(self):
        return bool(self._subtasks)

    def add_subtask(self, subtask):
        """Add subtask as a task of self."""
        self.__check_task_type(subtask, 'subtask')
        if subtask._parent:
            subtask._parent.remove_subtask(subtask)
        if subtask in self._subtasks:
            raise ValueError('{!r} is already a subtask'.format(subtask))
        self._subtasks.append(subtask)
        subtask._parent = self

    def add_subtasks(self, subtasks):
        for index, subtask in enumerate(subtasks):
            try:
                self.add_subtask(subtask)
            except Exception as exc:
                raise ValueError('invalid task found in item #{}'
                                 .format(index)) from exc

    def remove_subtask(self, subtask):
        """Remove subtask from the current task."""
        self.__check_task_type(subtask, 'subtask')
        try:
            index = self._subtasks.index(subtask)
        except ValueError:
            raise ValueError('cannot remove subtask {!r} from {!r}'
                             .format(subtask, self)) from None
        self._subtasks.pop(index)
        subtask._parent = None

    # XXX: Do we really need this?
    def is_subtask(self, subtask):
        return subtask in self._subtasks and subtask.parent is self

    def __repr__(self):
        return f'<Task {self.name!r}>'

    # Despite how truth value of objects are True by default (as long as
    # they don't implement __len__()) i'm still... yeah, doing this.
    def __bool__(self):
        return True

    # This sort of counts as the "name"... but is actually a tuple of names
    #
    # This method falls into an infinite loop if parent tasks are circular
    def get_complete_name(self):
        if self.parent is None:
            return (self.name,)
        names = []
        this_task = self
        while True:
            names.append(this_task.name)
            parent = this_task.parent
            this_task = parent
            if this_task is None:
                break
        names.reverse()
        return tuple(names)


class Event:
    """Event as a record of a duration of time."""
    # Order of the columns in events.csv:
    # Primary Key,Start Date,End Date,Comment,TaskKey
    __slots__ = ('_task', '_start', '_end', '_comment')

    def __init__(self, task, start, end, comment=''):
        self.task = task
        self.start = start
        self.end = end
        self.comment = comment

    @property
    def task(self):
        """The unique task that the currect event belongs to."""
        return self._task

    @task.setter
    def task(self, task):
        if not isinstance(task, Task):
            raise TypeError('task should be a Task object, not {!r}'
                            .format(task))
        self._task = task

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, dt):
        self._start = self.__convert_datetime(dt, 'start')
        self.__validate_time()

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, dt):
        self._end = self.__convert_datetime(dt, 'end')
        self.__validate_time()

    # XXX: A stub
    @staticmethod
    def __convert_datetime(dt, name):
        if isinstance(dt, datetime.datetime):
            # check it is aware
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                raise TypeError(f'{name} should be an aware datetime '
                                f'object')
            return dt
        raise TypeError(f'{name} should be a datetime.datetime object, '
                        f'not {dt!r}')

    def __validate_time(self):
        try:
            start = self._start
            end = self._end
        except AttributeError:
            # In case any one of these is unset, RETURN...
            return

        if start > end:
            raise ValueError('start time later than end time')

    @property
    def comment(self):
        return self._comment

    @comment.setter
    def comment(self, value):
        self._comment = value

    def __repr__(self):
        return f'<Event of {self.task!r}>'

    def __bool__(self):
        return True
