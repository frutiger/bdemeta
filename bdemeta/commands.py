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

rule cxx-executable
  deps    = gcc
  depfile = $out.d
  command = {cxx} $cflags $in $ldflags -MMD -MF $out.d -o $out

rule ar
  command = {ar} -crs $out $in

'''.format(cc=cc, cxx=cxx, ar=ar)
    lib_template=u'''\
build {output}: ar {input}{deps}

build {name}: phony {output}

'''
    defaults_template = u'''\
default {}

'''
    tests_template=u'''\
build {alias}: phony {targets}

'''
    obj_template=u'''\
build {output}: {compiler}-object {input}
  flags ={flags}

'''
    executable_template=u'''\
build {output}: cxx-executable {input}{deps}
  cflags ={cflags}
  ldflags ={ldflags}

build {name}: phony {output}

'''

    join  = lambda l: ' '.join(l)
    pjoin = path.join
    obj   = lambda c: pjoin('out', 'objs',  c)
    test  = lambda c: pjoin('out', 'tests', c)
    def output(unit):
        if unit.result_type() == 'library':
            return pjoin('out', 'libs', 'lib{}.a'.format(unit.name()))
        elif unit.result_type() == 'executable':
            return pjoin('out', 'apps', unit.name())
        else:
            return None

    file.write(rules)

    defaults  = []
    all_tests = []
    for unit in tsort(traverse(units)):
        if unit.result_type() == 'library':
            objects    = []
            unit_tests = []

            obj_deps = join([output(u) for u in tsort(traverse((unit,))) if \
                                                      u != unit and output(u)])
            obj_deps = ' | ' + obj_deps if obj_deps else ''

            test_deps = join([output(u) for u in tsort(traverse((unit,))) if \
                                                                    output(u)])
            test_deps = ' | ' + test_deps if test_deps else ''

            for c in unit.components():
                if c['type'] == 'object':
                    file.write(obj_template.format(
                      output   = obj(c['output']),
                      compiler = 'cxx' if c['input'][-4:] == '.cpp' else 'cc',
                      input    = c['input'],
                      flags    = c['cflags']))
                    objects.append(obj(c['output']))
                elif c['type'] == 'test':
                    file.write(executable_template.format(
                                                  output   = test(c['output']),
                                                  input    = c['input'],
                                                  deps     = test_deps,
                                                  cflags   = c['cflags'],
                                                  ldflags  = c['ldflags'],
                                                  name     = c['output']))
                    unit_tests.append(test(c['output']))
                    all_tests.append(test(c['output']))

            if objects:
                file.write(lib_template.format(output  = output(unit),
                                               name    = unit.name(),
                                               input   = join(objects),
                                               deps    = obj_deps))
                defaults.append(output(unit))

            if unit_tests:
                file.write(tests_template.format(alias   = unit.name() + '.t',
                                                 targets = join(unit_tests)))


        elif unit.result_type() == 'executable':
            exec_deps = join([output(u) for u in tsort(traverse((unit,))) if \
                                                      u != unit and output(u)])
            exec_deps = ' | ' + exec_deps if exec_deps else ''

            c = unit.components()[0]
            file.write(executable_template.format(output  = output(unit),
                                                  input   = c['input'],
                                                  deps    = exec_deps,
                                                  cflags  = c['cflags'],
                                                  ldflags = c['ldflags'],
                                                  name    = unit.name()))
            defaults.append(output(unit))

    if defaults:
        file.write(defaults_template.format(join(defaults)))

    if all_tests:
        file.write(tests_template.format(alias   = 'tests',
                                         targets =  join(all_tests)))

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
        tests = [path.join('out', 'tests', t) for t in tests]

    multiprocessing.Pool().map(runtest, sorted(tests))


