# bdemeta.cmake

import argparse
import os
from typing import Callable, List, Set, TextIO, Tuple, Union

from bdemeta.types import CMake, Group, Package, Pkg, Target
BdeTarget = Union[Group, Package]

Writer = Callable[[str, Callable[[TextIO], None]], None]

LISTS_PROLOGUE = '''\
cmake_minimum_required(VERSION 3.8)

'''
LIBRARY_PROLOGUE = '''\
add_library(
    {target.name}
'''
DEFINE_SYMBOL = '''\
set_target_properties(
    {target.name} PROPERTIES
    DEFINE_SYMBOL "BUILDING_{target_upper}"
)

'''
INCLUDE_DIRECTORIES_PROLOGUE = '''\
target_include_directories(
    {target.name} PUBLIC
'''
LINK_LIBRARIES_PROLOGUE = '''\
target_link_libraries(
    {target.name} PUBLIC
'''
LAZILY_BOUND_FLAG = '''\
if(APPLE)
    set_target_properties(
        {target.name} PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif()  # APPLE

'''
INSTALL_HEADERS_PROLOGUE = '''\
install(
    FILES
'''
INSTALL_HEADERS_DESTINATION = '''\
    DESTINATION include
    COMPONENT development
    EXCLUDE_FROM_ALL
'''
PKG_CONFIG = '''\
pkg_check_modules({name} REQUIRED {package})

add_library({name} INTERFACE)
if(BUILD_SHARED_LIBS)
    if({name}_INCLUDE_DIRS)
        target_include_directories({name} INTERFACE
                                   "${{{name}_INCLUDE_DIRS}}")
    endif()
    if({name}_LDFLAGS)
        target_link_libraries({name} INTERFACE
                              "${{{name}_LDFLAGS}}")
    endif()
    if({name}_CFLAGS_OTHER)
        target_compile_options({name} INTERFACE
                               "${{{name}_CFLAGS_OTHER}}")
    endif()
else()
    if({name}_STATIC_INCLUDE_DIRS)
        target_include_directories({name} INTERFACE
                                   "${{{name}_STATIC_INCLUDE_DIRS}}")
    endif()
    if({name}_STATIC_LDFLAGS)
        target_link_libraries({name} INTERFACE
                              "${{{name}_STATIC_LDFLAGS}}")
    endif()
    if({name}_STATIC_CFLAGS_OTHER)
        target_compile_options({name} INTERFACE
                               "${{{name}_STATIC_CFLAGS_OTHER}}")
    endif()
endif()  # BUILD_SHARED_LIBS

'''
INSTALL_LIBRARY = '''\
install(
    TARGETS {target.name}
    COMPONENT development
    DESTINATION lib
    EXCLUDE_FROM_ALL
)

install(
    TARGETS {target.name}
    COMPONENT runtime
    DESTINATION .
)

'''
TEST_TARGET_PROLOGUE = '''\
add_custom_target(
    {target.name}.t
    DEPENDS
'''
COMMAND_EPILOGUE = '''\
)

'''
TESTING_DRIVER = '''\
add_executable({name} EXCLUDE_FROM_ALL {driver})
target_link_libraries({name} {target.name})

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

def generate_bde(target: BdeTarget, writer: Writer) -> None:
    def write(out: TextIO) -> None:
        out.write(LIBRARY_PROLOGUE.format(**locals()))
        for component in target.sources():
            out.write('    {}\n'.format(component).replace('\\', '/'))
        out.write(COMMAND_EPILOGUE)

        target_upper = target.name.upper()
        out.write(DEFINE_SYMBOL.format(**locals()))

        out.write(INCLUDE_DIRECTORIES_PROLOGUE.format(**locals()))
        for include in target.includes():
            out.write('    {}\n'.format(include).replace('\\', '/'))
        out.write(COMMAND_EPILOGUE)

        out.write(LINK_LIBRARIES_PROLOGUE.format(**locals()))
        for dependency in target.dependencies():
            if dependency.has_output:
                out.write('    {}\n'.format(dependency.name))
        out.write(COMMAND_EPILOGUE)

        if target.lazily_bound:
            out.write(LAZILY_BOUND_FLAG.format(**locals()))

        drivers = []
        for driver in target.drivers():
            name = os.path.splitext(os.path.basename(driver))[0]
            out.write(TESTING_DRIVER.format(**locals()).replace('\\', '/'))
            drivers.append(name)

        if drivers:
            out.write(TEST_TARGET_PROLOGUE.format(**locals()))
            for driver in drivers:
                out.write('    {}\n'.format(driver))
            out.write(COMMAND_EPILOGUE)

        out.write(INSTALL_HEADERS_PROLOGUE)
        for header in target.headers():
            out.write('    {}\n'.format(header).replace('\\', '/'))
        out.write(INSTALL_HEADERS_DESTINATION)
        out.write(COMMAND_EPILOGUE)

        out.write(INSTALL_LIBRARY.format(**locals()))

    writer(f'{target.name}.cmake', write)

def generate_pkg(target: Pkg, writer: Writer) -> None:
    def write(out: TextIO) -> None:
        name    = target.name
        package = target.package
        out.write(PKG_CONFIG.format(**locals()))

    writer(f'{target.name}.cmake', write)

def generate(targets: List[Target], writer: Writer) -> None:
    uses_pkg_config = any(isinstance(t, Pkg) for t in targets)
    def write(out: TextIO) -> None:
        out.write(LISTS_PROLOGUE.format(**locals()))
        out.write(INSTALL_TARGETS)
        if uses_pkg_config:
            out.write('include(FindPkgConfig)\n')

        for target in reversed(targets):
            if isinstance(target, Group) or isinstance(target, Package):
                generate_bde(target, writer)
                out.write('include({target.name}.cmake)\n'.format(**locals()))
            elif isinstance(target, CMake):
                path = target.path()
                out.write('add_subdirectory({path} {target.name})\n'.format(
                                                **locals()).replace('\\', '/'))
            elif isinstance(target, Pkg):
                generate_pkg(target, writer)
                out.write('include({target.name}.cmake)\n'.format(**locals()))

            if target.overrides:
                out.write(f'include({target.overrides})\n'.replace('\\', '/'))

    writer('CMakeLists.txt', write)

