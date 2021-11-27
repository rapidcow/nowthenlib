"""dealing with archives"""
__all__ = [
    'ArchiveLoader', 'ArchiveDumper',
]

from contextlib import contextmanager
import csv
import datetime
import io
import uuid
import zipfile
# Import Task, Event
from . import *
from .context import HashedContext

_TASK_HEAD = ('Primary Key', 'Name', 'Abbreviation', 'Colour', 'Hidden',
              'Order', 'ParentKey')
_EVENT_HEAD = ('Primary Key', 'Start Date', 'End Date', 'Comment', 'TaskKey')
_TASK_FILE = 'tasks.csv'
_EVENT_FILE = 'events.csv'


class ArchiveLoader:
    def __init__(self, **kwargs):
        self._all_options = {
            'time_zone',
        }
        self.time_zone = datetime.timezone.utc
        self.configure(**kwargs)

    def configure(self, **kwargs):
        """Configure options.  This method should be called instead of
        directly accessing the underlying attributes.
        """
        invalid = kwargs.keys() - self._all_options
        if invalid:
            invalid_str = ', '.join(sorted(invalid))
            raise ValueError(f'invalid keys: {invalid_str}')
        for k, v in kwargs.items():
            setattr(self, k, v)

    def load(self, file):
        with self.__prepare_readers(file) as (task_reader, event_reader):
            context = self.__parse_tasks(task_reader)
            events = self.__parse_events(event_reader, context)
            return context, events

    def load_context(self, file):
        with self.__prepare_readers(file) as (task_reader, _):
            return self.__parse_tasks(task_reader)

    @contextmanager
    def __prepare_readers(self, file):
        with zipfile.ZipFile(file, 'r') as zf:
            with self.__open_file(zf, _TASK_FILE) as tk_fp, \
                    self.__open_file(zf, _EVENT_FILE) as ev_fp:
                task_reader = csv.reader(tk_fp)
                event_reader = csv.reader(ev_fp)
                yield task_reader, event_reader

    def __open_file(self, zf, file):
        return io.TextIOWrapper(zf.open(file, 'r'),
                                encoding='utf-8')

    def __parse_tasks(self, reader):
        # Columns of tasks.csv (for reference):
        # Primary Key,Name,Abbreviation,Colour,Hidden,Order,ParentKey
        assert tuple(next(reader)) == _TASK_HEAD

        task_map = {}
        for key, name, abbr, color, _, _, parent_key in reader:
            assert key not in task_map
            colors = None if color == 'Automatic' else color.split(',')
            task_map[key] = (Task(name, abbr, colors), parent_key)

        # Now we connect tasks to their appropriate parent tasks
        for task, parent_key in task_map.values():
            if parent_key:
                try:
                    task_map[parent_key][0].add_subtask(task)
                except KeyError:
                    raise ValueError(f'Cannot find parent task '
                                     f'{parent_id!r} for {name} '
                                     f'({primary_id})') from None

        return HashedContext({key: task for key, (task, _) in
                              task_map.items()})

    def __parse_events(self, reader, ctx):
        # Columns of events.csv (for reference):
        # Primary Key,Start Date,End Date,Comment,TaskKey
        assert tuple(next(reader)) == _EVENT_HEAD

        events = []
        for key, start_str, end_str, comment, task_key in reader:
            task = ctx.get_task_by_key(task_key)
            # TODO: Somehow parse start time and end time (with the
            # appropriate time zone!)
            start = self.__parse_time(start_str)
            end = self.__parse_time(end_str)
            events.append(Event(task, start, end, comment))

        return events

    def __parse_time(self, string):
        assert string.endswith('Z')
        # parsed = datetime.datetime.fromisoformat(string[:-1] + '+00:00')
        fmt = '%Y-%m-%dT%H:%M:%S'
        parsed = (datetime.datetime.strptime(string[:-1], fmt)
                  .replace(tzinfo=datetime.timezone.utc))
        return parsed.astimezone(self.time_zone)



class ArchiveDumper:
    """
    "It used to be called Dumpy, but now it's ArchiveDumper official!"
    """
    def dump(self, ctx, events, file):
        if not isinstance(ctx, HashedContext):
            ctx = HashedContext.from_tasks(ctx)
        with zipfile.ZipFile(file, 'w') as zf:
            with self.__open_file(zf, _TASK_FILE) as fp:
                writer = self.__prepare_writer(fp)
                self.__write_tasks(writer, ctx)
            with self.__open_file(zf, _EVENT_FILE) as fp:
                writer = self.__prepare_writer(fp)
                self.__write_events(writer, ctx, events)

    def __prepare_writer(self, fp):
        # XXX dialets
        # all quantities MUST be quoted
        return csv.writer(fp, dialect='unix', quoting=csv.QUOTE_ALL)

    def __open_file(self, zf, file):
        return io.TextIOWrapper(zf.open(file, 'w'),
                                encoding='utf-8',
                                # Let csv.writer do the job
                                newline='\n')

    def __write_tasks(self, writer, ctx):
        writer.writerow(_TASK_HEAD)
        for key, task, par_key, order in self._walk_context(ctx):
            print(key, task, par_key, order)
            if task is None:
                continue
            primary_key = '' if key is None else key
            parent_key = '' if par_key is None else par_key
            name = task.name
            abbr = '' if task.abbr is None else task.abbr
            color = ('Automatic' if task.color is None
                     else ','.join(str(ch) for ch in task.color))
            # Always write hidden as 0 (somehow???)
            writer.writerow((primary_key, name, abbr, color, '0',
                             format(order, '.2f'), parent_key))
            last_task = task
            last_key = key

    def _walk_context(self, ctx):
        yield from self.__walk_context_impl(ctx, None, None, None, 1)

    # Uses recursion
    def __walk_context_impl(self, ctx, this_key, this_task,
                            parent_key, index):
        # XXX: Not the most efficient way, but at least this guarentees
        # 'tasks' does not consist of any task outside of this context.
        #
        # (We still haven't agreed on how subtasks should be added for a
        # task that exists in a context)
        tasks = ((k, t) for k, t in ctx.get_keys_and_tasks()
                 if t.parent is this_task)
        # Recurse into subtasks later
        yield this_key, this_task, parent_key, index
        for idx, (key, task) in enumerate(tasks, start=1):
            yield from self.__walk_context_impl(
                ctx, key, task, this_key, idx)


    def __write_events(self, writer, ctx, events):
        writer.writerow(_EVENT_HEAD)
        keys_generated = set(ctx.get_keys())
        for event in events:
            task_key = ctx.find_task_key(event.task)
            start = self.__format_time(event.start)
            end = self.__format_time(event.end)
            comment = event.comment
            while True:
                key = str(uuid.uuid1()).upper()
                if key not in keys_generated:
                    break
            keys_generated.add(key)
            writer.writerow((str(key).upper(), start, end, comment, task_key))

    def __format_time(self, dt):
        utctime = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        s = utctime.isoformat(timespec='seconds')
        return s + 'Z'
