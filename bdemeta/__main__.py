# bdemeta

import collections
import json
import os.path
import pathlib
import sys
from typing import Callable, TextIO, List

import bdemeta.graph
import bdemeta.cmake
import bdemeta.resolver
import bdemeta.testing

class NoConfigError(RuntimeError):
    pass

class InvalidArgumentsError(RuntimeError):
    pass

class InvalidPathError(RuntimeError):
    pass

def file_writer(name: str, writer: Callable[[TextIO], None]) -> None:
    with open(name, 'w') as f:
        writer(f)

def run(output: TextIO, args: List[str]) -> int:
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

    if len(args) == 0:
        raise InvalidArgumentsError('No mode specified')

    mode = args[0]
    args = args[1:]

    if mode == 'walk':
        targets = bdemeta.resolver.resolve(resolver, args)
        print(' '.join(t.name for t in targets), file=output)
    elif mode == 'dot':
        targets = bdemeta.resolver.resolve(resolver, args)
        print('digraph G {')
        for t in targets:
            for d in resolver.dependencies(t.name):
                print(f'   "{t}" -> "{d}"')
        print('}')
    elif mode == 'cmake':
        options, target_names = bdemeta.cmake.parse_args(args)
        targets = bdemeta.resolver.resolve(resolver, target_names)
        bdemeta.cmake.generate(targets, file_writer, options)
    elif mode == 'runtests':
        return bdemeta.testing.run_tests(args)
    else:
        raise InvalidArgumentsError('Unknown mode \'{}\''.format(mode))
    return 0

def main() -> int:
    try:
        return run(sys.stdout, sys.argv[1:])
    except InvalidArgumentsError as e:
        usage = '''{0}. Usage:

{1} walk     <target> [<target>...]
  walk and topologically sort dependencies

{1} cmake    <target> [<target>...] [-t <target> ...]
  generate CMake files in the current directory

{1} runtests [-v] [<test>...]
  run unit tests'''

        print(usage.format(e.args[0], os.path.basename(sys.argv[0])),
              file=sys.stderr)
        return -1
    except NoConfigError as e:
        print(f'Could not find config at: {e.args[0]}')
    except InvalidPathError as e:
        print(f'Unknown path found in .bderoots.conf: {e.args[0]}')
    except bdemeta.graph.CyclicGraphError as e:
        print('Cyclic dependency error: {}'.format(' -> '.join(e.cycle)),
              file=sys.stderr)
        return -1
    except bdemeta.resolver.TargetNotFoundError as e:
        print('Could not find target:', e.args[0], file=sys.stderr)
        return -1
    return 0

if __name__ == '__main__':
    main()
