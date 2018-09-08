# tests.test_cmake_parser

from io       import StringIO
from unittest import TestCase

from tests.cmake_parser import lex, find_command, parse_if, parse

def mk_cmd(command, *args):
    return (command, list(args))

def call_parse_if(predicate, *cmds):
    return parse_if(predicate, iter(cmds))

def call_parse(*cmds):
    return parse(iter(cmds))

class TestLex(TestCase):
    def test_nested_command_error(self):
        text = StringIO("if(if())")
        error = False
        try:
            list(lex(text)) # consume the generator
        except RuntimeError:
            error = True
        assert(error)

    def test_unmatched_close_paren_error(self):
        text = StringIO("if)")
        error = False
        try:
            list(lex(text)) # consume the generator
        except RuntimeError:
            error = True
        assert(error)

class TestFindCommand(TestCase):
    def test_command_not_found_error(self):
        text = StringIO("if()")
        commands = lex(text)
        error = False
        try:
            find_command(commands, "add_library")
        except RuntimeError:
            error = True
        assert(error)

    def test_ambiguous_command_error(self):
        text = StringIO("if()\nif()")
        commands = lex(text)
        error = False
        try:
            find_command(commands, "if")
        except RuntimeError:
            error = True
        assert(error)

class TestParseIf(TestCase):
    def test_empty_if(self):
        node = call_parse_if('check', mk_cmd('endif'))
        assert(('check', [], []) == node)

    def test_one_command(self):
        add_lib = mk_cmd('add_library')
        node    = call_parse_if('check', add_lib, mk_cmd('endif'))
        assert(('check', [add_lib], []) == node)

    def test_empty_with_empty_else(self):
        node    = call_parse_if('check', mk_cmd('else'), mk_cmd('endif'))
        assert(('check', [], []) == node)

    def test_if_else(self):
        add_lib = mk_cmd('add_library')
        add_exe = mk_cmd('add_executable')
        node    = call_parse_if('check',
                                add_lib,
                                mk_cmd('else'),
                                add_exe,
                                mk_cmd('endif'))
        assert(('check', [add_lib], [add_exe]) == node)

    def test_nested_if(self):
        foo  = mk_cmd('foo')
        bar  = mk_cmd('bar')
        bam  = mk_cmd('bam')
        baz  = mk_cmd('baz')
        node = call_parse_if('check',
                             foo,
                             mk_cmd('if'),
                             bar,
                             mk_cmd('else'),
                             bam,
                             mk_cmd('endif'),
                             baz,
                             mk_cmd('endif'))
        assert(('check', [foo, ([], [bar], [bam]), baz], []) == node)

    def test_unmatched_endif_error(self):
        error = False
        try:
            call_parse_if('check', mk_cmd('add_library'))
        except RuntimeError:
            error = True
        assert(error)

class TestParse(TestCase):
    def test_empty(self):
        node = call_parse()
        assert([] == node)

    def test_one_non_if_command(self):
        add_lib = mk_cmd('add_library')
        node    = call_parse(add_lib)
        assert([add_lib] == node)

    def test_two_non_if_commands(self):
        add_lib = mk_cmd('add_library')
        add_exe = mk_cmd('add_executable')
        node    = call_parse(add_lib, add_exe)
        assert([add_lib, add_exe] == node)

    def test_command_with_if(self):
        add_lib = mk_cmd('add_library')
        add_exe = mk_cmd('add_executable')
        node    = call_parse(add_lib,
                             mk_cmd('if', 'c'),
                             add_exe,
                             mk_cmd('endif'))
        assert([add_lib, (['c'], [add_exe], [])] == node)

    def test_command_with_if_else(self):
        add_lib = mk_cmd('add_library')
        add_exe = mk_cmd('add_executable')
        include = mk_cmd('include')
        node    = call_parse(add_lib,
                             mk_cmd('if', 'c'),
                             add_exe,
                             mk_cmd('else'),
                             include,
                             mk_cmd('endif'))
        assert([add_lib, (['c'], [add_exe], [include])] == node)

