import glob
import multiprocessing
import os.path as path
import subprocess
from itertools import chain, count

from bdemeta.graph import traverse, tsort
from bdemeta.types import Group

def walk(units):
    return ' '.join(u.name() for u in tsort(traverse(units)))

def flags(units, type):
    units  = tsort(traverse(units))
    flags  = chain(*[u.flags(type) for u in units])
    return ' '.join(flags)

def ninja(units, cc, cxx, ar, file):
    rules = u'''\
rule cc-object
  deps    = gcc
  depfile = $out.d
  command = {cc} -c $flags $in -MMD -MF $out.d -o $out

rule cxx-object
  deps    = gcc
  depfile = $out.d
  command = {cxx} -c $flags $in -MMD -MF $out.d -o $out

rule cxx-test
  deps    = gcc
  depfile = $out.d
  command = {cxx} $in $flags -MMD -MF $out.d -o $out

rule ar
  command = {ar} -crs $out $in

'''.format(cc=cc, cxx=cxx, ar=ar)
    lib_template=u'''\
build {lib}: ar {objects} | {libs}

build {libname}: phony {lib}

default {lib}

'''
    tests_template=u'''\
build tests: phony {tests}

'''
    obj_template=u'''\
build {object}: {compiler}-object {source}
  flags = {flags}

'''
    test_template=u'''\
build {test}: cxx-test {driver} | {libs}
  flags = {flags}

build {testname}: phony {test}

'''

    join  = lambda l: ' '.join(l)
    pjoin = path.join
    obj   = lambda c: pjoin('out', 'objs',  c)
    test  = lambda c: pjoin('out', 'tests', c)
    lib   = lambda l: pjoin('out', 'libs', 'lib{}.a'.format(l.name()))

    file.write(rules)

    units = tsort(traverse(units))

    all_tests = []
    for unit in units:
        if not isinstance(unit, Group):
            continue

        components = unit.components()
        objects    = join((obj(c['object']) for c in components.values()))
        tests      = join((test(c['test'])  for c in components.values() \
                                                               if 'test' in c))
        all_tests.append(tests)

        units     = list(filter(lambda x: isinstance(x, Group),
                                tsort(traverse(frozenset((unit,))))))
        dep_units = list(filter(lambda x: x != unit, units))

        file.write(lib_template.format(lib     = lib(unit),
                                       libname = unit.name(),
                                       objects = objects,
                                       libs    = join(map(lib, dep_units))))

        for name in sorted(components.keys()):
            c      = components[name]
            flags  = ' '.join(c['cflags'])
            file.write(obj_template.format(
                      object   = obj(c['object']),
                      compiler = 'cxx' if c['source'][-4:] == '.cpp' else 'cc',
                      source   = c['source'],
                      flags    = flags))
            if 'driver' in c:
                flags = ' '.join(chain(c['cflags'], c['ldflags']))
                file.write(test_template.format(
                                             test     = test(c['test']),
                                             testname = c['test'],
                                             driver   = c['driver'],
                                             flags    = flags,
                                             libs     = join(map(lib, units))))

    file.write(tests_template.format(tests = join(all_tests)))

def runtest(test):
    for case in count():
        rc = subprocess.call((test, str(case)))
        if rc == 0:
            continue
        elif rc == 255:
            break
        else:
            raise RuntimeError('{test} case {case} failed'.format(test = test,
                                                                  case = case))

def runtests(tests):
    if len(tests) == 0:
        tests = glob.glob(path.join('out', 'tests', '*'))
    else:
        tests = [path.join('out', 'tests', t + '.t') for t in tests]

    multiprocessing.Pool().map(runtest, sorted(tests))


