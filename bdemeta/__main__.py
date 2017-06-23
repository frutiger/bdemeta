# bdemeta

import collections
import json
import os.path
import sys

import bdemeta.graph
import bdemeta.cmake
import bdemeta.resolver
import bdemeta.testing

def parse_config(filename):
    if os.path.isfile(filename):
        with open(filename) as f:
            return json.load(f)
    else:
        return {}

class InvalidArgumentsError(RuntimeError):
    def __init__(self, message):
        self.message = message

def file_writer(name, writer):
    with open(name, 'w') as f:
        writer(f)

def run(output, args):
    config = parse_config('.bderoots.conf')
    resolver = bdemeta.resolver.UnitResolver(config)

    if len(args) == 0:
        raise InvalidArgumentsError('No mode specified')

    mode = args[0]
    args = args[1:]

    if mode == 'walk':
        units = bdemeta.resolver.resolve(resolver, args)
        print(' '.join(units), file=output)
    elif mode == 'cmake':
        options, units = bdemeta.cmake.parse_args(args)
        units = bdemeta.resolver.resolve(resolver, units)
        bdemeta.cmake.generate(units, file_writer, options)
    elif mode == 'runtests':
        bdemeta.testing.runtests(args)
    else:
        raise InvalidArgumentsError('Unknown mode \'{}\''.format(mode))

def main():
    try:
        run(sys.stdout, sys.argv[1:])
    except InvalidArgumentsError as e:
        usage = '''{0}. Usage:

{1} walk     <unit> [<unit>...]
  walk and topologically sort dependencies

{1} cmake    <unit> [<unit>...] [-t <unit> ...]
  generate CMake files in the current directory

{1} runtests [<test>...]
  run unit tests'''

        print(usage.format(e.message, os.path.basename(sys.argv[0])),
              file=sys.stderr)
        return -1
    except bdemeta.graph.CyclicGraphError as e:
        print('Cyclic dependency error: {}'.format(' -> '.join(e.cycle)),
              file=sys.stderr)
        return -1
    except bdemeta.resolver.TargetNotFoundError as e:
        print('Could not find target:', e.args[0], file=sys.stderr)
        return -1

if __name__ == '__main__':
    main()
