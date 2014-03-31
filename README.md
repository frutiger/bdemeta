##bde-meta - build and test BDE-style code

### SYNOPSIS

`bde-meta deps [--root ROOT] <group> [<group> ...]`<br/>
`bde-meta cflags [--root ROOT] [--<name>.cflag CFLAG] <group> [<group> ...]`<br/>
`bde-meta ldflags [--root ROOT] [--<name>.ldflag LDFLAG] <group> [<group> ...]`<br/>
`bde-meta ninja [--root ROOT] [--<name>.cflag CFLAG] [--<name>.ldflag LDFLAG] <group>`<br/>
`bde-meta runtests [<test> ...]`:

### DESCRIPTION

`bde-meta` is a set of basic tools to assist building and testing [BDE-style
source trees](https://github.com/bloomberg/bde).  It can generate [ninja build
files](https://github.com/martine/ninja) for a particular package group, and
provide `cflags` and `ldflags` when building applications that depend on such
package groups.  It can also run all the unit tests for a particular package
group.

`bde-meta` supports finding package groups across [disconnected
directory structures](#roots), [arbitrary cflags and ldflags](#flags) for any
given dependency, and [dependencies that are not actually package
groups](#units).

`bde-meta` will insert the contents of `~/.bdemetarc` as if they were command
line flags before any flags specified on the command line.

### INSTALLATION

Place `bde-meta.py` in your `$PATH` somewhere. Personally, I symlink it to
`~/bin/bde-meta` and have `~/bin` in my `$PATH`.

This requires either of the latest versions of Python 2 or Python 3.

### OPTIONS

`bde-meta` runs in one of five modes as given by the first argument:

  * `deps [--root ROOT] <group> [<group> ...]`:
    Print the list of dependencies of the specified `<group>`s in topologically
    sorted order.

  * `cflags [--root ROOT] [--<name>.cflag CFLAG] <group> [<group> ...]`:
    Generate a set of `-I` directives that will allow a compilation unit
    depending on the specified `<group>`s to compile correctly.

  * `ldflags [--root ROOT] [--<name>.ldflag LDFLAG] <group> [<group> ...]`:
    Generate a set of `-L` and `-l` directives that allow a link of objects
    depending on the specified `<group>`s to link correctly.

  * `ninja [--root ROOT] [--<name>.cflag CFLAG] [--<name>.ldflag LDFLAG] <group>`:
    Generate a ninja build file that will build a statically linked library for
    the specified `<group>`.

  * `runtests [<test> ...]`:
    Run all of the specified BDE-style `<test>` programs to be found in
    `out/tests` or all of the tests in that subdirectory.

### ROOTS
<a name="roots"></a>

`bde-meta` will look for package groups in directories specified by (possibly
multiple) `--root` arguments.  This makes it easy to build code across multiple
BDE-style repositories, including your own.

### FLAGS
<a name="flags"></a>

Compiler and linker flags may be specified in addition to the ones generated by
the structure of the package group.  These are specified by supplying
`--<name>.cflag` and `--<name>.ldflag` respectively, where `<name>` specifies
the name of the dependency.  For example, specifying
`--bsl.cflag=-DBDE_BUILT_TARGET_EXC` will provide that as a flag for `bsl` and
every dependent of `bsl`.

### UNITS
<a name="units"></a>

`bde-meta` supports dependencies that are not package groups.  This can be
useful when depending on headers and libraries provided by the system.  By
default, such dependencies introduce no new cflags or ldflags, unless such a
flag has been specified with a `--<name>.cflag` or `--<name>.ldflag`.

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

