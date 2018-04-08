# bdemeta.testing

import argparse
import glob
import itertools
import locale
import multiprocessing
import os
import subprocess
import signal
import sys

def parse_args(args):
    parser = argparse.ArgumentParser()
    for i in range(5):
        short = '-' + ('v' * (i + 1))
        long  = ('Very' * i) + 'Verbose'
        long  = '--' + (long[0].lower() + long[1:])
        parser.add_argument(short,
                            long,
                            action='store_const',
                            const=i,
                            dest='verbosity')
    return parser.parse_known_args(args)

class Runner:
    def __init__(self, log, verbosity=None):
        self._log       = log
        self._verbosity = verbosity

    def __call__(self, test):
        errors = False
        for case in itertools.count(1):
            try:
                command = [test, str(case)] + ['.'] * self._verbosity
                result = subprocess.check_output(command,
                                                 stderr=subprocess.STDOUT)
                if self._log:
                    print(f'{test}\tCASE:{case}\tPASS')
                if self._verbosity:
                    print(result.decode(locale.getpreferredencoding()))
            except subprocess.CalledProcessError as e:
                if e.returncode == 255:
                    break
                else:
                    output = e.output.decode(locale.getpreferredencoding())
                    message = f'{test}, CASE {case}'
                    message += '\n' + ('=' * len(message)) + '\n'
                    message += output + '\n'
                    sys.stderr.write(message)
                    errors = True
                    if self._log:
                        print(f'{test}\tCASE:{case}\tFAIL:{e.returncode}')
        return errors

def run_tests(tests, options):
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if len(tests) == 0:
        tests = glob.glob(os.path.join('.', '*.t'))

    if options.verbosity == None:
        runner = Runner(False)
    else:
        runner = Runner(True, options.verbosity)
    errors = multiprocessing.Pool().map(runner, sorted(tests))
    return 0 if not any(errors) else -1

