##bde-meta - a script to assist building 'BDE' style code on Unix

### SYNOPSIS

`bde-meta cflags <group>`<br/>
`bde-meta deps <group>`<br/>
`bde-meta ldflags <group>`<br/>
`bde-meta makefile <group>`<br/>
`bde-meta ninja <group>`

### DESCRIPTION

`bde-meta` offers two related tools to assist in building [BDE-style source
trees](https://github.com/bloomberg/bsl) on *nix platforms, and building
software that uses such libraries.

Notably, `bde-meta` supports finding package groups across disconnected
directory structures, by means of the [ROOTS](#roots) environment variable.

### OPTIONS

`bde-meta` runs in one of two modes as given by the first argument:

  * `cflags <group>`:
    Generate a set of `-I` directives that will allow a compilation unit
    depending on the specified `<group>` to compile correctly.

  * `deps <group>`:
    Print the list of dependencies of the specified `<group>` in topologically
    sorted order.

  * `ldflags <group>`:
    Generate a set of `-L` and `-l` directives that allow a link of objects
    depending on the specified `<group>` to link correctly.

  * `makefile <group>`:
    Generate a makefile that will build a statically linked library for the
    specified `<group>`.

  * `ninja <group>`:
    Generate a ninja build file that will build a statically linked library for
    the specified `<group>`.

### ROOTS
<a name="roots"></a>

`bde-meta` will look for package groups inside a colon-delimited set of paths
denoted by the ROOTS environment variable. This makes it easy to build code
across multiple BDE-style repositories, including your own.

### EXAMPLES

To build a static library named `bsl` in `out/lib` using `make`:

    $ make -f <(bde-meta makefile bsl)

To build a static library named `bsl` in `out/lib` using `ninja`:

    $ ninja -f <(bde-meta ninja bsl)

To build `bsl` and all its dependencies as separate libraries in `out/lib`:

    $ bde-meta deps bsl | while read group
                            do ninja -f <(bde-meta ninja $group)
                          done

To build `m.cpp` with `bsl` as a dependency and link it with all its
dependencies:

    $ c++ $(bde-meta cflags bsl) $(bde-meta ldflags bsl) m.cpp

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

