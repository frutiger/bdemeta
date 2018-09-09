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
from bdemeta.cmake   import Writer
from bdemeta.testing import Runner, RunResult

class NoConfigError(RuntimeError):
    pass

class InvalidArgumentsError(RuntimeError):
    pass

class InvalidPathError(RuntimeError):
    pass

def file_writer(name: str, writer: Callable[[TextIO], None]) -> None:
    with open(name, 'w') as f:
        writer(f)

def test_runner(command: List[str]) -> RunResult:
    # determine how '-1' will be returned by the OS
    if sys.platform == 'win32':
        minus_one = 2 ** 32 - 1
    else:
        minus_one = 2 ** 8 - 1

    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if e.returncode == minus_one:
            return RunResult.NO_SUCH_CASE
        else:
            return RunResult.FAILURE
    return RunResult.SUCCESS

def run(stdout:  TextIO,
        stderr:  TextIO,
        writer:  Writer,
        runner:  Runner,
        columns: int,
        args:    List[str]) -> int:
    if len(args) == 0:
        raise InvalidArgumentsError('No mode specified')

    mode = args[0]
    args = args[1:]

    if mode in { 'walk', 'dot', 'cmake' }:
        config_path = pathlib.Path('.bdemeta.conf')
        try:
            with config_path.open() as f:
                config = json.load(f)
        except FileNotFoundError:
            raise NoConfigError(config_path)

        config['roots'] = list(map(pathlib.Path, config['roots']))
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
        options, target_names = bdemeta.cmake.parse_args(args)
        targets = bdemeta.resolver.resolve(resolver, target_names)
        bdemeta.cmake.generate(targets, writer, options)
    elif mode == 'runtests':
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        tests = args or glob.glob(os.path.join('.', '*.t'))
        return bdemeta.testing.run_tests(stdout,
                                         stderr,
                                         runner,
                                         columns,
                                         tests)
    else:
        raise InvalidArgumentsError('Unknown mode \'{}\''.format(mode))
    return 0

def main(stdout:  TextIO    = sys.stdout,
         stderr:  TextIO    = sys.stderr,
         writer:  Writer    = file_writer,
         runner:  Runner    = test_runner,
         columns: int       = shutil.get_terminal_size().columns,
         args:    List[str] = sys.argv) -> int:
    try:
        return run(stdout, stderr, writer, runner, columns, args[1:])
    except InvalidArgumentsError as e:
        usage = '''{0}. Usage:

{1} walk     <target> [<target>...]
  walk and topologically sort dependencies

{1} dot      <target> [<target>...]
  generate a directed graph in the DOT language

{1} cmake    <target> [<target>...] [-t <target> ...]
  generate CMake files in the current directory

{1} runtests [-v] [<test>...]
  run unit tests'''

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

if __name__ == '__main__':  # pragma: no cover
    main()                  # pragma: no cover

