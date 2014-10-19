# bdemeta.testing

import glob
import itertools
import multiprocessing
import os
import subprocess
import signal

def runtest(test):
    for case in itertools.count():
        rc = subprocess.call((test, str(case)))
        if rc == 0:
            continue
        elif rc == 255:
            break
        else:
            raise RuntimeError('{test} case {case} failed'.format(test = test,
                                                                  case = case))

def runtests(tests):
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if len(tests) == 0:
        tests = glob.glob(os.path.join('out', 'tests', '*'))
    else:
        tests = [os.path.join('out', 'tests', t) for t in tests]

    multiprocessing.Pool().map(runtest, sorted(tests))


