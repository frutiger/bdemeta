# tests.test_bdemeta

from io       import StringIO
from pathlib  import Path as P
from unittest import TestCase

from bdemeta.__main__ import InvalidArgumentsError, InvalidPathError, \
                             NoConfigError, run, main
from bdemeta.cmake    import generate
from bdemeta.resolver import resolve, TargetResolver
from tests.patcher    import OsPatcher

import bdemeta

def get_filestore_writer(files):
    def write(path, writer):
        files[path] = StringIO()
        writer(files[path])
        files[path].seek(0)
    return write

class NoConfigErrorTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({})

    def tearDown(self):
        self._patcher.reset()

    def test_no_config_error(self):
        caught = False
        try:
            run(StringIO(), None, ['walk', 'foo'])
        except NoConfigError as e:
            caught = True
        assert(caught)

    def test_args_error_if_config_unneeded(self):
        caught = False
        try:
            run(StringIO(), None, [])
        except InvalidArgumentsError as e:
            caught = True
        assert(caught)

class InvalidArgumentsErrorTest(TestCase):
    def test_carries_one_attribute(self):
        e = InvalidArgumentsError('foo')
        assert('foo' == e.args[0])

class RunTest(TestCase):
    def setUp(self):
        self._config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
            '.bdemeta.conf': '{"roots": ["r"]}',
            'r': {
                'groups': {
                    'gr1': {
                        'group': {
                            'gr1.dep': '',
                            'gr1.mem': 'gr1p1 gr1p2',
                        },
                        'gr1p1': {
                            'package': {
                                'gr1p1.dep': '',
                                'gr1p1.mem': '',
                            },
                        },
                        'gr1p2': {
                            'package': {
                                'gr1p2.dep': '',
                                'gr1p2.mem': '',
                            },
                        },
                    },
                    'gr2': {
                        'group': {
                            'gr2.dep': 'gr1',
                            'gr2.mem': '',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_no_mode_error(self):
        message = None
        try:
            run(StringIO(), None, [])
        except InvalidArgumentsError as e:
            message = e.args[0]
        assert('No mode specified' == message)

    def test_unknown_mode_error(self):
        message = None
        try:
            run(StringIO(), None, ['foo'])
        except InvalidArgumentsError as e:
            message = e.args[0]
        assert('Unknown mode \'{}\''.format('foo') == message)

    def test_target_with_dependencies(self):
        f = StringIO()
        run(f, None, ['walk', 'gr2'])

        r  = TargetResolver(self._config)
        us = resolve(r, ['gr2'])

        assert(' '.join(u.name for u in us) + '\n' == f.getvalue())

class NoRootTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            '.bdemeta.conf': '{"roots": ["r"]}',
        })

    def tearDown(self):
        self._patcher.reset()

    def test_no_root_error(self):
        error = None
        try:
            run(StringIO(), None, ['walk'])
        except InvalidPathError as e:
            error = e
        assert(error is not None)
        assert(P('r') == error.args[0])

    def test_no_root_main_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main([__name__, 'walk', 'p1'], stdout, stderr)
        assert(not stdout.getvalue())
        assert(stderr.getvalue())
        assert('r' in stderr.getvalue())

class GraphTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            '.bdemeta.conf': '{"roots": ["r"]}',
            'r': {
                'adapters': {
                    'p1': {
                        'package': {
                            'p1.dep': '',
                            'p1.mem': '',
                        },
                    },
                    'p2': {
                        'package': {
                            'p2.dep': 'p1',
                            'p2.mem': '',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_graph(self):
        f = StringIO()
        run(f, None, ['dot', 'p2'])
        lines = f.getvalue().split('\n')
        assert('digraph G {'      == lines[0])
        assert('    "p2" -> "p1"' == lines[1])
        assert('}'                == lines[2])

class CMakeTest(TestCase):
    def setUp(self):
        self._config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
            '.bdemeta.conf': '{"roots": ["r"]}',
            'r': {
                'adapters': {
                    'p': {
                        'package': {
                            'p.dep': '',
                            'p.mem': '',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_generate_cmake(self):
        output = StringIO()

        f1 = {}
        w1 = get_filestore_writer(f1)

        run(output, w1, ['cmake', 'p'])

        r  = TargetResolver(self._config)
        p  = resolve(r, 'p')
        f2 = {}
        w2 = get_filestore_writer(f2)
        generate(p, w2, {})

        assert(f1.keys() == f2.keys())
        for k in f1:
            assert(f1[k].getvalue() == f2[k].getvalue())

class MainTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            '.bdemeta.conf': '{"roots": ["r"]}',
            'r': {
                'adapters': {
                    'p1': {
                        'package': {
                            'p1.dep': '',
                            'p1.mem': '',
                        },
                    },
                    'p2': {
                        'package': {
                            'p2.dep': 'p1',
                            'p2.mem': '',
                        },
                    },
                    'p3': {
                        'package': {
                            'p3.dep': 'p4',
                            'p3.mem': '',
                        },
                    },
                    'p4': {
                        'package': {
                            'p4.dep': 'p3',
                            'p4.mem': '',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_walk(self):
        stdout = StringIO()
        main([None, 'walk', 'p2'], stdout)
        assert('p2 p1\n' == stdout.getvalue())

    def test_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main([__name__, 'foo'], stdout, stderr)
        assert(not stdout.getvalue())
        assert(stderr.getvalue())

    def test_cyclic_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main([__name__, 'walk', 'p3'], stdout, stderr)
        assert(not stdout.getvalue())
        assert(stderr.getvalue())
        assert('p3' in stderr.getvalue())
        assert('p4' in stderr.getvalue())

    def test_not_found_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main([__name__, 'walk', 'p5'], stdout, stderr)
        assert(not stdout.getvalue())
        assert(stderr.getvalue())
        assert('p5' in stderr.getvalue())

class NoConfigMainTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
        })

    def tearDown(self):
        self._patcher.reset()

    def test_help_text(self):
        stdout = StringIO()
        stderr = StringIO()
        main([__name__], stdout, stderr)
        assert(not stdout.getvalue())
        assert(stderr.getvalue())

    def test_no_config_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main([__name__, 'walk', 'p1'], stdout, stderr)
        assert(not stdout.getvalue())
        assert(stderr.getvalue())

