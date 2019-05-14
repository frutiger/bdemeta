# Contributing

Contributions in the form of issues and pull requests are greatly appreciated.

## Licensing Agreement

Please sign the <a
href="https://www.clahub.com/agreements/frutiger/bdemeta">sign the Contributor
License Agreement</a>.  It asks you to authorize the transfer of copyright
ownership of all contributions to this project to the original author of the
project (Mashud Rahman).

## Tests, Typing and Coverage

All changes must be accompanied by tests which cover the new functionality, and
all code must be completely typed.  Run the following commands to verify:

    $ python3 -m unittest
    $ mypy -p bdemeta -m tests.cmake_parser

## Raising issues

Please verify that the tests pass before raising an issue.  Failing tests on
Python 3.6 or newer is an issue in its own right.

## Creating pull requests

Please submit only one bugfix or enhancement per pull request, and please add a
test case for the feature you are fixing/improving.

