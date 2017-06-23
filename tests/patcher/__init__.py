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

    def reset(self):
        io.open = self._real_open
        pathlib._NormalAccessor.listdir = self._real_listdir
        pathlib._NormalAccessor.stat = self._real_stat

    def _traverse(self, path):
        path = list(reversed(path.parts))
        dir  = self._root
        while len(path) > 1:
            dir = dir.get(path.pop(), {})
        return dir.get(path.pop(), None)

    def _open(self, path, *args, **kwargs):
        return io.StringIO(self._traverse(pathlib.Path(path)))

    def _listdir(self, path):
        return self._traverse(path).keys()

    def _stat(self, path):
        data = self._traverse(path)
        if data != None and type(data) != dict:
            mode = stat.S_IFREG
        elif type(data) == dict:
            mode = stat.S_IFDIR
        else:
            mode = 0
        return os.stat_result([mode, 0, 0, 0, 0, 0, 0, 0, 0, 0])

