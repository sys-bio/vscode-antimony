import logging
# TODO remove this for production

from typing import Union
from stibium.ant_types import FileNode
from stibium.tree_builder import set_leaf_pointers, set_parents, transform_tree
from stibium.types import ASTNode, AntimonySyntaxError, SrcLocation, SrcPosition
from stibium.utils import get_abs_path, get_token_range
from .lark_patch import get_puppet

import os

from lark.visitors import Visitor
from lark import Lark, Token
from lark.tree import Meta, Tree
from lark.exceptions import (LexError, ParseError, UnexpectedCharacters,
                             UnexpectedInput, UnexpectedToken)

vscode_logger = logging.getLogger("vscode-antimony logger")

def get_grammar_str():
    '''Load the grammar string.'''
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, 'antimony.lark')) as r:
        grammar_str = r.read()

    return grammar_str


class ParentVisitor(Visitor):
    '''Lark Visitor that creates parent pointers in the constructed tree'''
    def __default__(self, tree):
        for subtree in tree.children:
            if isinstance(subtree, Tree):
                assert not hasattr(subtree, 'parent')
                setattr(subtree, 'parent', tree)


DUMMY_VALUE = "@@DUMMY@@"


def dummy_newline() -> Token:
    return Token('NEWLINE', DUMMY_VALUE, 0, 1, 1, 1, 1, 0)  # type: ignore


def is_dummy(node: Union[Token, Tree]):
    return isinstance(node, Token) and node.value == DUMMY_VALUE


def get_parser(grammar_str: str, cache_file: str):
    return Lark(grammar_str, start='root', parser='lalr',
                            propagate_positions=True,
                            keep_all_tokens=True,
                            maybe_placeholders=True,
                            lexer='contextual',
                            cache=cache_file)


