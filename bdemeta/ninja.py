# bdemeta.ninja

import os

def generate(targets, config, file):
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
  command = {cxx} $flags $in -MMD -MF $out.d -o $out

rule ar
  command = {ar} -crs $out $in

'''.format(cc=config['cc'], cxx=config['c++'], ar=config['ar'])
    lib_template=u'''\
build {output}: ar {input}

build {name}: phony {output}

'''
    defaults_template = u'''\
default {}

'''
    phonies_template = u'''\
build {{}}: phony {}

'''.format(os.devnull)
    tests_template=u'''\
build {alias}: phony {targets}

'''
    obj_template=u'''\
build {output}: {compiler}-object {input}
  flags ={flags}

'''
    executable_template=u'''\
build {output}: cxx-executable {input}
  flags ={flags}

build {name}: phony {output}

'''

    def write_source(file, source):
        if source.type == 'object':
            file.write(obj_template.format(name     = source.name,
                                           output   = source.output,
                                           input    = source.input,
                                           compiler = source.compiler,
                                           flags    = source.flags))
        elif source.type == 'executable':
            file.write(executable_template.format(name   = source.name,
                                                  output = source.output,
                                                  input  = source.input,
                                                  flags  = source.flags))

    join = lambda l: ' '.join(l)

    file.write(rules)

    defaults  = []
    phonies   = []
    all_tests = []

    for target in reversed(targets):
        for phony in target.ld_args():
            if not os.path.isfile(phony):
                phonies.append(phony)

        for source in target.sources():
            write_source(file, source)

        if target.objects():
            file.write(lib_template.format(output = target.output(),
                                           name   = target,
                                           input  = join(target.objects())))

        if target.unit_tests():
            file.write(tests_template.format(
                                          alias   = target + '.t',
                                          targets = join(target.unit_tests())))
            all_tests.extend(target.unit_tests())

        if target.output():
            defaults.append(target.output())

    if defaults:
        file.write(defaults_template.format(join(defaults)))

    if phonies:
        file.write(phonies_template.format(join(phonies)))

    if all_tests:
        file.write(tests_template.format(alias   = 'tests',
                                         targets =  join(all_tests)))

