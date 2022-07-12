import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)

from bioservices_server.utils import sb_position
from typing import Tuple
from stibium.analysis import AntTreeAnalyzer
from stibium.ant_types import Annotation, ArithmeticExpr, Assignment, DeclItem, DeclModifiers, Declaration, FileNode, InComp, Keyword, Name, NameMaybeIn, Number, Operator, Reaction, ReactionName, SimpleStmt, Species, SpeciesList, StringLiteral, VarName
from stibium.api import AntFile
from stibium.parse import AntimonyParser
from stibium.types import IncompatibleType, IssueSeverity, ObscuredValue, SrcPosition, SrcRange, UnexpectedEOFIssue, UnexpectedNewlineIssue, UnexpectedTokenIssue

from pygls.workspace import Document

import pytest

parser = AntimonyParser()
directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-data")

# some of the following test data are from Lucian Smith, https://github.com/sys-bio/antimony/tree/develop/src/test/test-data
@pytest.mark.parametrize('code', [
    # constant supported, this can be one way of declaring a boundary species
    ('const S1;'),
    ('const species S1;'),
    ('const species S1, S2, S3;'),
    ('var species S4, S5, S6;'),
    # boundary species
    ('species S1, $S2, $S3, S4, S5, $S6;'),
    # unit supported
    ('unit voltage = 1e3 gram * metre^2 / (second^3 * ampere);'), #compound units
    ('a=-(x+2)'),  # negative parenthesis
    # hasPart supported in SBO and cvterms
    ('''a=3
a hasPart "BQB_thing"'''), # hasPart
    ('''species x;
x = 3;'''), # species initialization
    ('''model foo()
 species x;
end

model bar()
 A: foo();
end'''), # default sub compartment
    ('''a = 3;
const a;
a identity "BQB_thing"'''), # identity
])

def test_no_issues(code):
    '''
    Test implemented grammar
    '''
    antfile = AntFile('', code)
    assert len(antfile.get_issues()) == 0
    

@pytest.mark.parametrize('code,expected_parse_tree_str', [
    ('# this is a comment', "Tree('root', [])"),
    ('// this is another comment', "Tree('root', [])"),
    ('/* one more cooment \n new line here */', "Tree('root', [])"),
])
def test_comment(code, expected_parse_tree_str):
    '''
    test comments
    '''
    antfile = AntFile('', code)
    assert len(antfile.get_issues()) == 0
    tree = parser.get_parse_tree_str(code)
    assert str(tree) == expected_parse_tree_str,\
        f"comment test failed"
        
        
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('reaction001',"Tree('root', [Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'compartment')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'default_compartment')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('reaction', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', '_J0')]), None]), Token('COLON', ':')]), Tree('species_list', [Tree('species', [None, None, Token('NAME', 'S1')])]), Token('ARROW', '->'), None, Token('SEMICOLON', ';'), Tree('product', [Tree('var_name', [None, Token('NAME', 'default_compartment')]), Token('STAR', '*'), Tree('var_name', [None, Token('NAME', 'S1')])]), None]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'default_compartment')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '')])])"),
    ('reactionIn',"Tree('root', [Tree('simple_stmt', [Tree('reaction', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'J0')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'C')])])]), Token('COLON', ':')]), None, Token('ARROW', '->'), Tree('species_list', [Tree('species', [None, None, Token('NAME', 'a')])]), Token('SEMICOLON', ';'), Tree('var_name', [None, Token('NAME', 'k1')]), None]), Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'k1')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('NEWLINE', '\\n')])])"),
    ('reactionIn_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'compartment')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'C')])])]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('reaction', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'J0')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'C')])])]), Token('COLON', ':')]), None, Token('ARROW', '->'), Tree('species_list', [Tree('species', [None, None, Token('NAME', 'a')])]), Token('SEMICOLON', ';'), Tree('var_name', [None, Token('NAME', 'k1')]), None]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'k1')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), None]), Token('COMMA', ','), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'k1')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('reaction',"Tree('root', [Tree('simple_stmt', [Tree('reaction', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'J0')]), None]), Token('COLON', ':')]), Tree('species_list', [Tree('species', [None, None, Token('NAME', 'a')])]), Token('ARROW', '->'), None, Token('SEMICOLON', ';'), Tree('var_name', [None, Token('NAME', 'k1')]), None]), Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'k1')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('reaction_rt', "Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('reaction', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'J0')]), None]), Token('COLON', ':')]), Tree('species_list', [Tree('species', [None, None, Token('NAME', 'a')])]), Token('ARROW', '->'), None, Token('SEMICOLON', ';'), Tree('var_name', [None, Token('NAME', 'k1')]), None]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'k1')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'k1')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    #('namedstoich_assignment',""),
    ('namedstoich_assignment_rt',""),
    #('namedstoich_basic',""),
    ('namedstoich_basic_rt',""),
    #('namedstoich_value',""),
    ('namedstoich_value_rt',""),
]) # all reactions included

