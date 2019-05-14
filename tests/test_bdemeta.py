# tests.test_bdemeta

import shutil
import sys
from io       import StringIO
from pathlib  import Path as P
from tempfile import TemporaryDirectory
from unittest import TestCase

from bdemeta.__main__ import InvalidArgumentsError, InvalidPathError, \
                             NoConfigError, run, main, file_writer,   \
                             test_runner, get_columns
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

class NoConfigErrorTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({})

    def tearDown(self):
        self._patcher.reset()

    def test_no_config_error(self):
        with self.assertRaises(NoConfigError):
            run(None, None, None, None, None, ['walk', 'foo'])

        stderr = StringIO()
        main(None, stderr, None, None, None, [__name__, 'walk', 'foo'])
        assert(stderr.getvalue())

    def test_args_error_if_config_unneeded(self):
        with self.assertRaises(InvalidArgumentsError):
            run(None, None, None, None, None, [])

        stderr = StringIO()
        main(None, stderr, None, None, None, [__name__])
        assert(stderr.getvalue())

class InvalidPathErrorTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher({
            '.bdemeta.conf': '{ "roots": ["unlikely_path_that_exists"] }',
        })

    def tearDown(self):
        self._patcher.reset()

    def test_invalid_path_error(self):
        with self.assertRaises(InvalidPathError):
            run(None, None, None, None, None, ['walk', 'foo'])

        stderr = StringIO()
        main(None, stderr, None, None, None, [__name__, 'walk', 'foo'])
        assert(stderr.getvalue())

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
        with self.assertRaises(InvalidArgumentsError) as e:
            run(None, None, None, None, None, [])
        assert('No mode specified' == e.exception.args[0])

    def test_unknown_mode_error(self):
        with self.assertRaises(InvalidArgumentsError) as e:
            run(None, None, None, None, None, ['foo'])
        assert('Unknown mode \'{}\''.format('foo') == e.exception.args[0])

    def test_target_with_dependencies(self):
        f = StringIO()
        run(f, None, None, None, None, ['walk', 'gr2'])

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
        with self.assertRaises(InvalidPathError) as e:
            run(None, None, None, None, None, ['walk'])
        assert(P('r') == e.exception.args[0])

    def test_no_root_main_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout, stderr, None, None, None, [__name__, 'walk', 'p1'])
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
        run(f, None, None, None, None, ['dot', 'p2'])
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

        run(output, None, w1, None, None, ['cmake', 'p'])

        r  = TargetResolver(self._config)
        p  = resolve(r, 'p')
        f2 = {}
        w2 = get_filestore_writer(f2)
        generate(p, w2)

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
        main(stdout, None, None, None, None, [None, 'walk', 'p2'])
        assert('p2 p1\n' == stdout.getvalue())

    def test_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout, stderr, None, None, None, [__name__, 'foo'])
        assert(not stdout.getvalue())
        assert(stderr.getvalue())

    def test_cyclic_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout, stderr, None, None, None, [__name__, 'walk', 'p3'])
        assert(not stdout.getvalue())
        assert(stderr.getvalue())
        assert('p3' in stderr.getvalue())
        assert('p4' in stderr.getvalue())

    def test_not_found_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout, stderr, None, None, None, [__name__, 'walk', 'p5'])
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
        main(stdout, stderr, None, None, None, [__name__])
        assert(not stdout.getvalue())
        assert(stderr.getvalue())

    def test_no_config_error(self):
        stdout = StringIO()
        stderr = StringIO()
        main(stdout, stderr, None, None, None, [__name__, 'walk', 'p1'])
        assert(not stdout.getvalue())
        assert(stderr.getvalue())

class FileWriterTest(TestCase):
    def test_file_writer(self):
        content = "hello world"
        def write(f):
            f.write(content)
        with TemporaryDirectory() as d:
            path = P(d)/'foo'
            file_writer(path, write)
            with open(path) as f:
                assert(f.read() == content)

class RunTestTest(TestCase):
    def test_running_tests(self):
        stdout1 = StringIO()
        stderr1 = StringIO()
        runner1 = MockRunner('sfsf')
        main(stdout1,
             stderr1,
             None,
             runner1,
             lambda: 80,
             [__name__, 'runtests', 'foo'])

        stdout2 = StringIO()
        stderr2 = StringIO()
        runner2 = MockRunner('sfsf')
        run_tests(stdout2, stderr2, runner2, lambda: 80, ['foo'])

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

