from __future__ import print_function

import io
import json
import locale
import os
import sys
from collections import defaultdict

import bdemeta.resolver
import bdemeta.commands
import bdemeta.config

def parse_config(filename):
    if os.path.isfile(filename):
        with io.open(filename) as f:
            return json.load(f)
    else:
        return {}

def run(output, args):
    user_config  = parse_config(os.path.expanduser('~/.bdemetarc'))
    local_config = parse_config('.bdemetarc')

    merge  = bdemeta.config.merge
    config = merge(merge({
        'roots': [],
        'ninja': {
            'cc':  u'cc',
            'c++': u'c++',
            'ar':  u'ar',
        },
        'cflags':       defaultdict(list),
        'ldflags':      defaultdict(list),
        'dependencies': defaultdict(list),
    }, user_config), local_config)

    resolver = bdemeta.resolver.Resolver(config)

    if sys.version_info.major < 3:
        # Convert arguments to 'unicode' on pre-Python 3
        args = [arg.decode(locale.getpreferredencoding()) for arg in args]

    mode = args[0] if len(args) > 1 else None

    if   mode == 'walk':
        groups = frozenset(resolver(unit) for unit in args[1:])
        print(bdemeta.commands.walk(groups), file=output)
    elif mode == 'cflags':
        groups = frozenset(resolver(unit) for unit in args[1:])
        print(bdemeta.commands.cflags(groups), file=output)
    elif mode == 'ldflags':
        groups = frozenset(resolver(unit) for unit in args[1:])
        print(bdemeta.commands.ldflags(groups), file=output)
    elif mode == 'ninja':
        groups = frozenset(resolver(unit) for unit in args[1:])
        bdemeta.commands.ninja(groups, config['ninja'], output)
    elif mode == 'runtests':
        bdemeta.commands.runtests(args[1:])
    else:
        raise RuntimeError('Unknown mode, should be one of: walk, cflags '
                           'ldflags, ninja, runtests')

def main():
    run(sys.stdout, sys.argv[1:])

