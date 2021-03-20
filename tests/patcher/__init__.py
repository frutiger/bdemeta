# tests.patcher

import io
import os
import pathlib
import stat

class DirEntry:
    def __init__(self, name, is_dir):
        self.name    = name
        self._is_dir = is_dir

    def is_dir(self):
        return self._is_dir

class ScandirIterator:
    def __init__(self, data):
        self._entries = (DirEntry(name, type(value) == dict) for \
                                                   name, value in data.items())

    def __enter__(self):
        return self._entries

    def __exit__(self, *exc_details):
        pass

class OsPatcher(object):
    def __init__(self, root):
        self._root = root

        self._parents = {}
        self._buildParents(None, [root])

        self._real_open = io.open
        io.open = self._open

        self._real_listdir = pathlib._NormalAccessor.listdir
        pathlib._NormalAccessor.listdir = self._listdir

        self._real_scandir = pathlib._NormalAccessor.scandir
        pathlib._NormalAccessor.scandir = self._scandir

        self._real_stat = pathlib._NormalAccessor.stat
        pathlib._NormalAccessor.stat = self._stat

        self._real_isdir = pathlib.Path.is_dir
        pathlib.Path.is_dir = lambda path: OsPatcher._is_dir(self, path)

    def reset(self):
        io.open = self._real_open
        pathlib._NormalAccessor.listdir = self._real_listdir
        pathlib._NormalAccessor.scandir = self._real_scandir
        pathlib._NormalAccessor.stat = self._real_stat
        pathlib.is_dir = self._real_isdir

    def _buildParents(self, dir, children):
        for child in children:
            self._parents[id(child)] = dir
            if isinstance(child, dict):
                self._buildParents(child, child.values())

    def _traverse(self, path):
        parts = list(reversed(path.parts))
        entry = self._root

        while len(parts) > 0 and entry is not None:
            part = parts.pop()
            if part == pathlib.Path().resolve().anchor:
                entry   = self._root
            elif part == '.':
                pass
            elif part == '..':
                entry = self._parents[id(entry)]
            else:
                entry = entry.get(part, None)
        if entry is None:
            raise FileNotFoundError(2, 'No such file or directory', str(path))
        return entry

    def _open(self, path, *args, **kwargs):
        return io.StringIO(self._traverse(pathlib.Path(path)))

    def _listdir(self, path):
        return self._traverse(path).keys()

    def _scandir(self, path):
        data = self._traverse(path)
        if type(data) != dict:
            raise NotADirectoryError(f'{path} is not a directory')
        return ScandirIterator(data)

    def _stat(self, path):
        data = self._traverse(path)
        if type(data) == dict:
            mode = stat.S_IFDIR
        else:
            mode = stat.S_IFREG
        return os.stat_result([mode, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def _is_dir(self, path):
        try:
            return isinstance(self._traverse(path), dict)
        except FileNotFoundError:
            return False

