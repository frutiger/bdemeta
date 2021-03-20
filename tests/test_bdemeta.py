# tests.test_bdemeta

import json
import shutil
import sys
from io       import StringIO
from pathlib  import Path as P
from tempfile import TemporaryDirectory
from unittest import TestCase

from bdemeta.__main__ import InvalidArgumentsError, InvalidPathError, \
                             NoConfigError, run, main, test_runner, \
                             get_columns, get_parser
from bdemeta.cmake    import generate
from bdemeta.resolver import resolve, TargetResolver
from bdemeta.testing  import run_tests, MockRunner, RunResult
from tests.patcher    import OsPatcher

import bdemeta

def get_filestore_writer(files):
    def write(path, writer):
        files[path] = StringIO()
        writer(files[path])
        files[path].seek(0)
    return write

class InvalidPathErrorTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            'bdemeta.json': '{ "roots": ["unlikely_path_that_exists"] }',
        })

    def tearDown(self):
        self._patcher.reset()

    def test_invalid_path_error(self):
        with self.assertRaises(InvalidPathError):
            run(None, None, None, None, '', ['walk', 'bdemeta.json', 't'])

        stderr = StringIO()
        main(None,
             stderr,
             None,
             None,
             '',
             [__name__, 'walk', 'bdemeta.json', 't'])
        assert(stderr.getvalue())

class RunTest(TestCase):
    def setUp(self):
        self._config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
            'bdemeta.json': '{"roots": ["r"]}',
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

    def test_target_with_dependencies(self):
        f = StringIO()
        run(f, None, None, None, '', ['walk', 'bdemeta.json', 'gr2'])

        r  = TargetResolver(self._config)
        us = resolve(r, ['gr2'])

        assert(' '.join(u.name for u in us) + '\n' == f.getvalue())

class NoRootTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            'bdemeta.json': '{"roots": ["r"]}',
        })

    def tearDown(self):
        self._patcher.reset()

    def test_no_root_error(self):
        with self.assertRaises(InvalidPathError) as e:
            run(None, None, None, None, '', ['walk', 'bdemeta.json', 'foo'])
        assert(P('r') == e.exception.args[0])

    def test_no_root_main_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout,
             stderr,
             None,
             None,
             '',
             [__name__, 'walk', 'bdemeta.json', 'p1'])
        assert(not stdout.getvalue())
        assert(stderr.getvalue())
        assert('r' in stderr.getvalue())

class GraphTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            'bdemeta.json': '{"roots": ["r"]}',
            'r': {
                'standalones': {
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
        run(f, None, None, None, '', ['dot', 'bdemeta.json', 'p2'])
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
            'bdemeta.json': '{"roots": ["r"]}',
            'r': {
                'standalones': {
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
        output1 = StringIO()

        run(output1, None, output1, None, '', ['cmake', 'bdemeta.json', 'p'])

        r       = TargetResolver(self._config)
        p       = resolve(r, 'p')
        output2 = StringIO()
        generate(p, output2)

        assert(output1.getvalue() == output2.getvalue())

class MainTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            'bdemeta.json': '{"roots": ["r"]}',
            'r': {
                'standalones': {
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

    def test_help(self):
        stdout = StringIO()
        get_parser().print_help(stdout)

    def test_walk(self):
        stdout = StringIO()
        main(stdout,
             None,
             None,
             None,
             '',
             [None, 'walk', 'bdemeta.json', 'p2'])
        assert('p2 p1\n' == stdout.getvalue())

    def test_cyclic_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout,
             stderr,
             None,
             None,
             '',
             [__name__, 'walk', 'bdemeta.json', 'p3'])
        assert(not stdout.getvalue())
        assert(stderr.getvalue())
        assert('p3' in stderr.getvalue())
        assert('p4' in stderr.getvalue())

    def test_not_found_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout,
             stderr,
             None,
             None,
             '',
             [__name__, 'walk', 'bdemeta.json', 'p5'])
        assert(not stdout.getvalue())
        assert(stderr.getvalue())
        assert('p5' in stderr.getvalue())

class NoConfigMainTest(TestCase):
    def test_no_config_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout,
             stderr,
             None,
             None,
             '',
             [__name__, 'walk', 'bdemeta.json', 'p1'])
        assert(not stdout.getvalue())
        assert(stderr.getvalue())

class RunTestTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            'foo.t': '',
        })

    def tearDown(self):
        self._patcher.reset()

    def test_running_tests(self):
        stdout1 = StringIO()
        stderr1 = StringIO()
        runner1 = MockRunner('sfsf')
        main(stdout1,
             stderr1,
             runner1,
             lambda: 80,
             '',
             [__name__, 'runtests', 'foo.t'])

        stdout2 = StringIO()
        stderr2 = StringIO()
        runner2 = MockRunner('sfsf')
        run_tests(stdout2, stderr2, runner2, lambda: 80, [('foo.t', 'foo.t')])

        assert(stdout1.getvalue() == stdout2.getvalue())
        assert(stderr1.getvalue() == stderr2.getvalue())
        assert(runner1.commands   == runner2.commands)

    def test_running_all_tests(self):
        stdout1 = StringIO()
        stderr1 = StringIO()
        runner1 = MockRunner('sfsf')
        main(stdout1,
             stderr1,
             runner1,
             lambda: 80,
             '',
             [__name__, 'runtests'])

        stdout2 = StringIO()
        stderr2 = StringIO()
        runner2 = MockRunner('sfsf')
        run_tests(stdout2,
                  stderr2,
                  runner2,
                  lambda: 80,
                  [('foo.t', 'foo.t')])

        assert(stdout1.getvalue() == stdout2.getvalue())
        assert(stdout1.getvalue() == stdout2.getvalue())
        assert(stderr1.getvalue() == stderr2.getvalue())
        assert(runner1.commands   == runner2.commands)

class TestRunnerTest(TestCase):
    def test_success(self):
        result = test_runner([sys.executable, "-c", "import sys; sys.exit(0)"])
        assert(result == RunResult.SUCCESS)

    def test_failure(self):
        result = test_runner([sys.executable, "-c", "import sys; sys.exit(1)"])
        assert(result == RunResult.FAILURE)

    def test_no_such_case(self):
        result = test_runner([sys.executable,
                              "-c",
                              "import sys; sys.exit(-1)"])
        assert(result == RunResult.NO_SUCH_CASE)

class TerminalSizeTest(TestCase):
    def test_valid(self):
        assert(get_columns() == shutil.get_terminal_size().columns)

class RelativePathTest(TestCase):
    def setUp(self):
        self._config = {
            'roots': [
                P('r'),
            ]
        }
        self._patcher = OsPatcher({
            'dir': {
                'bdemeta.json': '{"roots": ["../r"]}',
            },
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
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_target(self):
        f = StringIO()
        run(f, None, None, None, '', ['walk', 'dir/bdemeta.json', 'gr1'])

        r  = TargetResolver(self._config)
        us = resolve(r, ['gr1'])

        assert(' '.join(u.name for u in us) + '\n' == f.getvalue())

class AbsolutePathTest(TestCase):
    def setUp(self):
        root = P(P().resolve().anchor)/'r'
        self._config = {
            'roots': [
                root,
            ]
        }
        self._patcher = OsPatcher({
            'dir': {
                'bdemeta.json': json.dumps({ 'roots': [str(root)] }),
            },
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
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_target(self):
        f = StringIO()
        run(f, None, None, None, '', ['walk', 'dir/bdemeta.json', 'gr1'])

        r  = TargetResolver(self._config)
        us = resolve(r, ['gr1'])

        assert(' '.join(u.name for u in us) + '\n' == f.getvalue())

