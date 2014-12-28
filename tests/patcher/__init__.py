# tests.patcher

import io
import os

class Patcher(object):
    def __init__(self, module):
        self._names = module.__dict__

    def patch(self, full_name, value):
        names     = self._names
        full_name = full_name.split('.')
        full_name.reverse()
        while len(full_name) > 1:
            names = names[full_name.pop()].__dict__
        name = full_name.pop()
        if name in names:
            real_value = names[name]
        else:
            real_value = names['__builtins__'][name]
        names[name] = value
        return lambda: names.update([(name, real_value)])

class OsPatcher(object):
    def __init__(self, module, root):
        self._patcher       = Patcher(module)
        self._root          = root
        self._reset_open    = self._patch('io.open',        self._open)
        self._reset_listdir = self._patch('os.listdir',     self._listdir)
        self._reset_isfile  = self._patch('os.path.isfile', self._isfile)
        self._reset_isdir   = self._patch('os.path.isdir' , self._isdir)

    def _patch(self, name, value):
        return self._patcher.patch(name, value)

    def reset(self):
        self._reset_open()
        self._reset_listdir()
        self._reset_isfile()
        self._reset_isdir()

    def _traverse(self, path):
        path = path.split(os.path.sep)
        path.reverse()
        dir  = self._root
        while len(path) > 1:
            dir = dir.get(path.pop(), {})
        return dir.get(path.pop(), None)

    def _open(self, path):
        return io.StringIO(self._traverse(path))

    def _listdir(self, path):
        return self._traverse(path).keys()

    def _isfile(self, path):
        data = self._traverse(path)
        return data != None and type(data) != dict

    def _isdir(self, path):
        return type(self._traverse(path)) == dict

