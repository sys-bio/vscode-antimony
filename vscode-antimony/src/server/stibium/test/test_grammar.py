from typing import Tuple
from stibium.api import AntFile
from stibium.types import IncompatibleType, ObscuredValue, SrcPosition, SrcRange, UnexpectedEOFIssue, UnexpectedNewlineIssue, UnexpectedTokenIssue

import pytest

# the following test data are from Lucian Smith, https://github.com/sys-bio/antimony/tree/develop/src/test/test-data
@pytest.mark.parametrize('code', [
    # constant supported
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


@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    ('a=%', (1, 3, 1, 4), UnexpectedTokenIssue, 1, 0),
    ('a eee', (1, 3, 1, 6), UnexpectedTokenIssue, 1, 0),
    ('A.S1 is x', (1, 2, 1, 3), UnexpectedTokenIssue, 2, 0),
    ('A.S1 is x', (1, 9, 1, 10), UnexpectedTokenIssue, 2, 1),
    # uncertainty information
    # https://tellurium.readthedocs.io/en/latest/antimony.html#uncertainty-information
    ('a.confidenceInterval = {0, 25}', (1, 2, 1, 3), UnexpectedTokenIssue, 4, 0),
    ('a.variance = 25', (1, 2, 1, 3), UnexpectedTokenIssue, 1, 0),
    # clearing assignments
    ('a = ;', (1, 5, 1, 6), UnexpectedTokenIssue, 1, 0),
    # rate rule
    ('P1\' = X;', (1, 3, 1, 4), UnexpectedTokenIssue, 3, 0),
    ('P1\' = X;', (1, 5, 1, 6), UnexpectedTokenIssue, 3, 1),
    ('P1\' = X;', (1, 8, 1, 9), UnexpectedTokenIssue, 3, 2),
    # SBO and CVTerms
    ('a hasTaxon "BQB_thing"', (1, 12, 1, 23), UnexpectedTokenIssue, 1, 0), # why hasXXXX is treated differently?
    ('A hasVersion "cvterm"', (1, 14, 1, 22), UnexpectedTokenIssue, 1, 0), # see line 39 in antimony.lark
    ('A biological_entity_is "cvterm"', (1, 3, 1, 23), UnexpectedTokenIssue, 2, 0), # why this has two issues but line 44 has one?
    ('A biological_entity_is "cvterm"', (1, 24, 1, 32), UnexpectedTokenIssue, 2, 1),
    ('A part "cvterm"', (1, 3, 1, 7), UnexpectedTokenIssue, 2, 0),
    ('A part "cvterm"', (1, 8, 1, 16), UnexpectedTokenIssue, 2, 1),
    ('A isPropertyOf "cvterm"', (1, 5, 1, 15), UnexpectedTokenIssue, 2, 0), # isXXXX is not treated differently
    # events at: variable1=formula1, variable2=formula2 [etc];
    # https://tellurium.readthedocs.io/en/latest/antimony.html#events
    ('E1: at (Y1 > 3): Z1=0, Q1=0;', (1, 12, 1, 13), UnexpectedTokenIssue, 4, 0),
    ('E1: at (Y1 > 3): Z1=0, Q1=0;', (1, 15, 1, 16), UnexpectedTokenIssue, 4, 1),
    ('E1: at (Y1 > 3): Z1=0, Q1=0;', (1, 16, 1, 17), UnexpectedTokenIssue, 4, 2),
    ('E1: at (Y1 > 3): Z1=0, Q1=0;', (1, 22, 1, 23), UnexpectedTokenIssue, 4, 3),
    ('at (x>5): y=3, x=r+2;', (1, 14, 1, 15), UnexpectedTokenIssue, 4, 3),
    ('E1: at 2 after (x>5): y=3, x=r+2;', (1, 8, 1, 9), UnexpectedTokenIssue, 5, 0), # 'after'
    # delete
    ('delete A', (1, 8, 1, 9), UnexpectedTokenIssue, 1, 0),
    # exp()
    ('exp(-x);', (1, 5, 1, 6), UnexpectedTokenIssue, 2, 0),
    # maximize
    ('maximize J1', (1, 10, 1, 12), UnexpectedTokenIssue, 1, 0),
])
def test_unexpected_token(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    test unexpected token issue
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3]))
    assert isinstance(issues[issue_index], type_)
    
@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    ('ae= \n', (1, 5, 2, 1), UnexpectedNewlineIssue, 1, 0),
    ('J0: A->;\nJ0.sboTerm = 888', (1, 9, 2, 1), UnexpectedNewlineIssue, 2, 0)
])
def test_unexpected_new_line(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    test unexpected new line issue
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3]))
    assert isinstance(issues[issue_index], type_)
    
    
@pytest.mark.parametrize('code,range_,type_,issue_num,issue_index', [
    ('a = ', (1, 3, 1, 4), UnexpectedEOFIssue, 1, 0),
    ('P1\' = X', (1, 7, 1, 8), UnexpectedEOFIssue, 3, 2),
    # alternative boundary species declaration
    ('S1 + $E -> ES;', (1, 14, 1, 15), UnexpectedEOFIssue, 1, 0),
])
def test_unexpected_e_of_issue(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    test UnexpectedEOFIssue, check incomplete syntax
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3]))
    assert isinstance(issues[issue_index], type_)