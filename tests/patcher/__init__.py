# tests.patcher

import io
import os
import pathlib
import stat

class OsPatcher(object):
    def __init__(self, root):
        self._root = root

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

    def _traverse(self, path):
        parts = list(reversed(path.parts))
        dir   = self._root
        route = []
        while len(parts) > 1:
            part = parts.pop()
            if part == pathlib.Path().resolve().anchor:
                dir   = self._root
                route = []
            elif part == '.':
                pass
            elif part == '..':
                dir = route.pop()
            else:
                route.append(dir)
                dir = dir.get(part, {})
        result = dir.get(parts.pop(), None)
        if result is None:
            raise FileNotFoundError(2, 'No such file or directory', str(path))
        return result

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

