# bdemeta

import argparse
import glob
import json
import os.path
import pathlib
import shutil
import signal
import subprocess
import sys
from typing import Callable, List, TextIO

import bdemeta.cmake
import bdemeta.graph
import bdemeta.resolver
import bdemeta.testing
from bdemeta.testing import Runner, RunResult

class NoConfigError(RuntimeError):
    pass

class InvalidArgumentsError(RuntimeError):
    pass

class InvalidPathError(RuntimeError):
    pass

minus_one_rc = subprocess.run([sys.executable,
                               '-c',
                               'import sys; sys.exit(-1)']).returncode

exec_suffix = '.exe' if sys.platform == 'win32' else ''

def test_runner(command: List[str]) -> RunResult:
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if e.returncode == minus_one_rc:
            return RunResult.NO_SUCH_CASE
        else:
            return RunResult.FAILURE
    return RunResult.SUCCESS

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
    subparser.add_parser('cmake', parents=[resolving_parser],
                         help='generate a CMake lists file')
    runtest_parser = subparser.add_parser('runtests',
                                          help='run specified or discovered ' \
                                               'unit tests')
    runtest_parser.add_argument('tests', nargs='*', metavar='<test>',
                                help='test driver glob pattern')

    return parser

def run(stdout:      TextIO,
        stderr:      TextIO,
        runner:      Runner,
        get_columns: Callable[[], int],
        exec_suffix: str,
        raw_args:    List[str]) -> int:
    args = get_parser().parse_args(raw_args)

    if args.mode in { 'walk', 'dot', 'cmake' }:
        config_path = pathlib.Path(args.config)
        config_dir  = config_path.parent
        try:
            with config_path.open() as f:
                config = json.load(f)
        except FileNotFoundError:
            raise NoConfigError(config_path)

        result = []
        for root in config['roots']:
            path = pathlib.Path(root)
            if path.is_absolute():
                result.append(path)
            else:
                result.append(config_dir/path)
        config['roots'] = result

        for root in config['roots']:
            if not root.is_dir():
                raise InvalidPathError(root)

        resolver = bdemeta.resolver.TargetResolver(config,
                                                   args.incl_test_deps)

    if args.mode == 'walk':
        targets = bdemeta.resolver.resolve(resolver, args.targets)
        print(' '.join(t.name for t in targets), file=stdout)
        return 0
    elif args.mode == 'dot':
        targets = bdemeta.resolver.resolve(resolver, args.targets)
        print('digraph G {', file=stdout)
        for t in targets:
            for d in resolver.dependencies(t.name):
                print(f'    "{t.name}" -> "{d}"', file=stdout)
        print('}', file=stdout)
        return 0
    elif args.mode == 'cmake':
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
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        return bdemeta.testing.run_tests(stdout,
                                         stderr,
                                         runner,
                                         get_columns,
                                         tests)

def main(stdout:      TextIO            = sys.stdout,
         stderr:      TextIO            = sys.stderr,
         runner:      Runner            = test_runner,
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

if __name__ == '__main__':
    main()

