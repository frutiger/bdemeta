import glob
import multiprocessing
import os.path as path
import subprocess
import signal
from itertools import chain, count

from bdemeta.graph import traverse, tsort

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
build {lib}: ar {objects}{deps}

build {libname}: phony {lib}

default {lib}

'''
    tests_template=u'''\
build tests: phony {tests}

'''
    obj_template=u'''\
build {object}: {compiler}-object {source}
  flags ={flags}

'''
    test_template=u'''\
build {test}: cxx-test {driver}{deps}
  flags ={flags}

build {testname}: phony {test}

'''

    join  = lambda l: ' '.join(l)
    pjoin = path.join
    obj   = lambda c: pjoin('out', 'objs',  c)
    test  = lambda c: pjoin('out', 'tests', c)
    def output(unit):
        if unit.result_type() == 'library':
            return pjoin('out', 'libs', 'lib{}.a'.format(unit.name()))
        else:
            return None

    file.write(rules)

    all_tests = []
    for unit in tsort(traverse(units)):
        components  = unit.components()
        objects     = join((obj(c['object']) for c in components.values()))
        all_tests  += (test(c['test'])  for c in components.values() \
                                                                if 'test' in c)

        if unit.result_type() == 'library' and len(objects):
            deps = join([output(u) for u in tsort(traverse((unit,))) if \
                                                      u != unit and output(u)])
            if deps:
                deps = ' | ' + deps
            file.write(lib_template.format(lib     = output(unit),
                                           libname = unit.name(),
                                           objects = objects,
                                           deps    = deps))

        for name in sorted(components.keys()):
            c      = components[name]
            flags  = ' ' + ' '.join(c['cflags']) if c['cflags'] else ''
            file.write(obj_template.format(
                      object   = obj(c['object']),
                      compiler = 'cxx' if c['source'][-4:] == '.cpp' else 'cc',
                      source   = c['source'],
                      flags    = flags))
            if 'driver' in c:
                flags = chain(c['cflags'], c['ldflags'])
                flags = ' ' + ' '.join(flags) if flags else ''
                deps = join([output(u) for u in tsort(traverse((unit,))) if \
                                                                    output(u)])
                if deps:
                    deps = ' | ' + deps
                file.write(test_template.format(test     = test(c['test']),
                                                testname = c['test'],
                                                driver   = c['driver'],
                                                flags    = flags,
                                                deps     = deps))

    if len(all_tests):
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
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if len(tests) == 0:
        tests = glob.glob(path.join('out', 'tests', '*'))
    else:
        tests = [path.join('out', 'tests', t + '.t') for t in tests]

    multiprocessing.Pool().map(runtest, sorted(tests))


