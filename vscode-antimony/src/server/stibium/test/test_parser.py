from dataclasses import dataclass
from types import NoneType
from typing import List, NamedTuple, Optional, Tuple, Union
from lark.tree import Tree
from stibium.ant_types import Annotation, ArithmeticExpr, Assignment, DeclItem, DeclModifiers, Declaration, FileNode, InComp, Keyword, Name, NameMaybeIn, Number, Operator, Reaction, ReactionName, SimpleStmt, Species, SpeciesList, StringLiteral, VarName
from stibium.parse import AntimonyParser
from stibium.utils import formatted_code
from stibium.types import AntimonySyntaxError, SrcPosition, SymbolType, Variability

import pytest


parser = AntimonyParser()


# TODO add more tests as more syntax features are added
@pytest.mark.parametrize('code', [
    'a = 12.5 * b',
    'J0: A + 3B -> 10C + $D; -+--+12 * a * (4 + 3.332 ^ $b23);',
    '',
    '''
const A = 10, A_2
formula B, CCC = 2 * (B - 3)
var $B = 2 * 5 * k, EF, IAC
J0: A + 3A_2 -> 2.5C; took

baggins = 5;;;

gamgee = 10

i122 identity "http://identifiers.org/chebi/CHEBI:17234"''',
'const compartment_, reaction_, _species, var1, const2, formula__',  # starts with reserved keyword
])
def test_formatted_code(code):
    tree = parser.parse(code)
    other_tree = parser.parse(code, recoverable=True)  # tree without error recovery
    assert tree == other_tree
    assert code == formatted_code(tree)


def test_end_marker():
    '''Ensure this handles end marker well.'''
    tree = parser.parse('foo = 3.5')
    assert len(tree.children) == 1
    tree = parser.parse('foo = 3.5;')
    assert len(tree.children) == 2  # the second statement is from ';' to EOF and is empty
    assert isinstance(tree.children[1], SimpleStmt) and tree.children[1].children[0] is None


def assert_reaction(reaction: Reaction, expected_reactants: List[Tuple[float, str]],
                    expected_products: List[Tuple[float, str]], name: str = None):

    # structural assertions
    assert len(reaction.children) == 7
    assert reaction.children[0] is None or isinstance(reaction.children[0], ReactionName)
    assert reaction.children[1] is None or isinstance(reaction.children[1], SpeciesList)
    assert isinstance(reaction.children[2], Operator)
    assert reaction.children[3] is None or isinstance(reaction.children[3], SpeciesList)
    assert isinstance(reaction.children[4], Operator)
    assert isinstance(reaction.children[5], (ArithmeticExpr, Name))
    assert reaction.children[6] is None or isinstance(reaction.children[6], InComp)
    assert reaction.children[1] is not None or reaction.children[3] is not None

    assert reaction.get_name_text() == name

    reactants = reaction.get_reactants()
    products = reaction.get_products()

    if reactants:
        assert isinstance(reaction.get_reactant_list(), SpeciesList)
    else:
        assert reaction.get_reactant_list() is None

    if products:
        assert isinstance(reaction.get_product_list(), SpeciesList)
    else:
        assert reaction.get_product_list() is None

    # actual test case
    assert [(s.get_stoich(), s.get_name_text()) for s in reactants] == expected_reactants
    assert [(s.get_stoich(), s.get_name_text()) for s in products] == expected_products