def test_reactions(file_name, expected_parse_tree_str):
    '''
    test for reaction
    '''
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
        
        
@pytest.mark.parametrize('code,file_name,expected_parse_tree_str', [
    ('a = ;','',"Tree('root', [])"),
    ('','assignmentRule',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('AEQ', ':='), Token('NUMBER', '4.8')]), Token('NEWLINE', '')])])"),
    ('','assignmentRule_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('AEQ', ':='), Token('NUMBER', '4.8')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'var')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('','initialAmount',"Tree('root', [Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'C')])])]), Tree('decl_assignment', [Token('EQUAL', '='), Tree('product', [Token('NUMBER', '3'), Token('SLASH', '/'), Tree('var_name', [None, Token('NAME', 'C')])])])])]), Token('NEWLINE', '\\n')])])"),
    ('','initialAmount_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'compartment')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'C')])])]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Tree('product', [Token('NUMBER', '3'), Token('SLASH', '/'), Tree('var_name', [None, Token('NAME', 'C')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('','initialAssignment',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Tree('product', [Token('NUMBER', '4'), Token('SLASH', '/'), Token('NUMBER', '6')])]), Token('NEWLINE', '\\n')])])"),
    ('','initialAssignment_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Tree('product', [Token('NUMBER', '4'), Token('SLASH', '/'), Token('NUMBER', '6')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('','initialConcentration',"Tree('root', [Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Tree('decl_assignment', [Token('EQUAL', '='), Token('NUMBER', '3')])])]), Token('NEWLINE', '\\n')])])"),
    ('','initialConcentration_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('','initialValue',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('NEWLINE', '\\n')])])"),
    ('','initialValue_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('','parameter',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('NEWLINE', '\\n')])])"),
    ('','parameter_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('','parameter_inf',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'inf')])]), Token('NEWLINE', '\\n')])])"),
    ('','parameter_inf_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'inf')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('','parameter_nan',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'NaN')])]), Token('NEWLINE', '\\n')])])"),
    ('','parameter_nan_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'NaN')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('','parameter_neginf',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Tree('atom', [Token('MINUS', '-'), Tree('var_name', [None, Token('NAME', 'infinity')])])]), Token('NEWLINE', '\\n')])])"),
    ('','parameter_neginf_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Tree('atom', [Token('MINUS', '-'), Tree('var_name', [None, Token('NAME', 'inf')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
])
def test_initializing_values(code, file_name, expected_parse_tree_str):
    '''
    either using code or file to test
    '''
    if code == '':
        f = os.path.join(directory, file_name + '.ant')
        doc = Document(os.path.abspath(f))
        ant_file = AntFile(doc.path, doc.source)
        
    else:
        ant_file = AntFile('',code)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('species',"Tree('root', [Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'y')])])]), None])]), Token('NEWLINE', '\\n')])])"),
    ('species_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'compartment')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'y')])])]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
])
def test_define(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            

@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('compartment_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'compartment')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), None]), None]), Token('COMMA', ','), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('default_compartment',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'def_comp'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'compartment')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'default_compartment')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'S1')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('reaction', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', '_J0')]), None]), Token('COLON', ':')]), Tree('species_list', [Tree('species', [None, None, Token('NAME', 'S1')])]), Token('ARROW', '->'), None, Token('SEMICOLON', ';'), Tree('product', [Tree('var_name', [None, Token('NAME', 'default_compartment')]), Token('STAR', '*'), Tree('var_name', [None, Token('NAME', 'S1')])]), None]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'S1')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'default_compartment')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'default_compartment')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '')])])"),
    ('defaultOrNotCompartment_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'compartment')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'C')])])]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'C')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'baz'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'B')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('defaultOrNotCompartment',"Tree('root', [Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'y')]), Tree('in_comp', [Token('IN', 'in'), Tree('var_name', [None, Token('NAME', 'C')])])]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'baz'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'B')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('defaultSubCompartment',"Tree('root', [Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('defaultSubCompartment_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('defaultSubSubCompartment',"Tree('root', [Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'baz'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('defaultSubSubCompartment_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'baz'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
])
def test_compartment(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''

            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('BIOMD0000000118',""),
    ('function_name','Tree(\'root\', [Tree(\'function\', [Token(\'FUNCTION\', \'function\'), Token(\'NAME\', \'foo\'), Token(\'LPAR\', \'(\'), None, Token(\'RPAR\', \')\'), Token(\'NEWLINE\', \'\\n\'), Token(\'NUMBER\', \'3\'), Token(\'SEMICOLON\', \';\'), Token(\'NEWLINE\', \'\\n\'), Token(\'END\', \'end\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'is_assignment\', [Token(\'NAME\', \'foo\'), Token(\'IS\', \'is\'), Token(\'ESCAPED_STRING\', \'"foo!"\')]), Token(\'NEWLINE\', \'\')])])'),
    ('function_name_rt','Tree(\'root\', [Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'function\', [Token(\'FUNCTION\', \'function\'), Token(\'NAME\', \'foo\'), Token(\'LPAR\', \'(\'), None, Token(\'RPAR\', \')\'), Token(\'NEWLINE\', \'\\n\'), Token(\'NUMBER\', \'3\'), Token(\'SEMICOLON\', \';\'), Token(\'NEWLINE\', \'\\n\'), Token(\'END\', \'end\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [Tree(\'is_assignment\', [Token(\'NAME\', \'foo\'), Token(\'IS\', \'is\'), Token(\'ESCAPED_STRING\', \'"foo!"\')]), Token(\'NEWLINE\', \'\')])])'),
    ('SBO_function', "Tree('root', [Tree('function', [Token('FUNCTION', 'function'), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Token('NEWLINE', '\\n'), Token('NUMBER', '3'), Token('SEMICOLON', ';'), Token('NEWLINE', '\\n'), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')])])"),
    ('SBO_function_rt', "Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('function', [Token('FUNCTION', 'function'), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Token('NEWLINE', '\\n'), Token('NUMBER', '3'), Token('SEMICOLON', ';'), Token('NEWLINE', '\\n'), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')])])"),
    
])
def test_function(file_name,expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('identity','Tree(\'root\', [Tree(\'simple_stmt\', [Tree(\'assignment\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'a\')]), None]), Token(\'EQUAL\', \'=\'), Token(\'NUMBER\', \'3\')]), Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'annotation\', [Tree(\'var_name\', [None, Token(\'NAME\', \'a\')]), Token(\'ANNOT_KEYWORD\', \'identity\'), Token(\'ESCAPED_STRING\', \'"BQB_thing"\')]), Token(\'NEWLINE\', \'\\n\')])])'),
    ('identity_rt','Tree(\'root\', [Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'assignment\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'a\')]), None]), Token(\'EQUAL\', \'=\'), Token(\'NUMBER\', \'3\')]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'declaration\', [Tree(\'decl_modifiers\', [Token(\'VAR_MODIFIER\', \'const\')]), Tree(\'decl_item\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'a\')]), None]), None])]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'annotation\', [Tree(\'var_name\', [None, Token(\'NAME\', \'a\')]), Token(\'ANNOT_KEYWORD\', \'identity\'), Token(\'ESCAPED_STRING\', \'"BQB_thing"\')]), Token(\'NEWLINE\', \'\')])])'),
])
def test_annotation(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''

    

@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('BIOMD0000000696','Tree(\'root\', [Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'modular_model\', [Token(\'MODEL\', \'model\'), Token(\'STAR\', \'*\'), Token(\'NAME\', \'Boada2016___Incoherent_type_1_feed_forward_loop__I1_FFL\'), Token(\'LPAR\', \'(\'), None, Token(\'RPAR\', \')\'), Tree(\'simple_stmt_list\', [Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'declaration\', [Tree(\'decl_modifiers\', [Token(\'TYPE_MODIFIER\', \'compartment\')]), Tree(\'decl_item\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'Cell\')]), None]), None])]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'declaration\', [Tree(\'decl_modifiers\', [Token(\'TYPE_MODIFIER\', \'species\')]), Tree(\'decl_item\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'x6\')]), Tree(\'in_comp\', [Token(\'IN\', \'in\'), Tree(\'var_name\', [None, Token(\'NAME\', \'Cell\')])])]), None])]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'assignment\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'x6\')]), None]), Token(\'EQUAL\', \'=\'), Token(\'NUMBER\', \'0\')]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'assignment\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'Cell\')]), None]), Token(\'EQUAL\', \'=\'), Token(\'NUMBER\', \'1\')]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'assignment\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'P_theta\')]), None]), Token(\'EQUAL\', \'=\'), Token(\'NUMBER\', \'1\')]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'declaration\', [Tree(\'decl_modifiers\', [Token(\'VAR_MODIFIER\', \'var\')]), Tree(\'decl_item\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'P_theta\')]), None]), None])]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'declaration\', [Tree(\'decl_modifiers\', [Token(\'VAR_MODIFIER\', \'const\')]), Tree(\'decl_item\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'Cell\')]), None]), None])]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')])]), Token(\'END\', \'end\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [Tree(\'is_assignment\', [Token(\'NAME\', \'Boada2016___Incoherent_type_1_feed_forward_loop__I1_FFL\'), Token(\'IS\', \'is\'), Token(\'ESCAPED_STRING\', \'"Boada2016 - Incoherent type 1 feed-forward loop (I1-FFL)"\')]), Token(\'NEWLINE\', \'\')])])'),
    ('hierarchy',"Tree('root', [Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('hierarchy_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('module_name','Tree(\'root\', [Tree(\'modular_model\', [Token(\'MODEL\', \'model\'), None, Token(\'NAME\', \'foo\'), Token(\'LPAR\', \'(\'), None, Token(\'RPAR\', \')\'), Tree(\'simple_stmt_list\', [Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'assignment\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'a\')]), None]), Token(\'EQUAL\', \'=\'), Token(\'NUMBER\', \'3\')]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')])]), Token(\'END\', \'end\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'is_assignment\', [Token(\'NAME\', \'foo\'), Token(\'IS\', \'is\'), Token(\'ESCAPED_STRING\', \'"foo!"\')]), Token(\'NEWLINE\', \'\\n\')])])'),
    ('module_name_rt','Tree(\'root\', [Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'modular_model\', [Token(\'MODEL\', \'model\'), Token(\'STAR\', \'*\'), Token(\'NAME\', \'foo\'), Token(\'LPAR\', \'(\'), None, Token(\'RPAR\', \')\'), Tree(\'simple_stmt_list\', [Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'assignment\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'a\')]), None]), Token(\'EQUAL\', \'=\'), Token(\'NUMBER\', \'3\')]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'declaration\', [Tree(\'decl_modifiers\', [Token(\'VAR_MODIFIER\', \'const\')]), Tree(\'decl_item\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'a\')]), None]), None])]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')])]), Token(\'END\', \'end\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [Tree(\'is_assignment\', [Token(\'NAME\', \'foo\'), Token(\'IS\', \'is\'), Token(\'ESCAPED_STRING\', \'"foo!"\')]), Token(\'NEWLINE\', \'\')])])'),
    ('port',"Tree('root', [Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), Tree('parameters', [Token('NAME', 'x')]), Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), Tree('parameters', [Token('NAME', 'X')]), Token('RPAR', ')')]), Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('port_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), Tree('parameters', [Token('NAME', 'x')]), Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'bar'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), Tree('parameters', [Token('NAME', 'X')]), Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
])
def test_modular_models(file_name,expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('substance_only_species',"Tree('root', [Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('SUB_MODIFIER', 'substanceOnly'), Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'S1')]), None]), None])]), Token('NEWLINE', '\\n')])])"),
    ('substance_only_species_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('SUB_MODIFIER', 'substanceOnly'), Token('TYPE_MODIFIER', 'species')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'S1')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'S1')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
])
def test_substance_only_species(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('deleteAssignmentRuleDirect',"Tree('root', [Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'P1')]), None]), Token('AEQ', ':='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar1'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('AEQ', ':='), Token('NUMBER', '0')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('deleteAssignmentRuleDirect_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'P1')]), None]), Token('AEQ', ':='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'var')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'P1')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'bar1'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('AEQ', ':='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('deleteAssignmentRuleIndirect', "Tree('root', [Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'P1')]), None]), Token('AEQ', ':='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'bar1'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('deleteAssignmentRuleIndirect_rt', "Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), None, Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'P1')]), None]), Token('AEQ', ':='), Token('NUMBER', '3')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'var')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'P1')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'bar1'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('mmodel_call', [Tree('reaction_name', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'A')]), None]), Token('COLON', ':')]), Token('NAME', 'foo'), Token('LPAR', '('), None, Token('RPAR', ')')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
])
def test_assignment_rules(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('names','Tree(\'root\', [Tree(\'simple_stmt\', [Tree(\'is_assignment\', [Token(\'NAME\', \'x\'), Token(\'IS\', \'is\'), Token(\'ESCAPED_STRING\', \'"This Name!"\')]), Token(\'NEWLINE\', \'\\n\')])])'),
    ('names_rt','Tree(\'root\', [Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'assignment\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'x\')]), None]), Token(\'EQUAL\', \'=\'), Token(\'NUMBER\', \'1\')]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'declaration\', [Tree(\'decl_modifiers\', [Token(\'VAR_MODIFIER\', \'const\')]), Tree(\'decl_item\', [Tree(\'namemaybein\', [Tree(\'var_name\', [None, Token(\'NAME\', \'x\')]), None]), None])]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\\n\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')]), Tree(\'simple_stmt\', [Tree(\'is_assignment\', [Token(\'NAME\', \'x\'), Token(\'IS\', \'is\'), Token(\'ESCAPED_STRING\', \'"This Name!"\')]), Token(\'SEMICOLON\', \';\')]), Tree(\'simple_stmt\', [None, Token(\'NEWLINE\', \'\\n\')])])'),
])
def test_display_names(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('compound_units1',"Tree('root', [Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'voltage')]), Token('EQUAL', '='), Tree('product', [Tree('atom', [Token('NUMBER', '1000'), Tree('var_name', [None, Token('NAME', 'grams')])]), Token('STAR', '*'), Tree('power', [Tree('atom', [Token('NUMBER', '1'), Tree('var_name', [None, Token('NAME', 'meters')])]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])])]), Token('NEWLINE', '\\n')])])"),
    ('compound_units1_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'voltage')]), Token('EQUAL', '='), Tree('product', [Tree('atom', [Token('NUMBER', '1e3'), Tree('var_name', [None, Token('NAME', 'gram')])]), Token('STAR', '*'), Tree('power', [Tree('var_name', [None, Token('NAME', 'metre')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('compound_units2',"Tree('root', [Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'voltage')]), Token('EQUAL', '='), Tree('product', [Tree('product', [Tree('product', [Tree('atom', [Token('NUMBER', '1000'), Tree('var_name', [None, Token('NAME', 'grams')])]), Token('STAR', '*'), Tree('power', [Tree('var_name', [None, Token('NAME', 'meters')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])]), Token('SLASH', '/'), Tree('power', [Tree('var_name', [None, Token('NAME', 'seconds')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '3')])]), Token('SLASH', '/'), Tree('var_name', [None, Token('NAME', 'ampere')])])]), Token('NEWLINE', '\\n')])])"),
    ('compound_units2_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'voltage')]), Token('EQUAL', '='), Tree('product', [Tree('product', [Tree('atom', [Token('NUMBER', '1e3'), Tree('var_name', [None, Token('NAME', 'gram')])]), Token('STAR', '*'), Tree('power', [Tree('var_name', [None, Token('NAME', 'metre')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])]), Token('SLASH', '/'), Tree('atom', [Token('LPAR', '('), Tree('product', [Tree('power', [Tree('var_name', [None, Token('NAME', 'second')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '3')]), Token('STAR', '*'), Tree('var_name', [None, Token('NAME', 'ampere')])]), Token('RPAR', ')')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('compound_units3',"Tree('root', [Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'voltage')]), Token('EQUAL', '='), Tree('product', [Tree('product', [Tree('product', [Tree('atom', [Token('NUMBER', '1000'), Tree('var_name', [None, Token('NAME', 'grams')])]), Token('STAR', '*'), Tree('power', [Tree('atom', [Token('NUMBER', '1'), Tree('var_name', [None, Token('NAME', 'meters')])]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])]), Token('SLASH', '/'), Tree('power', [Tree('atom', [Token('NUMBER', '1'), Tree('var_name', [None, Token('NAME', 'seconds')])]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '3')])]), Token('SLASH', '/'), Tree('atom', [Token('NUMBER', '1'), Tree('var_name', [None, Token('NAME', 'ampere')])])])]), Token('NEWLINE', '\\n')])])"),
    ('compound_units3_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'voltage')]), Token('EQUAL', '='), Tree('product', [Tree('product', [Tree('atom', [Token('NUMBER', '1e3'), Tree('var_name', [None, Token('NAME', 'gram')])]), Token('STAR', '*'), Tree('power', [Tree('var_name', [None, Token('NAME', 'metre')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])]), Token('SLASH', '/'), Tree('atom', [Token('LPAR', '('), Tree('product', [Tree('power', [Tree('var_name', [None, Token('NAME', 'second')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '3')]), Token('STAR', '*'), Tree('var_name', [None, Token('NAME', 'ampere')])]), Token('RPAR', ')')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('compound_units4',"Tree('root', [Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'persecondsq')]), Token('EQUAL', '='), Tree('product', [Token('NUMBER', '1'), Token('SLASH', '/'), Tree('power', [Tree('var_name', [None, Token('NAME', 'seconds')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])])]), Token('NEWLINE', '\\n')])])"),
    ('compound_units4_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'persecondsq')]), Token('EQUAL', '='), Tree('product', [Token('NUMBER', '1'), Token('SLASH', '/'), Tree('power', [Tree('var_name', [None, Token('NAME', 'second')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('global_units',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'length')]), None]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'meters')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'area')]), None]), Token('EQUAL', '='), Tree('power', [Tree('var_name', [None, Token('NAME', 'meters')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'volume')]), None]), Token('EQUAL', '='), Tree('power', [Tree('var_name', [None, Token('NAME', 'meters')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '3')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'substance')]), None]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'moles')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'extent')]), None]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'dimensionless')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'time_unit')]), None]), Token('EQUAL', '='), Tree('product', [Tree('var_name', [None, Token('NAME', 'seconds')]), Token('STAR', '*'), Token('NUMBER', '60')])]), Token('NEWLINE', '\\n')])])"),
    ('global_units_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'length')]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'metre')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'area')]), Token('EQUAL', '='), Tree('power', [Tree('var_name', [None, Token('NAME', 'metre')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '2')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'volume')]), Token('EQUAL', '='), Tree('power', [Tree('var_name', [None, Token('NAME', 'metre')]), Token('CIRCUMFLEX', '^'), Token('NUMBER', '3')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'substance')]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'mole')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'extent')]), Token('EQUAL', '='), Tree('var_name', [None, Token('NAME', 'dimensionless')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'time_unit')]), Token('EQUAL', '='), Tree('atom', [Token('NUMBER', '6e1'), Tree('var_name', [None, Token('NAME', 'second')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    ('same_unit_name',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('modular_model', [Token('MODEL', 'model'), Token('STAR', '*'), Token('NAME', 'same_units'), Token('LPAR', '('), None, Token('RPAR', ')'), Tree('simple_stmt_list', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '6')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_assignment', [Tree('var_name', [None, Token('NAME', 'x')]), Token('HAS', 'has'), Tree('var_name', [None, Token('NAME', 'x_unit')])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'x_unit')]), Token('EQUAL', '='), Tree('product', [Tree('var_name', [None, Token('NAME', 'second')]), Token('SLASH', '/'), Tree('var_name', [None, Token('NAME', 'litre')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])]), Token('END', 'end')]), Tree('simple_stmt', [None, Token('NEWLINE', '')])])"),
    ('units',"Tree('root', [Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'mL')]), Token('EQUAL', '='), Tree('product', [Token('NUMBER', '.001'), Token('STAR', '*'), Tree('var_name', [None, Token('NAME', 'liters')])])]), Token('NEWLINE', '\\n')])])"),
    ('units_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('unit_declaration', [Token('UNIT', 'unit'), Tree('var_name', [None, Token('NAME', 'mL')]), Token('EQUAL', '='), Tree('atom', [Token('NUMBER', '1e-3'), Tree('var_name', [None, Token('NAME', 'litre')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')])])"),
    
])
def test_units(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('negparen',"Tree('root', [Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Tree('atom', [Token('MINUS', '-'), Tree('atom', [Token('LPAR', '('), Tree('sum', [Tree('var_name', [None, Token('NAME', 'x')]), Token('PLUS', '+'), Token('NUMBER', '2')]), Token('RPAR', ')')])])]), Token('NEWLINE', '\\n')])])"),
    ('negparen_rt',"Tree('root', [Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), Token('EQUAL', '='), Tree('atom', [Token('MINUS', '-'), Tree('atom', [Token('LPAR', '('), Tree('sum', [Tree('var_name', [None, Token('NAME', 'x')]), Token('PLUS', '+'), Token('NUMBER', '2')]), Token('RPAR', ')')])])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), Token('EQUAL', '='), Token('NUMBER', '1')]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [None, Token('NEWLINE', '\\n')]), Tree('simple_stmt', [Tree('declaration', [Tree('decl_modifiers', [Token('VAR_MODIFIER', 'const')]), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'a')]), None]), None]), Token('COMMA', ','), Tree('decl_item', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'x')]), None]), None])]), Token('SEMICOLON', ';')]), Tree('simple_stmt', [None, Token('NEWLINE', '')])])"),
])
def test_negative_parenthesis(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('replaceAssignmentRule',""),
    ('replaceAssignmentRule_rt',""),
    ('replaceCompartment',""),
    ('replaceCompartment_rt',""),
    ('replaceInitialAssignment',""),
    ('replaceInitialAssignment_rt',""),
    ('replaceParameter',""),
    ('replaceParameter_rt',""),
])
def test_replace(file_name, expected_parse_tree_str):
    '''
    warning: not implemented feature
    '''
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0
    # if error_count == 0:
    #     actual_str = parser.get_parse_tree_str(ant_file.text)
    #     assert expected_parse_tree_str == actual_str,\
    #         f'''Logging actual {repr(actual_str)} \n'''


