# bdemeta.testing

import enum
import multiprocessing
from typing import Callable, List, Set, TextIO, Tuple

class RunResult(enum.Enum):
    SUCCESS      = enum.auto()
    FAILURE      = enum.auto()
    NO_SUCH_CASE = enum.auto()

Runner = Callable[[List[str]], RunResult]

class MockRunner:
    def __init__(self, behaviour: str) -> None:
        self.commands: List[List[str]] = []
        self._behaviour                = behaviour
        self._run                      = 0

    def __call__(self, command: List[str]) -> RunResult:
        self.commands.append(command)
        if self._run >= len(self._behaviour):
            return RunResult.NO_SUCH_CASE
        code = self._behaviour[self._run]
        self._run += 1
        return RunResult.SUCCESS if code == 's' else RunResult.FAILURE

def trim(value: str, max_length: int, trail: str='...') -> str:
    if len(trail) >= max_length:
        return trail[:max_length]
    if len(value) <= max_length:
        return value
    return value[:max_length - len(trail)] + trail

def run_one(args: Tuple[Runner, str]) -> Tuple[str, Set[int]]:
    runner, test = args
    errors = set()
    case   = 1
    while True:
        command = [test, str(case)]
        result  = runner(command)
        if result == RunResult.FAILURE:
            errors.add(case)
        elif result == RunResult.NO_SUCH_CASE:
            break
        case += 1
    return test, errors

def run_tests(stdout:  TextIO,
              stderr:  TextIO,
              runner:  Runner,
              columns: int,
              tests:   List[str]) -> int:
    status_format = '[{run_drivers}/{num_drivers}] {test}'

    num_drivers = len(tests) # all test drivers
    run_drivers = 0          # drivers run so far

    args   = [(runner, t) for t in tests]
    jobs   = multiprocessing.Pool().imap_unordered(run_one, args)
    errors = {}
    for test, test_errors in jobs:
        run_drivers    += 1
        if test_errors:
            errors[test] = test_errors

        message  = '\r' + ' ' * columns + '\r'
        message += trim(status_format.format(**locals()), columns)
        print(message, end='', file=stderr, flush=True)
    print(file=stderr, flush=True)

    for test, test_errors in errors.items():
        for error in test_errors:
            print(f'FAIL TEST {test} CASE {error}', file=stdout)
    return 1 if errors else 0

