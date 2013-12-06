##bde-meta(1) -- a script to assist building 'BDE' style code on Unix

### SYNOPSIS

`bde-meta cflags <group>`<br/>
`bde-meta mkmk <group>`<br/>
`bde-meta deps <group>`

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

  * `mkmk <group>`:
    Generate a makefile that will build a statically linked library for the
    specified `<group>`.

  * `deps <group>`:
    Print the list of dependencies of the specified `<group>` in topologically
    sorted order.

### ROOTS
<a name="roots"></a>

`bde-meta` will look for package groups inside a colon-delimited set of paths
denoted by the ROOTS environment variable. This makes it easy to build code
across multiple BDE-style repositories, including your own.

### EXAMPLES

The following examples are shown as given to the shell:

`make -f <(bde-meta mkmk bsl)`<br/>
Build `out/lib/libbsl.a`.

`g++ m.cpp $(bde-meta cflags bsl)`<br/>
Build `m.cpp`, linking against `bsl` and any of its dependencies.

### SEE ALSO

make(1)
