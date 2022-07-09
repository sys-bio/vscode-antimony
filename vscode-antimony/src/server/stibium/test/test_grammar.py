from typing import Tuple
from stibium.api import AntFile
from stibium.types import IncompatibleType, ObscuredValue, SrcPosition, SrcRange, UnexpectedEOFIssue, UnexpectedNewlineIssue, UnexpectedTokenIssue

import pytest

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