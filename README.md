##bde-meta - build and test BDE-style code

### SYNOPSIS

`bde-meta cflags <group> [<group> ...]`<br/>
`bde-meta deps <group> [<group> ...]`<br/>
`bde-meta ldflags <group> [<group> ...]`<br/>
`bde-meta ninja [--cflags <cflags>] [--ldflags <ldflags>] <group>`<br/>
`bde-meta runtests [<test> ...]`

### DESCRIPTION

`bde-meta` is a set of basic tools to assist building and testing [BDE-style
source trees](https://github.com/bloomberg/bde).  It can generate [ninja build
files](https://github.com/martine/ninja) for a particular package group, and
provide `cflags` and `ldflags` when building applications that depend on such
package groups.  It can also run all the unit tests for a particular package
group.

Notably, `bde-meta` supports finding package groups across disconnected
directory structures, by means of the [ROOTS](#roots) environment variable.

### OPTIONS

`bde-meta` runs in one of five modes as given by the first argument:

  * `cflags <group> [<group> ...]`:
    Generate a set of `-I` directives that will allow a compilation unit
    depending on the specified `<group>`s to compile correctly.

  * `deps <group> [<group> ...]`:
    Print the list of dependencies of the specified `<group>`s in topologically
    sorted order.

  * `ldflags <group> [<group> ...]`:
    Generate a set of `-L` and `-l` directives that allow a link of objects
    depending on the specified `<group>`s to link correctly.

  * `ninja [--cflags <cflags>] [--ldflags <ldflags>] <group>`:
    Generate a ninja build file that will build a statically linked library for
    the specified `<group>`, supplying the optionally specified <cflags> to the
    compiler for both, object files and tests, and the optionally specified
    <ldflags> to the linker for tests.

  * `runtests [<test> ...]`:
    Run all of the specified BDE-style `<test>` programs to be found in
    `out/tests` or all of the tests in that subdirectory.

### ROOTS
<a name="roots"></a>

`bde-meta` will look for package groups inside a colon-delimited set of paths
denoted by the ROOTS environment variable. This makes it easy to build code
across multiple BDE-style repositories, including your own.

### EXAMPLES

To build a static library named `bsl` in `out/lib`:

    $ ninja -f <(bde-meta ninja bsl)

To build `bdl` and all its dependencies as separate libraries in `out/lib`:

    $ bde-meta deps bdl | while read group
                            do ninja -f <(bde-meta ninja $group)
                          done

To build all tests in the `bdl` package group using `ninja`, first build the
library (and all dependent libraries), then build the tests:

    $ bde-meta deps bdl | while read group
                            do ninja -f <(bde-meta ninja $group)
                          done
    $ ninja -f <(bde-meta ninja bdl) tests

To run all of the previously built tests:

    $ bde-meta runtests

To build `m.cpp` with `bdl` as a dependency and link it with all its
dependencies:

    $ c++ $(bde-meta cflags bdl) $(bde-meta ldflags bdl) m.cpp

### LICENSE

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

