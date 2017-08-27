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
DEFINE_SYMBOL = '''\
set_target_properties(
    {target} PROPERTIES
    DEFINE_SYMBOL "BUILDING_{target_upper}"
)

'''
INCLUDE_DIRECTORIES_PROLOGUE = '''\
target_include_directories(
    {target} PUBLIC
'''
LINK_LIBRARIES_PROLOGUE = '''\
target_link_libraries(
    {target} PUBLIC
'''
LAZILY_BOUND_FLAG = '''\
if (APPLE)
    set_target_properties(
        {target} PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif ()  # APPLE

'''
INSTALL_HEADERS_PROLOGUE = '''\
install(
    FILES
'''
INSTALL_HEADERS_DESTINATION = '''\
    DESTINATION include
    COMPONENT development
'''
INSTALL_LIBRARY = '''\
install(
    TARGETS {target}
    COMPONENT development
    DESTINATION lib
)

install(
    TARGETS {target}
    COMPONENT runtime
    DESTINATION .
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
add_test({name} bdemeta runtests ./{name})

'''
TESTING_EPILOGUE = '''\
endif()  # BUILD_TESTING

'''
INSTALL_TARGETS = '''\
add_custom_target(
    install.devel
    COMMAND ${CMAKE_COMMAND} -DCOMPONENT=devel -P ${CMAKE_BINARY_DIR}/cmake_install.cmake
)

add_custom_target(
    install.runtime
    COMMAND ${CMAKE_COMMAND} -DCOMPONENT=runtime -P ${CMAKE_BINARY_DIR}/cmake_install.cmake
)

'''

def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--generate-test', type=str,
                                                 nargs='*', default=[])
    options, targets = parser.parse_known_args(args)
    return set(options.generate_test), targets

def generate_target(target, file_writer, generate_test):
    def write(out):
        out.write('''project({target} CXX)\n'''.format(**locals()))
        out.write(LIBRARY_PROLOGUE.format(**locals()))
        for component in target.sources():
            out.write('    {}\n'.format(component).replace('\\', '/'))
        out.write(COMMAND_EPILOGUE)

        target_upper = target.upper()
        out.write(DEFINE_SYMBOL.format(**locals()))

        out.write(INCLUDE_DIRECTORIES_PROLOGUE.format(**locals()))
        for include in target.includes():
            out.write('    {}\n'.format(include).replace('\\', '/'))
        out.write(COMMAND_EPILOGUE)

        out.write(LINK_LIBRARIES_PROLOGUE.format(**locals()))
        for dependency in target.dependencies():
            if dependency.has_output:
                out.write('    {}\n'.format(dependency))
        out.write(COMMAND_EPILOGUE)

        if target.lazily_bound:
            out.write(LAZILY_BOUND_FLAG.format(**locals()))

        out.write(INSTALL_HEADERS_PROLOGUE)
        for header in target.headers():
            out.write('    {}\n'.format(header).replace('\\', '/'))
        out.write(INSTALL_HEADERS_DESTINATION)
        out.write(COMMAND_EPILOGUE)

        out.write(INSTALL_LIBRARY.format(**locals()))

        if generate_test:
            out.write(TESTING_PROLOGUE)
            for driver in target.drivers():
                name = os.path.splitext(os.path.basename(driver))[0]
                out.write(TESTING_DRIVER.format(**locals()).replace('\\', '/'))
            out.write(TESTING_EPILOGUE)

    file_writer(f'{target}.cmake', write)

def generate(targets, file_writer, test_targets):
    def write(out):
        out.write(LISTS_PROLOGUE.format(**locals()))
        out.write(INSTALL_TARGETS)

        for target in reversed(targets):
            if any([isinstance(target, bdemeta.types.Group),
                    isinstance(target, bdemeta.types.Package)]):
                generate_target(target, file_writer, target in test_targets)
                out.write('include({target}.cmake)\n'.format(**locals()))
            elif isinstance(target, bdemeta.types.CMake):
                path = target.path()
                out.write('add_subdirectory({path} {target})\n'.format(
                                                **locals()).replace('\\', '/'))
            if target.overrides:
                out.write(f'include({target.overrides})\n'.replace('\\', '/'))

    file_writer('CMakeLists.txt', write)

