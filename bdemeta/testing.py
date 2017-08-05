# bdemeta.testing

import glob
import itertools
import locale
import multiprocessing
import os
import subprocess
import signal
import sys

def runtest(test):
    errors = False
    for case in itertools.count(1):
        try:
            command = [test, str(case)]
            subprocess.check_output(command, stderr=subprocess.STDOUT)
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
    return errors

def runtests(tests):
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if len(tests) == 0:
        tests = glob.glob(os.path.join('.', '*.t'))

    errors = multiprocessing.Pool().map(runtest, sorted(tests))
    return 0 if not any(errors) else -1

