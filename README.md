[![CI](https://github.com/frutiger/bdemeta/workflows/CI/badge.svg)](https://github.com/frutiger/bdemeta/actions?query=workflow%3ACI)
[![Coverage](https://codecov.io/gh/frutiger/bdemeta/branch/master/graph/badge.svg)](https://codecov.io/gh/frutiger/bdemeta)

# bdemeta

Build and test BDE-style code.

## Synopsis

`bdemeta walk [-t] CONFIG TARGET [TARGET ...]`<br/>
`bdemeta dot [-t] CONFIG TARGET [TARGET ...]`<br/>
`bdemeta cmake [-p] [-t] CONFIG TARGET [TARGET ...]`<br/>
`bdemeta runtests [-e EXECUTOR] [-m MAX_CASES] [TEST ...]`

## Description

`bdemeta` is a set of basic tools to assist building and testing [BDE-style
source trees](https://github.com/bloomberg/bde).  It can generate
[`CMake`](https://cmake.org) files for package groups and test drivers within
them.  It can also invoke BDE-style test drivers.

`bdemeta` supports finding targets across [disconnected directory
structures](#roots).

## Installation

Platforms running Python 3.7 or newer are supported.  Install using `pip`:

    $ pip install git+https://github.com/frutiger/bdemeta

## Modes

`bdemeta` runs in one of four modes as given by the first positional argument:

  * `walk [-t] CONFIG TARGET [TARGET ...]`:<br/>
    Walk and topologically sort dependencies

  * `dot [-t] CONFIG TARGET [TARGET ...]`:<br/>
    Generate a directed graph in the DOT language

  * `cmake [-p] [-t] CONFIG TARGET [TARGET ...]`:<br/>
    Generate a CMake lists file

  * `runtests [-e EXECUTOR] [-m MAX_CASES] [TEST ...]`:<br/>
    Run specified or discovered unit tests

## Configuration

`bdemeta` is configured by a JSON configuration file supplied as the first
argument to the `walk`, `dot` and `cmake` modes.  The configuration is as
follows:

    {
        "roots": [
            "<root>",
            ...
        ],
        "conan_roots": [
            "<conan_root>",
            ...
        ],
        "standalones": [
            "<standalone>",
            ...
        ],
        "providers": {
            "<target1>: ["<target2>", "<target3>", ...],
            ...
        },
        "runtime_libraries": ["<target4>", "<target5">, ...],
        "pkg_configs": {
            "<target6>": "<pkg1>",
            ...
        },
        "extra_dependencies": {
            "<target7>": ["<target8>", "<target9>", ...],
            ...
        }
    }

The meaning of each block is explained below.

### Roots

`bdemeta` will look for targets in directories specified by (possibly multiple)
`<root>`s in the configuration.  This makes it easy to build code across
multiple BDE-style repositories, including your own.  Relative `<root>`s are
considered relative to the path of the configuration file, not relative to the
current working directory.

In particular, `bdemeta` will search for targets by name within each `<root>`
directory:

  * package groups in `<root>/groups/<name>`
  * standalone packages in `<root>/standalones/<name>`
  * applications in `<root>/applications/<name>` (these must contain at least
    one `main` file named `<name>.m.cpp`, but may contain additional components
    if listed in `<root>/applications/<name>/package/<name>.mem`)
  * third party CMake packages in:
      * `<root>/thirdparty/CMakeLists.txt`
      * `<root>/CMakeLists.txt`

The set of directories searched for standalone packages can be extended by
specifying multiple `<standalone>` directories in the configuration.

### Conan roots

Conan will be relied on to provide binaries for each `<conan_root>` specified.
`bdemeta` will not attempt to build targets that belong to these roots.

#### Test-only dependencies

Supplying `-t` (or `--test-deps`) to the `walk`, `dot` or `cmake` modes will
include `<target>.t.dep` when calculating dependencies of a BDE-style package
group or package.

### Target providers

A number of third party targets may be specified by a single `CMakeLists.txt`.
However, the dependency from a target is on another target (i.e. library), not
on a directory.  A "target provider" may be used to specify that a directory
containing a `CMakeLists.txt` will actually provide other targets.

The sample configuration above indicates that the `CMakeLists.txt` in
`<target1>` will actually provide `<target2>` and `<target3>`.  This allows
`bdemeta` to consider the targets `<target2>` and `<target3>` found once it
finds `<target1>`.

Note that the `providers` block is optional.

### Runtime libraries

Some platforms require undefined symbols to be provided at link time.  However,
when building plug-in libraries, some symbols are expected to be supplied by
the hosting executable at runtime.  Enumerating the libraries that contain
symbols that will be supplied at runtime allows `bdemeta` to ensure that any
targets that depend those libraries are linked allowing undefined symbols.

The sample configuration indicates that any target depending (transitively or
not) on `<target4>` or `<target5>` should be linked allowing undefined symbols.

Note that the `runtime_libraries` block is optional.

### Package Config

A target may have its dependencies defined by the `pkg-config`, already
available on the system.  The `pkg_configs` block is consulted to map a target
name `<target6>` to a `pkg-config` package named `<pkg1>`.  This block
is only consulted if the search through every root as described above has been
exhausted.

Note that the `pkg_configs` block is optional.

### Extra Dependencies

Often a CMake target or a `PkgConfig` target may require additional
dependencies that `bdemeta` is expected to resolve.  Since `bdemeta` does not
parse CMake files, it needs to be informed about such dependencies.  The
`extra_dependencies` block introduces a dependency from `<target7>` onto
`<target8>`, `<target9>`, etc.

## CMake

For every target specified to the `cmake` subcommand, `bdemeta` walks all
transitive dependencies based on the configuration described above.

For each BDE-type group or package dependency, `bdemeta` generates:

  * a CMake library target
  * a CMake executable target for each test driver
  * a CMake custom target comprising all the test drivers, named `<name>.t`
  * a 'development' install target for the library & headers
  * a 'runtime' install target for the library

For each BDE-type application dependency, `bdemeta` generates a CMake
executable target, comprising the `<name>.m.cpp` main file in addition to any
components listed in `<name>.mem`.

For each `PkgConfig`-type dependency, `bdemeta` generates a CMake interface
target consisting of the discovered include directories, compile options and
link libraries.

## Plugin Tests

Code that is intended to be loaded as a shared library or plugin into another
program will often need symbols to provided by the hosting program.  `bdemeta`
will generate test targets as shared libraries instead of executables if `-p`
(or `--plugin-tests`) is supplied to the `cmake` subcommand.

## Running Tests

The `runtests` subcommand is provided as a helper utility to iterate through
multiple test drivers in parallel supporting BDE-style test case status codes.
In particular, each driver takes the test case number to run as the first
command-line argument and exits with `0` upon success, `-1` if there is no such
test case and greater than `0` upon failure.

By default, test drivers are executed by the system.  If a custom
executor is specified with the `-e` flag, that is invoked instead, supplying
the test driver and test case as trailing arguments.  The status codes from the
custom executor must match the rules described in the previous paragraph.

By default, up to 100 cases will be run per test driver.  This can be modified
by specifiying the number of desired cases with the `-m` flag.

## License

Copyright (C) 2013 Masud Rahman

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

