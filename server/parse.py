from lark_patch import get_puppet

import os
from lark import Lark, Token
from lark.tree import Tree
from lark.exceptions import (LexError, ParseError, UnexpectedCharacters,
                             UnexpectedInput, UnexpectedToken)


def get_grammar_str():
    '''Load the grammar string.'''
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, 'antimony.lark')) as r:
        grammar_str = r.read()
    return grammar_str


class AntimonyParser:
    '''Frontend of a parser for Antimony, basically wrapping a Lark parser with error recovery.'''
    def __init__(self):
        grammar_str = get_grammar_str()
        self.parser = Lark(grammar_str, start='root', parser='lalr',
                                propagate_positions=True,
                                keep_all_tokens=True,
                                maybe_placeholders=True)

    def parse(self, text: str, recover=True):
        text += '\n'

        if recover:
            root_puppet = get_puppet(self.parser, 'root', text)
            return self._recoverable_parse(root_puppet)
        else:
            return self.parser.parse(text)

    def _recoverable_parse(self, puppet):
        while True:
            state = puppet.parser_state
            try:
                token = None
                for token in state.lexer.lex(state):
                    state.feed_token(token)

                token = Token.new_borrow_pos(
                    '$END', '', token) if token else Token('$END', '', 0, 1, 1) # type: ignore
                return state.feed_token(token, True)
            except UnexpectedCharacters:
                self._recover_from_error(puppet)
            except UnexpectedInput as e:
                # Encountered error; try to recover
                self._recover_from_error(puppet, getattr(e, 'token'))
            except Exception as e:
                # if self.debug:
                #     print("")
                #     print("STATE STACK DUMP")
                #     print("----------------")
                #     for i, s in enumerate(state.state_stack):
                #         print('%d)' % i , s)
                #     print("")
                raise

    def _recover_from_error(self, err_puppet, token=None):
        '''Given a puppet, return a copy of it with the lexer located at the next statement separator.

        All tokens between the current lexer position and the next statement separator are skipped.
        '''
        def last_suite(state_stack, states):
            until_index = None
            # For now just discard everything that is not a suite or
            # file_input, if we detect an error.
            for until_index, state_arg in reversed(list(enumerate(state_stack))):
                # `suite` can sometimes be only simple_stmt, not stmt.
                if 'full_statement' in states[state_arg]:
                    break
            return until_index

        def update_stacks(value_stack, state_stack, start_index):
            all_nodes = value_stack[start_index-1:]

            if all_nodes:
                node = Tree('error_node', all_nodes)
                value_stack[start_index - 2].children.append(node)
                del state_stack[start_index:]
                del value_stack[start_index-1:]

            return bool(all_nodes)

        pstate = err_puppet.parser_state
        until_index = last_suite(pstate.state_stack, pstate.parse_conf.states)

        if update_stacks(pstate.value_stack, pstate.state_stack, until_index + 1):
            # re-feed this token later
            if token:
                s = err_puppet.lexer_state.state
                s.line_ctr.char_pos = token.pos_in_stream
        else:
            # No error node created; create token instead
            if token:
                token.type = 'error_token'
                pstate.value_stack[-1].children.append(token)
                return

            s = err_puppet.lexer_state.state
            p = s.line_ctr.char_pos
            tok = Token('error_token', s.text[p], p, s.line_ctr.line, s.line_ctr.column) # type: ignore
            pstate.value_stack[-1].children.append(tok)
            s.line_ctr.feed('?')
