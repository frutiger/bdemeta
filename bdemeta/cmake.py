# bdemeta.cmake

import os

import bdemeta.types

PROLOGUE = '''\
cmake_minimum_required(VERSION 3.7)
project({target} CXX)

option(BUILD_TESTING "" OFF)
include(CTest)

'''
LIBRARY_PROLOGUE = '''\
add_library(
    {target}
'''
SOURCE = '''\
    {component}
'''
INCLUDE = '''\
    -I{include}
'''
COMPILE_OPTIONS_PROLOGUE = '''\
target_compile_options(
    {target} PUBLIC
'''
LINK_LIBRARIES_PROLOGUE = '''\
target_link_libraries(
    {target} PUBLIC
'''
TESTING_PROLOGUE = '''\
if(BUILD_TESTING)

'''
TESTING_DRIVER = '''\
add_executable({name} {driver})
target_link_libraries({name} {target})

'''
TESTING_EPILOGUE = '''\
endif()  # BUILD_TESTING

'''
COMMAND_EPILOGUE = '''\
)

'''

def generate_group(target, outdir):
    with open(os.path.join(outdir, f'{target}.cmake'), 'w') as out:
        out.write(PROLOGUE.format(**locals()))

        out.write(LIBRARY_PROLOGUE.format(**locals()))
        for component in target.sources():
            out.write(SOURCE.format(**locals()))
        out.write(COMMAND_EPILOGUE)

        out.write(COMPILE_OPTIONS_PROLOGUE.format(**locals()))
        for include in target.includes():
            out.write(INCLUDE.format(**locals()))
        out.write(COMMAND_EPILOGUE)

        out.write(LINK_LIBRARIES_PROLOGUE.format(**locals()))
        for dependency in target.dependencies():
            out.write('    {}\n'.format(dependency))
        out.write(COMMAND_EPILOGUE)

        out.write(TESTING_PROLOGUE)
        for driver in target.drivers():
            name = os.path.splitext(os.path.basename(driver))[0]
            out.write(TESTING_DRIVER.format(**locals()))
        out.write(TESTING_EPILOGUE)

def generate(targets, outdir):
    with open(os.path.join(outdir, 'CMakeLists.txt'), 'w') as out:
        out.write('cmake_minimum_required(VERSION 3.8)\n')
        for target in reversed(targets):
            if any([isinstance(target, bdemeta.types.Group),
                    isinstance(target, bdemeta.types.Package)]):
                generate_group(target, outdir)
                out.write('include({target}.cmake)\n'.format(**locals()))
            elif isinstance(target, bdemeta.types.CMake):
                path = target.path()
                out.write('add_subdirectory({path} {target})\n'.format(
                                                                   **locals()))

