[![Build Status](https://img.shields.io/travis/frutiger/bdemeta/master.svg?style=flat-square)](https://travis-ci.org/frutiger/bdemeta)
[![Coverage Status](https://img.shields.io/coveralls/frutiger/bdemeta/master.svg?style=flat-square)](https://coveralls.io/r/frutiger/bdemeta?branch=master)

# bdemeta

Build and test BDE-style code.

## Synopsis

`bdemeta walk UNIT [UNIT ...]`<br/>
`bdemeta cmake UNIT [UNIT ...]`<br/>
`bdemeta runtests [TEST ...]`:

## Description

`bdemeta` is a set of basic tools to assist building and testing [BDE-style
source trees](https://github.com/bloomberg/bde).  It can generate
[`CMake`](https://cmake.org) files, and it can also invoke BDE-style test
drivers.

`bdemeta` supports finding targets across [disconnected directory
structures](#roots).

## Installation

Platforms running Python 3.6 or newer are supported.  Install using `pip`:

    $ pip install git+https://github.com/frutiger/bdemeta

## Modes

`bdemeta` runs in one of four modes as given by the first positional argument:

  * `walk UNIT [UNIT ...]`:<br/>
    Walk and topologically sort dependencies

  * `cmake UNIT [UNIT ...]`:<br/>
    Generate CMake files in the current directory

  * `runtests [TEST ...]`:<br/>
    Run unit tests

## Configuration

`bdemeta` is configured by a JSON configuration file in the current directory
called `.bderoots.conf`.  The configuration is as follows:

    [
        "<root>",
        ...
    ]

The specified `<root>`s are added to the target search paths.

### Roots

`bdemeta` will look for targets in directories specified by (possibly multiple)
`<root>`s in the configuration.  This makes it easy to build code across
multiple BDE-style repositories, including your own.

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

