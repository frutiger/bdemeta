# bdemeta.cmake

import argparse
import os

import bdemeta.types

LISTS_PROLOGUE = '''\
cmake_minimum_required(VERSION 3.8)

option(BUILD_TESTING "" OFF)
include(CTest)

'''
LIBRARY_PROLOGUE = '''\
add_library(
    {target}
'''
INCLUDE_DIRECTORIES_PROLOGUE = '''\
target_include_directories(
    {target} PUBLIC
'''
LINK_LIBRARIES_PROLOGUE = '''\
target_link_libraries(
    {target} PUBLIC
'''
INSTALL_HEADERS_PROLOGUE = '''\
install(
    FILES
'''
INSTALL_HEADERS_DESTINATION = '''\
    DESTINATION include
'''
INSTALL_LIBRARY = '''\
install(
    TARGETS {target}
    DESTINATION lib
)
'''
COMMAND_EPILOGUE = '''\
)

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

def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--generate-test', type=str,
                                                 nargs='*', default=[])
    options, units = parser.parse_known_args(args)
    return set(options.generate_test), units

def generate_unit(target, file_writer, generate_test):
    def write(out):
        out.write('''project({target} CXX)\n'''.format(**locals()))
        out.write(LIBRARY_PROLOGUE.format(**locals()))
        for component in target.sources():
            out.write('    {}\n'.format(component))
        out.write(COMMAND_EPILOGUE)

        out.write(INCLUDE_DIRECTORIES_PROLOGUE.format(**locals()))
        for include in target.includes():
            out.write('    {}\n'.format(include))
        out.write(COMMAND_EPILOGUE)

        out.write(LINK_LIBRARIES_PROLOGUE.format(**locals()))
        for dependency in target.dependencies():
            out.write('    {}\n'.format(dependency))
        out.write(COMMAND_EPILOGUE)

        out.write(INSTALL_HEADERS_PROLOGUE)
        for header in target.headers():
            out.write('    {}\n'.format(header))
        out.write(INSTALL_HEADERS_DESTINATION)
        out.write(COMMAND_EPILOGUE)

        out.write(INSTALL_LIBRARY.format(**locals()))

        if generate_test:
            out.write(TESTING_PROLOGUE)
            for driver in target.drivers():
                name = os.path.splitext(os.path.basename(driver))[0]
                out.write(TESTING_DRIVER.format(**locals()))
            out.write(TESTING_EPILOGUE)

    file_writer(f'{target}.cmake', write)

def generate(targets, file_writer, test_targets):
    def write(out):
        out.write(LISTS_PROLOGUE.format(**locals()))

        for target in reversed(targets):
            if any([isinstance(target, bdemeta.types.Group),
                    isinstance(target, bdemeta.types.Package)]):
                generate_unit(target, file_writer, target in test_targets)
                out.write('include({target}.cmake)\n'.format(**locals()))
            elif isinstance(target, bdemeta.types.CMake):
                path = target.path()
                out.write('add_subdirectory({path} {target})\n'.format(
                                                                   **locals()))

    file_writer('CMakeLists.txt', write)

