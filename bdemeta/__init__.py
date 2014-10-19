# bdemeta

from __future__ import print_function

import collections
import io
import itertools
import json
import locale
import os.path
import sys

import bdemeta.config
import bdemeta.graph
import bdemeta.ninja
import bdemeta.resolver
import bdemeta.testing
import bdemeta.types

def parse_config(filename):
    if os.path.isfile(filename):
        with io.open(filename) as f:
            return json.load(f)
    else:
        return {}

class InvalidArgumentsError(RuntimeError):
    def __init__(self, message):
        self.message = message

def run(output, args):
    user_config  = parse_config(os.path.expanduser('~/.bdemetarc'))
    local_config = parse_config('.bdemetarc')

    unit_options = lambda: { 'internal_cflags': [],
                             'external_cflags': [],
                             'ld_args':         [],
                             'deps':            [], }
    config = {
        'roots': [],
        'ninja': {
            'cc':  '',
            'c++': '',
            'ar':  '',
        },
        'units': collections.defaultdict(unit_options),
    }
    config = bdemeta.config.merge(config, user_config)
    config = bdemeta.config.merge(config, local_config)

    resolver = bdemeta.resolver.Resolver(config)

    if sys.version_info.major < 3:
        # Convert arguments to 'unicode' on pre-Python 3
        args = [arg.decode(locale.getpreferredencoding()) for arg in args]

    if len(args) == 0:
        raise InvalidArgumentsError('No mode specifed')

    mode = args[0]
    args = args[1:]

    if mode == 'walk':
        units = resolver(args)
        targets = [t for t in units if isinstance(t, bdemeta.types.Target)]
        print(' '.join(targets), file=output)
    elif mode == 'cflags':
        units = resolver(args)
        print(' '.join(itertools.chain(*[u.cflags() for u in units])),
              file=output)
    elif mode == 'ninja':
        if config['ninja']['cc'] == '':
            config['ninja']['cc'] = 'cc'
        if config['ninja']['c++'] == '':
            config['ninja']['c++'] = 'c++'
        if config['ninja']['ar'] == '':
            config['ninja']['ar'] = 'ar'
        units = resolver(args)
        targets = [t for t in units if isinstance(t, bdemeta.types.Target)]
        bdemeta.ninja.generate(targets, config['ninja'], output)
    elif mode == 'runtests':
        bdemeta.testing.runtests(args)
    else:
        raise InvalidArgumentsError('Unknown mode \'{}\''.format(mode))

def main():
    try:
        run(sys.stdout, sys.argv[1:])
    except InvalidArgumentsError as e:
        usage = '''{0}. Usage:

{1} walk     <unit> [<unit>...] - walk and topologically sort dependencies
{1} cflags   <unit> [<unit>...] - produce flags for compiling dependents
{1} ninja    <unit> [<unit>...] - generate a ninja build for building units
{1} runtests [<test>...]        - run unit tests'''

        print(usage.format(e.message, os.path.basename(sys.argv[0])),
              file=sys.stderr)
        return -1
    except bdemeta.graph.CyclicGraphError as e:
        print('Cyclic dependency error: {}'.format(' -> '.join(e.cycle)),
              file=sys.stderr)
        return -1