#
# from here, testing is for not implemented features
#
        
@pytest.mark.parametrize('code,issue_num,issue_index', [
    ('a.confidenceInterval = {0, 25}', 4, 0),
    ('a.variance = 25', 1, 0),
    ('A.distribution is "http://uri"', 2, 1)
])
def test_uncertainty_information(code, issue_num, issue_index):
    '''
    uncertainty information
    for more specific syntax of uncertainty information, go to:
    https://tellurium.readthedocs.io/en/latest/antimony.html#uncertainty-information
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num, \
        f"Uncertainty information was not supported before, and should have {len(issues)} issues. Actual {issue_num} issues."
    assert issues[issue_index].range.start == SrcPosition(1, 2), \
        f"Uncertainty information was not supported before, specifically, the dot in {code} should throw an UnexpectedTokenIssue."
        

@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    # clearing assignments
    ('a = ;', (1, 5, 1, 6), UnexpectedTokenIssue, 1, 0),
    ('a = ', (1, 3, 1, 4), UnexpectedEOFIssue, 1, 0),
])
def test_clear_assignment(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    Sometimes it is necessary to clear assignments and rules to a variable.
    To accomplish this, simply declare a new assignment or rule for the variable, but leave it blank.
    Clear assignment is not yet supported, so it will throw an UnexpectedTokenIssue 
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num, \
        f"Clear assignment was not supported before, and should have {len(issues)} issues. Actual {issue_num} issues."

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3])), \
        f"Expected issue at line {range_[0]} char {range_[1]} to line {range_[2]} char {range_[3]}.\
            Actual issue at line {issues[issue_index].range.start.line} char {issues[issue_index].range.start.column}\
            to {issues[issue_index].range.end.line} char {issues[issue_index].range.end.column} issues."
    assert isinstance(issues[issue_index], type_), \
        f"Expected issue type {issues[issue_index]}. Actual issue type {type_}."
        
        
@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    # rate rule
    ('P1\' = X;', (1, 3, 1, 4), UnexpectedTokenIssue, 3, 0),
    ('P1\' = X;', (1, 5, 1, 6), UnexpectedTokenIssue, 3, 1),
    ('P1\' = X;', (1, 8, 1, 9), UnexpectedTokenIssue, 3, 2),\
    # missing semicolon
    ('P1\' = X', (1, 7, 1, 8), UnexpectedEOFIssue, 3, 2),
])
def test_rate_rule(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    Waiting for merging raterules.
    Rate rules define the change in a symbol's value over time instead of defining its new value.
    These may be modeled in Antimony by appending an apostrophe to the name of the symbol, and using an equals sign to define the rate
    https://github.com/sys-bio/vscode-antimony/issues/45
    https://tellurium.readthedocs.io/en/latest/antimony.html?highlight=clearing#rate-rules
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num, \
        f"Rate rules was not supported before, and should have {len(issues)} issues. Actual {issue_num} issues."

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3])), \
        f"Expected to throw an issue at the apostrophe. Expected issue at line {range_[0]} char {range_[1]}\
            to line {range_[2]} char {range_[3]}. Actual issue at line {issues[issue_index].range.start.line} char {issues[issue_index].range.start.column}\
            to {issues[issue_index].range.end.line} char {issues[issue_index].range.end.column} issues."
    assert isinstance(issues[issue_index], type_), \
        f"The apstrophe should not be recognized. Expected issue type {issues[issue_index]}. Actual issue type {type_}."
        
        
@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    # SBO and cvterms
    ('a hasTaxon "BQB_thing"', (1, 12, 1, 23), UnexpectedTokenIssue, 1, 0), # why hasXXXX is treated differently?
    ('A hasVersion "cvterm"', (1, 14, 1, 22), UnexpectedTokenIssue, 1, 0), # see line 39 in antimony.lark
    ('A biological_entity_is "cvterm"', (1, 3, 1, 23), UnexpectedTokenIssue, 2, 0), # why this has two issues but line 44 has one?
    ('A biological_entity_is "cvterm"', (1, 24, 1, 32), UnexpectedTokenIssue, 2, 1),
    ('A part "cvterm"', (1, 3, 1, 7), UnexpectedTokenIssue, 2, 0),
    ('A part "cvterm"', (1, 8, 1, 16), UnexpectedTokenIssue, 2, 1),
    ('A isPropertyOf "cvterm"', (1, 5, 1, 15), UnexpectedTokenIssue, 2, 0), # isXXXX is not treated differently
    ('A.sboTerm = SBO:00000236', (1, 2, 1, 3), UnexpectedTokenIssue, 3, 0),
    ('A.sboTerm = SBO:00000236', (1, 16, 1, 17), UnexpectedTokenIssue, 3, 1),
    ('A.sboTerm = SBO:00000236', (1, 17, 1, 25), UnexpectedEOFIssue, 3, 2),
])
def test_sbo_cvterms(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    SBO and cvterms not supported
    Antimony model elements may also be annotated with their SBO terms and cvterms.
    https://github.com/sys-bio/vscode-antimony/issues/64
    https://tellurium.readthedocs.io/en/latest/antimony.html?highlight=clearing#sbo-and-cvterms
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num, \
        f"SBO and cvterms was not supported before, and should have {len(issues)} issues. Actual {issue_num} issues."

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3])), \
        f"Expected issue at line {range_[0]} char {range_[1]} to line {range_[2]} char {range_[3]}.\
            Actual issue at line {issues[issue_index].range.start.line} char {issues[issue_index].range.start.column}\
            to {issues[issue_index].range.end.line} char {issues[issue_index].range.end.column} issues."
    assert isinstance(issues[issue_index], type_), \
        f"The second or third word should not be recognized. Expected issue type {issues[issue_index]}. Actual issue type {type_}."
    
    
@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    # events at: variable1=formula1, variable2=formula2 [etc];
    # https://tellurium.readthedocs.io/en/latest/antimony.html#events
    ('E1: at (Y1 > 3): Z1=0, Q1=0;', (1, 12, 1, 13), UnexpectedTokenIssue, 4, 0),
    ('E1: at (Y1 > 3): Z1=0, Q1=0;', (1, 15, 1, 16), UnexpectedTokenIssue, 4, 1),
    ('E1: at (Y1 > 3): Z1=0, Q1=0;', (1, 16, 1, 17), UnexpectedTokenIssue, 4, 2),
    ('E1: at (Y1 > 3): Z1=0, Q1=0;', (1, 22, 1, 23), UnexpectedTokenIssue, 4, 3),
    ('at (x>5): y=3, x=r+2;', (1, 14, 1, 15), UnexpectedTokenIssue, 4, 3),
    ('E1: at 2 after (x>5): y=3, x=r+2;', (1, 8, 1, 9), UnexpectedTokenIssue, 5, 0), # 'after' is unexpected token
])
def test_events(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    Events are discontinuities in model simulations that change the definitions of
    one or more symbols at the moment when certain conditions apply.
    Event is not supported yet.
    https://github.com/sys-bio/vscode-antimony/issues/4
    https://tellurium.readthedocs.io/en/latest/antimony.html?highlight=clearing#events
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num, \
        f"Events was not supported, and should have {len(issues)} issues. Actual {issue_num} issues."

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3])), \
        f"Expected issue at line {range_[0]} char {range_[1]} to line {range_[2]} char {range_[3]}.\
            Actual issue at line {issues[issue_index].range.start.line} char {issues[issue_index].range.start.column}\
            to {issues[issue_index].range.end.line} char {issues[issue_index].range.end.column} issues."
    assert isinstance(issues[issue_index], type_), \
        f"Expected issue type {issues[issue_index]}. Actual issue type {type_}."
    
    
@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    # alternative boundary species declaration
    ('S1 + $E -> ES;', (1, 14, 1, 15), UnexpectedEOFIssue, 1, 0),
    ('$S1 ->  S2', (1, 9, 1, 11), UnexpectedEOFIssue, 1, 0), # this means that boundary species feature is not fully supported
])
def test_boundary_species(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    Boundary species are those species which are unaffected by the model.
    https://github.com/sys-bio/vscode-antimony/issues/63
    https://tellurium.readthedocs.io/en/latest/antimony.html#boundary-species
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num, \
        f"One of the two ways for declaring was not supported, and should have {len(issues)} issues. Actual {issue_num} issues."

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3])), \
        f"Expected issue at line {range_[0]} char {range_[1]} to line {range_[2]} char {range_[3]}.\
            Actual issue at line {issues[issue_index].range.start.line} char {issues[issue_index].range.start.column}\
            to {issues[issue_index].range.end.line} char {issues[issue_index].range.end.column} issues."
    assert isinstance(issues[issue_index], type_), \
        f"Expected issue type {issues[issue_index]}. Actual issue type {type_}."
    
    
@pytest.mark.parametrize('range_,type_,issue_index', [
    # alternative boundary species declaration
    ((1, 18, 2, 1), UnexpectedNewlineIssue, 0),
    ((2, 40, 2, 41), UnexpectedTokenIssue, 1), # - in -| is not recognized
    ((2, 41, 2, 42), UnexpectedTokenIssue, 2), # | in -| is not recognized
    ((2, 45, 2, 46), UnexpectedTokenIssue, 3), # ; in second line is not recognized
    ((3, 40, 3, 41), UnexpectedTokenIssue, 4), # - in -o is not recognized
    ((3, 43, 3, 45), UnexpectedTokenIssue, 5), # J0 in third line is not recognized, 
    ((4, 40, 4, 41), UnexpectedTokenIssue, 6), # - in -( is not recognized
    ((4, 41, 4, 42), UnexpectedTokenIssue, 7), # ( in -( is not recognized
    ((4, 45, 4, 46), UnexpectedTokenIssue, 8), # ; in fourth line is not recognized
])
def test_interactions(range_: Tuple[int, int, int, int], type_, issue_index, issue_num=9,\
                      code = '''J0: S1 + E -> SE;
                                i1: S2 -| J0;
                                i2: S3 -o J0;
                                i3: S4 -( J0;''',):
    '''
    Boundary species are those species which are unaffected by the model.
    https://github.com/sys-bio/vscode-antimony/issues/63
    https://tellurium.readthedocs.io/en/latest/antimony.html#boundary-species
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num,\
        f"Currently, there should be 9 issues because interaction is not supported, but received {len(issues)} issues."
    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3])),\
        f"The {issue_index}th(or st/nd/rd) issue should be at line {range_[0]} char {range_[1]} to line {range_[2]} char {range_[3]}.\
            Actual issue at line {issues[issue_index].range.start.line} char {issues[issue_index].range.start.column}\
            to {issues[issue_index].range.end.line} char {issues[issue_index].range.end.column} issues."
    assert isinstance(issues[issue_index], type_),\
        f"The {issue_index}th(or st/nd/rd) issue should be {issues[issue_index]}. Actual issue type {type_}."
    
    