class AntimonyParser:
    '''Frontend of a parser for Antimony, basically wrapping a Lark parser with error recovery.'''
    def __init__(self):
        grammar_str = get_grammar_str()
        cache_file = get_abs_path('.lark-cache')
        try:
            self.parser = get_parser(grammar_str, cache_file)
        except RuntimeError:
            os.remove(cache_file)
            self.parser = get_parser(grammar_str, cache_file)

    def parse(self, text: str, recoverable=False) -> FileNode:
        '''Parse the tree, automatically appending a newline character to the end of the given text.
        
        TODO docs
        '''
        tree: Tree
        root_puppet = get_puppet(self.parser, 'root', text)
        tree = self._parse_with_puppet(root_puppet, recoverable, text)
        vscode_logger.info("Parse tree:")
        vscode_logger.info(str(tree))
        # If text is empty, this tree would not have line or columns
        if len(tree.children) == 0:
            tree.meta.line = 1
            tree.meta.end_line = 1
            tree.meta.column = 1
            tree.meta.end_column = 1
            tree.meta.empty = False
        root = transform_tree(tree)
        assert root is not None and isinstance(root, FileNode)

        set_parents(root)
        set_leaf_pointers(root)
        return root

    def get_parse_tree_str(self, text: str, recoverable=False) -> str:
        root_puppet = get_puppet(self.parser, 'root', text)
        return str(self._parse_with_puppet(root_puppet, recoverable, text))

    def _parse_with_puppet(self, puppet, recoverable, text: str, token_callback = None):
        '''Parse with the given puppet in a recoverable way.
        '''
        if token_callback is None:
            token_callback = lambda _: None

        # HACK: this is to make error recovery behave normally in the case that there are
        # error tokens at the start of the text. In that case, the parser hasn't constructed a 
        # root node yet, so it is impossible to find the last "statement" node (from which to
        # construct an error node). In any case, this force-creates an empty statement in the tree
        # so that edge cases are avoided.
        # Two semicolons are fed because only after the second semicolon is fed, will the first
        # semicolon be parsed as an empty statement. Not sure why this is the case yet, but it
        # doesn't matter that much.
        if recoverable:
            INIT_TOKEN = dummy_newline()
            puppet.feed_token(INIT_TOKEN)
            puppet.feed_token(INIT_TOKEN)

        while True:
            try:
                # Main parser loop
                state = puppet.parser_state
                token = None
                for token in state.lexer.lex(state):
                    token_callback(token)
                    state.feed_token(token)

                # HACK feed one NEWLINE if there is no newline at the end of the file
                if token and token.type not in ('STMT_SEPARATOR', 'NEWLINE') and 'NEWLINE' in puppet.choices():
                    line_ctr = state.lexer.state.line_ctr
                    state.feed_token(Token('NEWLINE', '', line_ctr.char_pos, line_ctr.line,
                                     line_ctr.column, line_ctr.line,
                                     line_ctr.column, line_ctr.char_pos))  # type: ignore

                token = Token.new_borrow_pos(
                    '$END', '', token) if token else Token('$END', '', 0, 1, 1)  # type: ignore
                token_callback(token)
                tree = state.feed_token(token, True)

                # remove the dummy tokens
                if recoverable:
                    tree.children = tree.children[2:]

                return tree
            except UnexpectedCharacters as e:
                if recoverable:
                    self._recover_from_error(puppet, token_callback)
                else:
                    # re-throw error using our own class
                    raise AntimonySyntaxError(text[e.pos_in_stream], SrcPosition(e.line, e.column))
            except UnexpectedInput as e:
                token = getattr(e, 'token')
                if recoverable:
                    self._recover_from_error(puppet, token_callback, token)
                else:
                    # re-throw error using our class
                    range_ = get_token_range(token)
                    raise AntimonySyntaxError(token.value, range_.start, range_.end)

    def _recover_from_error(self, err_puppet, token_callback, token=None):
        '''Given a puppet in error, restore the puppet to a state from which it can keep parsing.

        Error tokens or error nodes may be created.
        '''
        def last_statement(state_stack, states):
            until_index = None
            for until_index, state_arg in reversed(list(enumerate(state_stack))):
                if 'simple_stmt' in states[state_arg]:
                    break
            return until_index

        def recover_stacks(value_stack, state_stack, start_index):
            '''Remove nodes/tokens preceding an error token in the parser stacks, so that the stacks
            are again at a valid state.

            Note that by default an ErrorNode containing the removed nodes/tokens is added to
            the stack in place of those tokens so as to preserve the tree.

            Args:
                value_stack: The parser value stack (for more details see LALR parsers and Lark)
                state_stack: The parser state stack
                start_index: The index of the first token in the *state stack* that needs to be
                             removed, i.e. the first token that has not been parsed as part of
                             a full statement.
            '''
            # I cannot remember the exact implementation details of Lark, but it seems that
            # the indexing of state stack is one higher than that of value stack. That's why
            # I'm decreasing it by 1 here.
            all_nodes = value_stack[start_index-1:]  # the nodes to remove

            if all_nodes:
                # if we added a dummy NEWLINE token previously (see 'HACK' below), then don't add
                # the token as an error node
                if not (len(all_nodes) == 1 and all_nodes[0] and is_dummy(all_nodes[0])):
                    # propgate positions
                    meta = Meta()
                    meta.line = all_nodes[0].line
                    meta.column = all_nodes[0].column
                    meta.end_line = all_nodes[-1].end_line
                    meta.end_column = all_nodes[-1].end_column
                    meta.empty = False
                    # create error node with removed nodes as children
                    node = Tree('error_node', all_nodes, meta=meta)
                    value_stack[start_index - 2].children.append(node)

                del state_stack[start_index:]
                del value_stack[start_index-1:]

                return True

            return False


        # create the error token
        manual_add = False
        if token:
            token.type = 'ERROR_TOKEN'
        else:
            # create token manually
            manual_add = True
            s = err_puppet.lexer_state.state
            p = s.line_ctr.char_pos
            if p == len(s.text):
                # unexpected EOF; don't add token
                token = None
            else:
                line = s.line_ctr.line
                col = s.line_ctr.column
                text = s.text[p]
                assert text != s.line_ctr.newline_char
                token = Token('ERROR_TOKEN', text, p, line, col, line, col + 1) # type: ignore

        # callback on the error token before updating the stacks
        if token is not None:
            token_callback(token)

        choices = err_puppet.choices()
        if 'NEWLINE' in choices:
            action, rule = choices['NEWLINE']
            if action.name == 'Reduce' and rule.origin.name == 'simple_stmt':
                # HACK it is possible that we have a full statement now, and we only need to reduce it.
                # We need to force it to be reduced by passing it a NEWLINE. A concrete example:
                # Suppose we are here:
                # 'a = 5;?'
                #        ^
                # Then parser_state.state_stack contains:
                # [..., Assignment, SEMICOLON]
                # This is not yet a simple_stmt. Ideally we want
                # [..., SimpleStmt(Assignment, SEMICOLON)]
                # so that we can produce a full statement before inserting the error token.
                # The easy hacky way to do so would be to check if NEWLINE is an expected token and
                # leads to Reduce. If so, we pass in NEWLINE, so that the state stack is like so
                # [..., SimpleStmt(...), NEWLINE]
                # And then pop the NEWLINE from the state stack
                err_puppet.feed_token(dummy_newline())

        # create error node if possible
        pstate = err_puppet.parser_state
        until_index = last_statement(pstate.state_stack, pstate.parse_conf.states)

        # make all nodes until the last statement to be the children of an error node
        # until_index is the last full statement. Increase it by 1 to get the first token to remove
        recover_stacks(pstate.value_stack, pstate.state_stack, until_index + 1)

        # finally, add error token
        if manual_add and token is not None:
            # advance the line counter if the token was manually created (since the token was not
            # resolved by Lark's lexer and thus the line counter was not updated)
            s = err_puppet.lexer_state.state
            s.line_ctr.feed(token.value)

        if token is not None:
            # token could be None if the EOF is unexpected. In this case we don't add the EOF as
            # an ErrorToken, since we normally never see EOF
            pstate.value_stack[-1].children.append(token)
    
    def get_puppet_at_position(self, text: str, stop_pos: SrcPosition):
        '''Get the parser puppet at the given source position
        TODO see note in Completer.__init__(). Possibly to get the leaf and get the previous token
        '''

        class PositionReached(Exception):
            pass

        def token_callback(token: Token):
            '''
            In those cases, stop (^ indicates lexer position, * indicates stop position)

            1) last_token      token
                         ^       *
            2) last_token      token
                         ^  *
            '''
            if token.type == '$END':
                raise PositionReached
            token_range = get_token_range(token)
            # token_range.end is exclusive, i.e. token at position 1 with length 1 would have end 2.
            if stop_pos < token_range.end:
                raise PositionReached

        # TODO OPTIMIZE: instead of re-parsing the entire text, try picking out only the
        # relevant lines nearby, and then parse only that.
        # that's why we want the leaf
        puppet = get_puppet(self.parser, 'root', text)
        try:
            self._parse_with_puppet(puppet, True, text, token_callback)
        except PositionReached:
            return puppet
        
        return puppet
