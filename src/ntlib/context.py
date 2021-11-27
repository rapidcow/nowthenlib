"""Context objects for tasks."""

from abc import ABC, abstractmethod
from functools import lru_cache
import uuid
from . import *

__all__ = [
    'Context', 'HashedContext',
]

# The most powerful idea of all (idea from Nov 16): Context
#
# A Context object carries the tasks for a backup file.
class Context(ABC):
    # XXX: This code is SUS!!!  Remove the sussy bakas!!!
    # (That is, i'm saying we should update the exception messages to more
    # meaningful words)
    @abstractmethod
    def get_tasks(self):
        if False:
            yield

    @abstractmethod
    def add_task(self, task):
        raise NotImplementedError('sus')

    @abstractmethod
    def remove_task(self, task):
        raise NotImplementedError('sus')

    # One major problem (especially for the case of creating a dictionary
    # that maps the task ID to its corresponding Task object) is that
    # it would be impossible to set up the context for lookup when one of
    # the tasks in the context hierarchy has been appended a new subtask.
    #
    # A possible solution i'm proposing here is to add a method hook that
    # helps add the subtasks...
    @abstractmethod
    def add_subtask(self, task, subtask):
        task.add_subtask(subtask)

    @abstractmethod
    def __len__(self):
        return 0

    @abstractmethod
    def __iter__(self):
        return self.get_tasks()

    @abstractmethod
    def __contains__(self, item):
        return item in list(self)


# XXX: The hashing process cannot possibly take place when a subtask is
# added.  How would we work around this...?
class HashedContext(Context):
    __slots__ = ('_data',)

    def __init__(self, tasks):
        if isinstance(tasks, dict):
            self._data = tasks
        else:
            raise TypeError('currently objects other than a dict cannot '
                            'be used to directly instantiate a HashContext '
                            'object')

        self.__cached_find_task = lru_cache(maxsize=128)(
            self.__find_task)

    @classmethod
    def from_tasks(cls, tasks):
        mapping = {}
        for task in tasks:
            while True:
                key = cls._generate_key()
                if key not in mapping:
                    break
            mapping[key] = task
        return cls(mapping)

    # XXX: UUID1 has the potential to generate duplicate keys?
    # (I don't know??)
    @staticmethod
    def _generate_key():
        return str(uuid.uuid1()).upper()

    # _generate_key only takes care of getting a new str key through
    # some implementation-defined algorithm
    #
    # this is different in that while _generate_key can be overridden
    # in subclasses, __generate_new_key cannot
    def __generate_new_key(self):
        while True:
            key = self._generate_key()
            if key not in self._data:
                return key

    def get_tasks(self):
        yield from self._data.values()

    def get_keys_and_tasks(self):
        yield from self._data.items()

    def get_keys(self):
        yield from self._data.keys()

    def get_task_by_key(self, task_key):
        return self._data[task_key]

    def add_task(self, task):
        self.__add_task_no_clear_cache(task)
        self.__clear_cache()

    def __add_task_no_clear_cache(self, task):
        if task in self:
            raise ValueError(f'{task!r} is already added to this context')
        key = self._generate_key()
        self._data[key] = task
        for subtask in task:
            self.__add_task_no_clear_cache(subtask)

    # XXX: this does not remove a single task, as the name implies.
    # (a big problem!!)
    def remove_task(self, task):
        keys_to_delete = [
            key for key, task in self._data.items()
            # XXX: A weird criterion
            if this_task is task or (isinstance(task, str) and key == task)
        ]

        for key in keys_to_delete:
            del self._data[key]
        self.__clear_cache()

    def add_subtask(self, task, subtask):
        self.add_task(self, subtask)
        super().add_subtask(task, subtask)
        self.__clear_cache()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return super().__iter__()

    def __contains__(self, other):
        if not isinstance(other, Task):
            return False
        try:
            self.__cached_find_task(id(other))
        except LookupError:
            return False
        return True

    def find_task_key(self, other):
        return self.__cached_find_task(id(other))

    # cached
    def __find_task(self, task_id):
        for task_key, task in self.get_keys_and_tasks():
            if id(task) == task_id:
                return task_key
        raise LookupError(task_id)

    def __clear_cache(self):
        self.__cached_find_task.cache_clear()
