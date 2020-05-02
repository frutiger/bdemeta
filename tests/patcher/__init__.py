# tests.patcher

import io
import os
import pathlib
import stat

class OsPatcher(object):
    def __init__(self, root):
        self._root = root

        self._parents = {}
        self._buildParents(None, [root])

        self._real_open = io.open
        io.open = self._open

        self._real_listdir = pathlib._NormalAccessor.listdir
        pathlib._NormalAccessor.listdir = self._listdir

        self._real_stat = pathlib._NormalAccessor.stat
        pathlib._NormalAccessor.stat = self._stat

        self._real_isdir = pathlib.Path.is_dir
        pathlib.Path.is_dir = lambda path: OsPatcher._is_dir(self, path)

    def reset(self):
        io.open = self._real_open
        pathlib._NormalAccessor.listdir = self._real_listdir
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