@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    ('a=%', (1, 3, 1, 4), UnexpectedTokenIssue, 1, 0),
    ('a eee', (1, 3, 1, 6), UnexpectedTokenIssue, 1, 0),
    ('A.S1 is x', (1, 2, 1, 3), UnexpectedTokenIssue, 2, 0),
    ('A.S1 is x', (1, 9, 1, 10), UnexpectedTokenIssue, 2, 1),
    # delete
    ('delete A', (1, 8, 1, 9), UnexpectedTokenIssue, 1, 0),
    # exp()
    ('exp(-x);', (1, 5, 1, 6), UnexpectedTokenIssue, 2, 0),
    # maximize
    ('maximize J1', (1, 10, 1, 12), UnexpectedTokenIssue, 1, 0),
    # import https://tellurium.readthedocs.io/en/latest/antimony.html#other-files
    ('import "models1.txt"', (1, 8, 1, 21), UnexpectedTokenIssue, 1, 0),
])
def test_misc(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    test miscellaneous
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num, \
        f"Expected {len(issues)} issues. Actual {issue_num} issues."

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3])), \
        f"Expected issue at line {range_[0]} char {range_[1]} to line {range_[2]} char {range_[3]}.\
            Actual issue at line {issues[issue_index].range.start.line} char {issues[issue_index].range.start.column}\
            to {issues[issue_index].range.end.line} char {issues[issue_index].range.end.column} issues."
    assert isinstance(issues[issue_index], type_), \
        f"Expected issue type {issues[issue_index]}. Actual issue type {type_}."