@pytest.mark.parametrize('code,expected_args', [
    # basic
    ('J0: A -> 2B; 2 * k;', ('1/A', '2/B', 'J0')),
    # same name
    ('A -> 2A; 2 * k;', ('1/A', '2/A', None)),
    # multiple reactants/products and rare float format
    ('J_33: A + 3.2B12 -> 2e4C + 1.2D + 0E; 2 * k;', ('1/A,3.2/B12', '2e4/C,1.2/D,0/E', 'J_33')),
    # no reactants
    ('J: => 2e4C + 1.2D + 0E; 2 * k', ('', '2e4/C,1.2/D,0/E', 'J')),
    # no products
    ('J: 2A->;3+k;', ('2/A', '', 'J')),
    # no name
    ('A + 22B72_ => 1.4C; 1', ('1/A,22/B72_', '1.4/C', None)),
    # no name or reactants
    ('-> 1.4C; 1;', ('', '1.4/C', None)),
])
def test_reaction(code: str, expected_args: Tuple[str, str, Optional[str]]):
    def parse_species_list(text: str):
        '''Helper for parsing expected species lists'''
        if not text:
            return []
        tokens = text.split(',')
        ret = list()
        for tok in tokens:
            subtoks = tok.split('/')
            assert len(subtoks) == 2
            stoich, name = subtoks
            ret.append((float(stoich), name))
        return ret

    # parse args using the baby test parser
    assert len(expected_args) == 3
    reactants = parse_species_list(expected_args[0])
    products = parse_species_list(expected_args[1])
    name = expected_args[2]

    tree = parser.parse(code)

    assert len(tree.children) in (1, 2)  # may or may not have a stmt_separator at the end
    stmt = tree.children[0]
    assert isinstance(stmt, SimpleStmt)

    reaction = stmt.get_stmt()
    assert isinstance(reaction, Reaction)

    assert_reaction(reaction, reactants, products, name)


def test_reaction_reversibility():
    tree = parser.parse('A -> B; 1')
    reaction = tree.children[0].children[0]
    assert isinstance(reaction, Reaction) and reaction.is_reversible()

    tree = parser.parse('A => B; 1')
    reaction = tree.children[0].children[0]
    assert isinstance(reaction, Reaction) and not reaction.is_reversible()


# Classes for easier testing
@dataclass
class DeclMod:
    variab: Variability
    type: SymbolType  # this is the formatted code of the value


@dataclass
class DeclItm:
    name: str
    value: str


@dataclass
class Decl:
    mod: DeclMod
    items: List[DeclItm]


@pytest.mark.parametrize('code,expected', [
    ('var a',
     Decl(mod=DeclMod(Variability.VARIABLE, SymbolType.Unknown), items=[DeclItm('a', '')])),

    ('const a22', Decl(mod=DeclMod(Variability.CONSTANT,
     SymbolType.Unknown), items=[DeclItm('a22', '')])),

    ('species a', Decl(mod=DeclMod(Variability.UNKNOWN,
     SymbolType.Species), items=[DeclItm('a', '')])),

    ('formula a_ = 12.5\n', Decl(mod=DeclMod(Variability.UNKNOWN,
     SymbolType.Parameter), items=[DeclItm('a_', '12.5')])),

    ('compartment a', Decl(mod=DeclMod(Variability.UNKNOWN,
     SymbolType.Compartment), items=[DeclItm('a', '')])),

    ('const species foo;', Decl(mod=DeclMod(Variability.CONSTANT,
     SymbolType.Species), items=[DeclItm('foo', '')])),

    ('var formula foo, b22=12.5,bar, c=-5e4* k - 2', Decl(mod=DeclMod(Variability.VARIABLE,
     SymbolType.Parameter), items=[DeclItm('foo', ''), DeclItm('b22', '12.5'), DeclItm('bar', ''),
     DeclItm('c', '-5e4 * k - 2')])),
])
def test_declaration(code: str, expected: Decl):
    # TODO
    tree = parser.parse(code)
    assert len(tree.children) in (1, 2)
    stmt = tree.children[0]
    assert isinstance(stmt, SimpleStmt) and len(stmt.children) == 2

    # structural assertions
    declaration = stmt.children[0]
    assert isinstance(declaration, Declaration)
    declmod = declaration.children[0]
    assert isinstance(declmod, DeclModifiers)
    assert declmod.children[0] is None or isinstance(declmod.children[0], Keyword)
    assert declmod.children[1] is None or isinstance(declmod.children[1], Keyword)
    assert declmod.children[2] is None or isinstance(declmod.children[2], Keyword)
    assert declmod.children[0] is not None or declmod.children[1] is not None or declmod.children[2] is not None
    assert isinstance(declaration.children[1], DeclItem)
    for i in range(2, len(declaration.children), 2):
        assert isinstance(declaration.children[i], Operator)
        assert isinstance(declaration.children[i + 1], DeclItem)

    # interface assertions
    mods = declaration.get_modifiers()
    assert mods.get_variab() == expected.mod.variab
    assert mods.get_type() == expected.mod.type

    items = declaration.get_items()
    assert [x.get_name_text() for x in items] == [x.name for x in expected.items]
    assert [formatted_code(x.get_value()) for x in items] == [x.value for x in expected.items]


