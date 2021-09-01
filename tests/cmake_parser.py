# tests.cmake_parser

import re

from typing import List, TextIO, Tuple, Union, Iterator, Any

Command = Tuple[str, List[str]]
# Using 'Any' below as mypy does not allow recursive types :(
IfNode = Tuple[List[str], List[Any], List[Any]]  # type: ignore
Node   = List[Union[Command, IfNode]]

def lex(input: TextIO) -> Iterator[Command]:
    input.seek(0)
    whitespace = re.compile('\s+')

    parsing_item    = False
    parsing_command = False
    command, args   = '', []
    while True:
        char = input.read(1)
        if char == '':
            break
        if whitespace.match(char):
            if parsing_item:
                assert(parsing_command)
                args.append('')
            parsing_item = False
        elif char == '(':
            if parsing_command:
                raise RuntimeError('Nested command')
            args.append('')
            parsing_command = True
            parsing_item    = False
        elif char == ')':
            if not parsing_command:
                raise RuntimeError('Unexpected ")"')
            if args[-1] == '':
                args = args[:-1]
            yield command, args
            command, args   = '', []
            parsing_item    = False
            parsing_command = False
        elif char == '#':
            while char != '\n':
                char = input.read(1)
        else:
            if parsing_command:
                args[-1] += char
            else:
                command += char
            parsing_item = True

def partial_match(lhs: Command, rhs: Command) -> bool:
    if lhs[0] != rhs[0]:
        return False

    if len(lhs[1]) > len(rhs[1]):
        return False

    for index, lhs_item in enumerate(lhs[1]):
        if lhs_item != rhs[1][index]:
            return False

    return True

def find_commands(commands: List[Command],
                  command:  str,
                  opt_args: None=None) -> List[Tuple[int, List[str]]]:
    args: List[str] = opt_args if opt_args is not None else []

    matches = []
    for index, item in enumerate(commands):
        if partial_match((command, args), item):
            matches.append((index, item[1]))
    return matches

def find_command(commands: List[Command],
                 command:  str,
                 opt_args: None=None) -> Tuple[int, List[str]]:
    args: List[str] = opt_args if opt_args is not None else []

    candidates = find_commands(commands, command, opt_args)
    if len(candidates) == 0:
        raise LookupError('Predicate ({}, {}) not found'.format(command, args))
    if len(candidates) > 1:
        raise RuntimeError('Ambiguous predicate ({}, {}) yielded {}'.format(
                                                                   command,
                                                                   args,
                                                                   candidates))
    return candidates[0]

def parse_if(predicate: List[str], commands: Iterator[Command]) -> IfNode:
    true_branch:  Node = []
    false_branch: Node = []

    branch = true_branch
    for command in commands:
        if 'if' == command[0]:
            branch.append(parse_if(command[1], commands))
        elif 'else' == command[0]:
            branch = false_branch
        elif 'endif' == command[0]:
            return (predicate, true_branch, false_branch)
        else:
            branch.append(command)
    raise RuntimeError('if with unmatched endif')

def parse(commands: Iterator[Command]) -> Node:
    result: Node = []

    for command in commands:
        if 'if' == command[0]:
            result.append(parse_if(command[1], commands))
        else:
            result.append(command)

    return result

