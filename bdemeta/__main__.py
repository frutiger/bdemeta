# bdemeta

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

def run(stdout:      TextIO,
        stderr:      TextIO,
        runner:      Runner,
        get_columns: Callable[[], int],
        args:        List[str]) -> int:
    if len(args) == 0:
        raise InvalidArgumentsError('No mode specified')

    mode = args[0]
    args = args[1:]

    if mode in { 'walk', 'dot', 'cmake' }:
        if len(args) == 0:
            raise InvalidArgumentsError('No config specified')
        config_path = pathlib.Path(args[0])
        config_dir  = config_path.parent
        args        = args[1:]
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

        resolver = bdemeta.resolver.TargetResolver(config)

    if mode == 'walk':
        targets = bdemeta.resolver.resolve(resolver, args)
        print(' '.join(t.name for t in targets), file=stdout)
    elif mode == 'dot':
        targets = bdemeta.resolver.resolve(resolver, args)
        print('digraph G {', file=stdout)
        for t in targets:
            for d in resolver.dependencies(t.name):
                print(f'    "{t.name}" -> "{d}"', file=stdout)
        print('}', file=stdout)
    elif mode == 'cmake':
        targets = bdemeta.resolver.resolve(resolver, args)
        bdemeta.cmake.generate(targets, stdout)
    elif mode == 'runtests':
        patterns = args or ['*.t']
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
    else:
        raise InvalidArgumentsError('Unknown mode \'{}\''.format(mode))
    return 0

def main(stdout:      TextIO            = sys.stdout,
         stderr:      TextIO            = sys.stderr,
         runner:      Runner            = test_runner,
         get_columns: Callable[[], int] = get_columns,
         args:        List[str]         = sys.argv) -> int:
    try:
        return run(stdout, stderr, runner, get_columns, args[1:])
    except InvalidArgumentsError as e:
        usage = '''{0}. Usage:

{1} walk     <config> <target> [<target>...]
  walk and topologically sort dependencies

{1} dot      <config> <target> [<target>...]
  generate a directed graph in the DOT language

{1} cmake    <config> <target> [<target>...]
  generate a CMake lists file

{1} runtests [<test>...]
  run specified or discovered unit tests'''

        print(usage.format(e.args[0], os.path.basename(args[0])),
              file=stderr)
        return -1
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