@pytest.mark.parametrize('code', [
    # reactions
    '1: A -> B;1',  # illegal name
    ':A->B;1',  # no name
    '=>;1',  # no reactants or products

    # declarations/assignments
    'a, b',
    'a = 5, b',
    'a='

    # separators
    'a = \n5',  # cannot span multiple lines
    'a = ;5',  # similar to above
    'A -> B; a = 5'  # reaction divider is not the same as statement separator
    'A -> B\n5',  # reaction divider cannot be newline

    # numbers
    'a = 12e-2.2',

    # strings
    'a in "\\"',

    # comments
    'a = //',
    '''a = 5 /*
    multiline comment */ b = 10
    ''',  # antimony does not allow this, presumably because it straight up ignores the multiline
          # comment, so that there is no newline between 'a = 5' and 'b = 10'

    # reserved keywords (identity, hasPart, etc. are not reserved)
    'var species = 5',
    'var = 5',
    'compartment compartment = 2',
    'species = 2',
    'formula: A -> B;1',
])
def test_raises_syntax_error(code: str):
    '''Should fail for illegal reactions'''
    with pytest.raises(AntimonySyntaxError):
        parser.parse(code)

@pytest.mark.parametrize('code,expected', [
    ('c = $b', ('c', '$b')),
    ('a_ = ++-+-12.51e4', ('a_', '++-+-12.51e4')),
    ('b45=foo ^ 22 * (---3.3 + a15)', ('b45', 'foo ^ 22 * (---3.3 + a15)')),
])
def test_assignment(code: str, expected: Tuple[str, str]):
    tree = parser.parse(code)
    stmt = tree.children[0]
    assert isinstance(stmt, SimpleStmt)
    assignment = stmt.get_stmt()

    # structural assertions
    assert isinstance(assignment, Assignment)
    assert len(assignment.children) == 3
    assert isinstance(assignment.children[0], NameMaybeIn)
    assert isinstance(assignment.children[1], Operator)
    assert isinstance(assignment.children[2], (ArithmeticExpr, VarName))

    # interface assertions
    ename, evalue = expected
    assert assignment.get_name_text() == ename
    assert formatted_code(assignment.get_value()) == evalue


def get_assignment_value(code: str) -> Union[ArithmeticExpr, Name]:
    '''Must pass an assignment rule of format $var = $value. Return the value.'''
    tree = parser.parse(code)
    assert isinstance(tree.children[0], SimpleStmt)
    assignment = tree.children[0].get_stmt()
    assert isinstance(assignment, Assignment)
    return assignment.get_value()


@pytest.mark.parametrize('code,expected', [
    ('a = 5', 5),
    ('a = 12.5', 12.5),
    ('a = 3e4', 30000),
    ('a = 2E3', 2000),
    ('a = 12e-2', 12e-2),
    ('a = 00102', 102),
])
def test_numbers(code: str, expected: float):
    '''Test parsing numbers using assignment rules. No signed numbers since that would become
    more complicated than just a Number.
    '''
    val = get_assignment_value(code)
    assert isinstance(val, Number) and val.get_value() == expected


