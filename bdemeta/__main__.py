# bdemeta

import argparse
import json
import pathlib
import shlex
import shutil
import signal
import sys
from typing import Callable, List, TextIO

import bdemeta.cmake
import bdemeta.graph
import bdemeta.resolver
import bdemeta.testing
from bdemeta.resolver import InvalidPathError, normalize_roots
from bdemeta.testing import Runner

class NoConfigError(RuntimeError):
    pass

class InvalidArgumentsError(RuntimeError):
    pass

exec_suffix = '.exe' if sys.platform == 'win32' else ''

def get_columns() -> int:
    return shutil.get_terminal_size().columns

class CustomFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action(self, action: argparse.Action) -> str:
        result = super()._format_action(action)
        if action.nargs == argparse.PARSER:
            # since we aren't showing the subcommand group, de-indent by 2
            # spaces
            lines = result.split('\n')
            lines = [line[2:] for line in lines]
            result = '\n'.join(lines)
        return result

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=CustomFormatter)

    resolving_parser = argparse.ArgumentParser(add_help=False)
    resolving_parser.add_argument('-t', '--test-deps',
                                  action='store_true',
                                  dest='incl_test_deps',
                                  help='include test dependencies')
    resolving_parser.add_argument('config', metavar='<config>',
                                  help='configuration file')
    resolving_parser.add_argument('targets', nargs='+', metavar='<target>',
                                  help='build target')

    subparser = parser.add_subparsers(dest='mode', required=True,
                                      metavar='<mode>', title=argparse.SUPPRESS)
    subparser.add_parser('walk', parents=[resolving_parser],
                         help='walk and topologically sort dependencies')
    subparser.add_parser('dot', parents=[resolving_parser],
                         help='generate a directed graph in the DOT language')
    cmake_parser = subparser.add_parser('cmake', parents=[resolving_parser],
                                        help='generate a CMake lists file')
    cmake_parser.add_argument('-p', '--plugin-tests',
                              action='store_true',
                              help='build tests as plugins')
    runtest_parser = subparser.add_parser('runtests',
                                          help='run specified or discovered ' \
                                               'unit tests')
    runtest_parser.add_argument('-e', '--executor', metavar='<executor>',
                                help='custom test executor')
    runtest_parser.add_argument('-m', '--max-cases', metavar='<maximum cases>',
                                type=int, default=100,
                                help='maximum cases to attempt per driver')
    runtest_parser.add_argument('tests', nargs='*', metavar='<test>',
                                help='test driver glob pattern')

    return parser

def make_resolver(config_path_str: str,
                  incl_test_deps: bool,
                  plugin_tests: bool) -> bdemeta.resolver.TargetResolver:
    config_path = pathlib.Path(config_path_str)
    config_dir  = config_path.parent
    try:
        with config_path.open() as f:
            config = json.load(f)
    except FileNotFoundError:
        raise NoConfigError(config_path)

    config['roots'] = normalize_roots(config['roots'], config_dir)
    if 'conan_roots' in config:
        config['conan_roots'] = normalize_roots(config['conan_roots'], config_dir)

    return bdemeta.resolver.TargetResolver(config,
                                           incl_test_deps,
                                           plugin_tests)

def run(stdout:      TextIO,
        stderr:      TextIO,
        runner:      Runner,
        get_columns: Callable[[], int],
        exec_suffix: str,
        raw_args:    List[str]) -> int:
    args = get_parser().parse_args(raw_args)

    if args.mode == 'walk':
        resolver = make_resolver(args.config,
                                 args.incl_test_deps,
                                 getattr(args, 'plugin_tests', False))
        targets = bdemeta.resolver.resolve(resolver, args.targets)
        print(' '.join(t.name for t in targets), file=stdout)
        return 0
    elif args.mode == 'dot':
        resolver = make_resolver(args.config,
                                 args.incl_test_deps,
                                 getattr(args, 'plugin_tests', False))
        targets = bdemeta.resolver.resolve(resolver, args.targets)
        print('digraph G {', file=stdout)
        for t in targets:
            for d in resolver.dependencies(t.name):
                print(f'    "{t.name}" -> "{d}"', file=stdout)
        print('}', file=stdout)
        return 0
    elif args.mode == 'cmake':
        resolver = make_resolver(args.config,
                                 args.incl_test_deps,
                                 getattr(args, 'plugin_tests', False))
        targets = bdemeta.resolver.resolve(resolver, args.targets)
        bdemeta.cmake.generate(targets, stdout)
        return 0
    else:
        assert(args.mode == 'runtests')
        if args.tests:
            patterns = args.tests
        else:
            patterns = [f'*.t{exec_suffix}']
        tests = []
        for pattern in patterns:
            for test in pathlib.Path('.').glob(pattern):
                tests.append((str(test), str(test.resolve())))

        if args.executor:
            executor = shlex.split(args.executor,
                                   posix=sys.platform != "win32")
        else:
            executor = []

        signal.signal(signal.SIGINT, signal.SIG_DFL)
        return bdemeta.testing.run_tests(stdout,
                                         stderr,
                                         runner,
                                         executor,
                                         get_columns,
                                         tests,
                                         args.max_cases)

def main(stdout:      TextIO            = sys.stdout,
         stderr:      TextIO            = sys.stderr,
         runner:      Runner            = bdemeta.testing.test_runner,
         get_columns: Callable[[], int] = get_columns,
         exec_suffix: str               = exec_suffix,
         args:        List[str]         = sys.argv) -> int:
    try:
        return run(stdout, stderr, runner, get_columns, exec_suffix, args[1:])
    except NoConfigError as e:
        print(f'Could not find config at: {e.args[0]}', file=stderr)
    except InvalidPathError as e:
        print(f'Unknown path found in configuration file: {e.args[0]}',
              file=stderr)
    except bdemeta.graph.CyclicGraphError as e:
        print('Cyclic dependency error: {}'.format(' -> '.join(e.cycle)),
              file=stderr)
        return -1
    except bdemeta.resolver.TargetNotFoundError as e:
        print('Could not find target:', e.args[0], file=stderr)
        return -1
    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())

