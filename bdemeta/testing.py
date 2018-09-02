# bdemeta.testing

import glob
import itertools
import locale
import multiprocessing
import os
import subprocess
import signal
import sys

def runner(test):
    num_cases = 0
    errors    = set()
    for case in itertools.count(1):
        num_cases += 1
        command    = [test, str(case)]
        try:
            subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            if e.returncode == 255:
                num_cases -= 1
                break
            else:
                errors.add(case)
    return test, num_cases, errors

def trimpad(name, length=40, ellipsis='...'):
    max_length = length - len(ellipsis)
    if len(name) > length:
        return name[max_length] + '...'
    else:
        return name[:length] + (' ' * (length - len(name)))

def run_tests(tests):
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    tests = tests or glob.glob(os.path.join('.', '*.t'))

    num_drivers = len(tests) # all test drivers
    run_drivers = 0          # drivers run so far
    bad_drivers = 0          # drivers with errors so far
    num_cases   = 0          # cases run so far
    bad_cases   = 0          # cases with errors so far

    jobs       = multiprocessing.Pool().imap_unordered(runner, tests)
    any_errors = False
    all_errors = {}
    for test, cases, errors in jobs:
        run_drivers += 1
        num_cases   += cases
        if errors:
            any_errors = True
            all_errors[test] = errors

        trimmed     = trimpad(test)
        drivers_pct = 100 * run_drivers / num_drivers
        message = f'\r[{drivers_pct:>4.1f}%] '        \
                  f'{run_drivers:4}/{num_drivers:4} ' \
                  f'[{trimmed}]'
        print(message, end='', file=sys.stderr)
    print()

    for test, errors in all_errors.items():
        for error in errors:
            print(f'FAIL TEST {test} CASE {error}')
    return 1 if any_errors else 0