@pytest.mark.parametrize('code,name,keyword,uri', [
    ('i122 identity "http://identifiers.org/chebi/CHEBI:17234"', 'i122', 'identity',
        'http://identifiers.org/chebi/CHEBI:17234'),
    ('aga hasPart ""', 'aga', 'hasPart', ''),  # empty uri
    ('aga hasPart "\\n"', 'aga', 'hasPart', '\\n'),  # escaped character
    ('aga hasPart ";"', 'aga', 'hasPart', ';'),  # semicolon
    ('aga hasPart "const"', 'aga', 'hasPart', 'const'),  # keyword
])
def test_annotation(code: str, name: str, keyword: str, uri: str):
    # TODO
    tree = parser.parse(code)
    stmt = tree.children[0]
    assert len(stmt.children) == 2
    annotation = stmt.get_stmt()

    # structural assertions
    assert isinstance(annotation, Annotation)
    assert len(annotation.children) == 4
    assert isinstance(annotation.children[0], VarName)
    assert isinstance(annotation.children[1], Keyword)
    assert isinstance(annotation.children[2], StringLiteral)
    assert isinstance(annotation.children[3], NoneType)

    # interface assertions
    assert annotation.get_name_text() == name
    assert annotation.get_keyword() == keyword
    assert annotation.get_uri()[0] == uri


# test multiple statements separated by semicolon or newline
def test_multiple_statements():
    # TODO
    tree = parser.parse('''
    A -> B; c; a = 5.2; const compartment c = 12.5, d = 6
    J: C -> D; $foo * 66
    A identity "http://www.example.com"
    ''')
    
    # TODO once we add optimizations to merge statement separators, modify this test to reflec that

    # the first line is empty; therefore the first simplestmt is None
    assert isinstance(tree.children[0], SimpleStmt) and tree.children[0].get_stmt() is None
    assert isinstance(tree.children[1], SimpleStmt) and isinstance(tree.children[1].get_stmt(), Reaction)
    assert isinstance(tree.children[2], SimpleStmt) and isinstance(tree.children[2].get_stmt(), Assignment)
    assert isinstance(tree.children[3], SimpleStmt) and isinstance(tree.children[3].get_stmt(), Declaration)
    assert isinstance(tree.children[4], SimpleStmt) and isinstance(tree.children[4].get_stmt(), Reaction)
    assert isinstance(tree.children[5], SimpleStmt) and isinstance(tree.children[5].get_stmt(), Annotation)

    # verify one of the statement
    assignment = tree.children[2].get_stmt()
    assert isinstance(assignment, Assignment)
    assert assignment.get_name_text() == 'a'
    val = assignment.get_value()
    assert isinstance(val, Number)
    assert val.get_value() == 5.2


def test_node_range():
    tree = parser.parse('beef   =37.2 * $B\n   A->B;1     ;')
    assignment = tree.children[0].get_stmt()
    assert isinstance(assignment, Assignment)
    assert assignment.range.start == SrcPosition(1, 1)
    assert assignment.range.end == SrcPosition(1, 18)  # range is end-exclusive and also excludes \n

    nmi = assignment.children[0]
    assert nmi.range.start == SrcPosition(1, 1)
    assert nmi.range.end == SrcPosition(1, 5)

    op = assignment.children[1]
    assert op.range.start == SrcPosition(1, 8)
    assert op.range.end == SrcPosition(1, 9)

    val = assignment.children[2]
    assert val.range.start == SrcPosition(1, 9)
    assert val.range.end == SrcPosition(1, 18)

    reaction = tree.children[1].get_stmt()
    assert tree.children[1].range.start == SrcPosition(2, 4)
    assert tree.children[1].range.end == SrcPosition(2, 16)  # includes ;

    assert reaction.range.start == SrcPosition(2, 4)
    assert reaction.range.end == SrcPosition(2, 10)  # excludes the whitespace after that


# TODO test comments
@pytest.mark.parametrize('code,reconstructed', [
    ('a = 5//comment\nb =    6', 'a = 5\nb = 6'),
    ('a = 5  //comment;b =    6', 'a = 5'),  # comment is not broken by ';'
    ('A -> B; 1 /* multi\nline\ncomment   */\nvar c', 'A -> B; 1\nvar c')
])
def test_comments(code: str, reconstructed: str):
    tree = parser.parse(code)
    assert formatted_code(tree) == reconstructed

