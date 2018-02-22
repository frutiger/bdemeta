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
    parser.add_argument('-v', '--verbose', action='store_true')
    return parser.parse_known_args(args)

def run_test(test, is_verbose):
    errors = False
    for case in itertools.count(1):
        try:
            command = [test, str(case)]
            result = subprocess.check_output(command, stderr=subprocess.STDOUT)
            if is_verbose:
                print(f'{test}\tCASE:{case}\tPASS')
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
                if is_verbose:
                    print(f'{test}\tCASE:{case}\tFAIL:{e.returncode}')
    return errors

def run_verbose(test):
    return run_test(test, True)

def run_silent(test):
    return run_test(test, False)

def run_tests(tests, options):
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if len(tests) == 0:
        tests = glob.glob(os.path.join('.', '*.t'))

    runner = run_verbose if options.verbose else run_silent
    errors = multiprocessing.Pool().map(runner, sorted(tests))
    return 0 if not any(errors) else -1

