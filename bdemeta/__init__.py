from __future__ import print_function

import argparse
import os
import sys
from collections import defaultdict

import bdemeta.resolver
import bdemeta.commands

def get_parser():
    parser = argparse.ArgumentParser(description='build and test BDE-style '
                                                 'code');
    parser.add_argument('--root',
                         action='append',
                         metavar='ROOT',
                         dest='roots',
                         default=[],
                         help='Add the specified ROOT to the package '
                              'group search path')

    parser.add_argument('--dependency',
                         action='append',
                         metavar='NAME:DEPENDENCY',
                         dest='dependencies',
                         default=[],
                         help='Consider the specified NAME to have the '
                              'specified DEPENDENCY.')

    parser.add_argument('--cflag',
                         action='append',
                         metavar='NAME:FLAG',
                         dest='cflags',
                         default=[],
                         help='Append the specified FLAG when generating '
                              'cflags for the dependency with the specified '
                              'NAME.')

    parser.add_argument('--ldflag',
                         action='append',
                         metavar='NAME:FLAG',
                         dest='ldflags',
                         default=[],
                         help='Append the specified FLAG when generating '
                              'ldflags for the dependency with the specified '
                              'NAME.')

    subparser = parser.add_subparsers(metavar='MODE')

    walk_parser = subparser.add_parser('walk',
                                        help='Walk and topologically sort '
                                             'dependencies',
                                        description='Print the list of '
                                                    'dependencies of the '
                                                    'specified GROUPs in '
                                                    'topologically sorted '
                                                    'order')
    walk_parser.add_argument('groups', nargs='+', metavar='GROUP')
    walk_parser.set_defaults(mode='walk')

    cflags_parser = subparser.add_parser('cflags',
                                          help='Produce cflags for compiling '
                                               'dependents',
                                          description='Produce flags that '
                                                      'will allow a '
                                                      'compilation unit '
                                                      'depending on the '
                                                      'specified GROUPs to '
                                                      'compile correctly')
    cflags_parser.add_argument('groups', nargs='+', metavar='GROUP')
    cflags_parser.set_defaults(mode='cflags')

    ldflags_parser = subparser.add_parser('ldflags',
                                           help='Produce flags for linking '
                                                'dependents',
                                           description='Produce flags that '
                                                       'will allow a '
                                                       'compilation unit '
                                                       'depending on the '
                                                       'specified GROUPs to '
                                                       'link correctly')
    ldflags_parser.add_argument('groups', nargs='+', metavar='GROUP')
    ldflags_parser.set_defaults(mode='ldflags')

    ninja_parser = subparser.add_parser('ninja',
                                         help='Generate a ninja build file',
                                         description='Generate a ninja build '
                                                     'file that will build '
                                                     'statically linked '
                                                     'libraries and tests for '
                                                     'the specified GROUPs '
                                                     'and all dependent '
                                                     'groups')
    ninja_parser.add_argument('groups', nargs='+', metavar='GROUP')
    ninja_parser.add_argument('--cc',
                               default='cc',
                               help='Use the specified CC as the C compiler '
                                    'to build objects and linker to build '
                                    'tests')
    ninja_parser.add_argument('--cxx',
                               default='c++',
                               help='Use the specified CXX as the C++ '
                                    'compiler to build objects and linker to '
                                    'build tests')
    ninja_parser.add_argument('--ar',
                               default='ar',
                               help='Use the specified AR as the archiver '
                                    'to build static libraries')
    ninja_parser.set_defaults(mode='ninja')

    runtests_parser = subparser.add_parser('runtests',
                                            help='Run BDE-style unit tests',
                                            description='Run all of the '
                                                        'optionally specified '
                                                        'BDE-style TESTs '
                                                        'found in '
                                                        '\'out/tests\'; if '
                                                        'none are specified, '
                                                        'then run all the '
                                                        'tests in that '
                                                        'directory')
    runtests_parser.add_argument('tests', nargs='*', metavar='TEST')
    runtests_parser.set_defaults(mode='runtests')

    return parser

def parse_args(args):
    def args_from_file(filename):
        if os.path.isfile(filename):
            with open(filename) as f:
                options = [l[:-1] for l in f.readlines() if l[0] != '#']
                return ' '.join(options).split()
        return []

    args = args_from_file(os.path.expanduser('~/.bdemetarc')) + \
                                           args_from_file('.bdemetarc') + args

    parser = get_parser()
    args   = parser.parse_args(args=args)

    if not hasattr(args, 'mode'):
        parser.print_usage()
        print('{}: error: too few arguments'.format(sys.argv[0]))
        sys.exit(-1)

    def set_user_options(args, kind, type):
        result = defaultdict(type)
        for value in getattr(args, kind):
            if len(value.split(':')) < 2:
                raise RuntimeError('flag value should be NAME:{}'.format(
                                                                 kind.upper()))

            name, option = value.split(':')
            result[name].append(option)
        delattr(args,  kind)
        setattr(args, 'user_' + kind, result)

    set_user_options(args, 'dependencies', frozenset)
    set_user_options(args, 'cflags',       list)
    set_user_options(args, 'ldflags',      list)

    setattr(args, 'user_flags', defaultdict(lambda: {'c': [], 'ld': []}))
    for unit in args.user_cflags:
        args.user_flags[unit]['c']  = args.user_cflags[unit]
    for unit in args.user_ldflags:
        args.user_flags[unit]['ld'] = args.user_ldflags[unit]
    delattr(args, 'user_cflags')
    delattr(args, 'user_ldflags')

    return args

def run(output, args):
    args     = parse_args(args)
    resolver = bdemeta.resolver.Resolver(args.roots,
                        args.user_dependencies,
                        args.user_flags)

    if hasattr(args, 'groups'):
        groups = frozenset(resolver(unit) for unit in args.groups)

    if   args.mode == 'walk':
        print(bdemeta.commands.walk(groups), file=output)
    elif args.mode == 'cflags':
        print(bdemeta.commands.flags(groups, 'c'), file=output)
    elif args.mode == 'ldflags':
        print(bdemeta.commands.flags(groups, 'ld'), file=output)
    elif args.mode == 'ninja':
        bdemeta.commands.ninja(groups, args.cc, args.cxx, args.ar, output)
    elif args.mode == 'runtests':
        bdemeta.commands.runtests(args.tests)
    else:
        raise RuntimeError('Unknown mode')

def main():
    run(sys.stdout, sys.argv[1:])

