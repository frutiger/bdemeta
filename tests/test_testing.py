# tests.test_testing

import io
from unittest import TestCase

from bdemeta.testing import trim, run_one, RunResult, run_tests, MockRunner

def gen_value(length):
    result = ''
    for i in range(length):
        result += chr(ord('A') + (i % 26))
    return result

class TestMockRunner(TestCase):
    def test_no_cases(self):
        runner = MockRunner('')
        assert(RunResult.NO_SUCH_CASE == runner('foo'))
        assert(['foo']                == runner.commands)

    def test_one_success(self):
        runner = MockRunner('s')
        assert(RunResult.SUCCESS      == runner('foo'))
        assert(RunResult.NO_SUCH_CASE == runner('bar'))
        assert(['foo', 'bar']         == runner.commands)

    def test_one_failure(self):
        runner = MockRunner('f')
        assert(RunResult.FAILURE      == runner('foo'))
        assert(RunResult.NO_SUCH_CASE == runner('bar'))
        assert(['foo', 'bar']         == runner.commands)

    def test_one_success_one_failure(self):
        runner = MockRunner('sf')
        assert(RunResult.SUCCESS      == runner('foo'))
        assert(RunResult.FAILURE      == runner('bar'))
        assert(RunResult.NO_SUCH_CASE == runner('bam'))
        assert(['foo', 'bar', 'bam']  == runner.commands)

class TestTrim(TestCase):
    def test_short_string_unmodified(self):
        max_length = 20
        trail = '...'
        for length in range(max_length - len(trail)):
            value   = gen_value(length)
            trimmed = trim(value, max_length)
            assert(len(trimmed) < max_length)
            assert(value == value)

    def test_string_clipped(self):
        value = gen_value(20)
        trail = '...'
        for max_length in range(len(value) + len(trail) + 20):
            trimmed = trim(value, max_length)
            assert(len(trimmed) <= max_length)
            if len(value) <= max_length:
                assert(value == trimmed)
            elif max_length >= len(trail):
                assert(trimmed.endswith(trail))

class TestRunOne(TestCase):
    def test_driver_with_no_cases(self):
        runner = MockRunner('')
        test, errors = run_one((runner, 'foo', 'foo'))
        assert('foo' == test)
        assert(1 == len(runner.commands))
        assert(['foo', '1'] == runner.commands[0])
        assert(not errors)

    def test_driver_with_four_successes(self):
        runner = MockRunner('ssss')
        test, errors = run_one((runner, 'foo', 'foo'))
        assert('foo' == test)
        assert(5 == len(runner.commands))
        assert(['foo', '1'] == runner.commands[0])
        assert(['foo', '2'] == runner.commands[1])
        assert(['foo', '3'] == runner.commands[2])
        assert(['foo', '4'] == runner.commands[3])
        assert(['foo', '5'] == runner.commands[4])
        assert(not errors)

    def test_driver_with_one_failure(self):
        runner = MockRunner('f')
        test, errors = run_one((runner, 'foo', 'foo'))
        assert('foo' == test)
        assert(2 == len(runner.commands))
        assert(['foo', '1'] == runner.commands[0])
        assert(['foo', '2'] == runner.commands[1])
        assert(1 == len(errors))
        assert(1 in errors)

    def test_driver_with_mixed_successes_failures(self):
        runner = MockRunner('sfsf')
        test, errors = run_one((runner, 'foo', 'foo'))
        assert('foo' == test)
        assert(5 == len(runner.commands))
        assert(['foo', '1'] == runner.commands[0])
        assert(['foo', '2'] == runner.commands[1])
        assert(['foo', '3'] == runner.commands[2])
        assert(['foo', '4'] == runner.commands[3])
        assert(['foo', '5'] == runner.commands[4])
        assert(2 == len(errors))
        assert(2 in errors)
        assert(4 in errors)

class TestRun(TestCase):
    def test_single_success(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        runner = MockRunner('s')

        rc = run_tests(stdout, stderr, runner, lambda: 80, [["foo", "foo"]])
        assert(0 == rc)

        assert('\n' not in stderr.getvalue()[:-1])
        assert('foo' in stderr.getvalue())

    def test_single_failure(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        runner = MockRunner('f')

        rc = run_tests(stdout, stderr, runner, lambda: 80, [["foo", "foo"]])
        assert(1 == rc)

        assert('\n' not in stderr.getvalue()[:-1])
        assert('foo' in stderr.getvalue())

        failures = stdout.getvalue().split('\n')[:-1]
        assert(1 == len(failures))
        assert('FAIL TEST foo CASE 1' in failures)

    def test_two_drivers_four_successes_each(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        runner = MockRunner('ssss')

        rc = run_tests(stdout,
                       stderr,
                       runner,
                       lambda: 80,
                       [["foo", "foo"], ["bar", "bar"]])
        assert(0 == rc)

        assert('\n' not in stderr.getvalue()[:-1])
        assert('foo' in stderr.getvalue())
        assert('bar' in stderr.getvalue())

    def test_two_drivers_mixed_successes(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        runner = MockRunner('sfsf')

        rc = run_tests(stdout,
                       stderr,
                       runner,
                       lambda: 80,
                       [["foo", "foo"], ["bar", "bar"]])
        assert(1 == rc)

        assert('\n' not in stderr.getvalue()[:-1])
        assert('foo' in stderr.getvalue())
        assert('bar' in stderr.getvalue())

        failures = stdout.getvalue().split('\n')[:-1]
        assert(4 == len(failures))
        assert('FAIL TEST foo CASE 2' in failures)
        assert('FAIL TEST foo CASE 4' in failures)
        assert('FAIL TEST bar CASE 2' in failures)
        assert('FAIL TEST bar CASE 4' in failures)

