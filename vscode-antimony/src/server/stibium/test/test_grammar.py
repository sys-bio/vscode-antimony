from typing import Tuple
from stibium.api import AntFile
from stibium.types import IncompatibleType, ObscuredValue, SrcPosition, SrcRange, UnexpectedEOFIssue, UnexpectedNewlineIssue, UnexpectedTokenIssue

import pytest

# the following test data are from Lucian Smith, https://github.com/sys-bio/antimony/tree/develop/src/test/test-data
@pytest.mark.parametrize('code', [
    ('unit voltage = 1e3 gram * metre^2 / (second^3 * ampere);'), #compound units
    ('a=-(x+2)'),  # negative parenthesis
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
    ('a=', (1, 2, 1, 3), UnexpectedEOFIssue, 1, 0),
    ('ae= \n', (1, 5, 2, 1), UnexpectedNewlineIssue, 1, 0),
    ('a=%', (1, 3, 1, 4), UnexpectedTokenIssue, 1, 0),
    ('a eee', (1, 3, 1, 6), UnexpectedTokenIssue, 1, 0),
    ('A.S1 is x', (1, 2, 1, 3), UnexpectedTokenIssue, 2, 0)
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
])
def test_unexpected_e_of_issue(code, range_: Tuple[int, int, int, int], type_, issue_num, issue_index):
    '''
    test UnexpectedEOFIssue, no issue at this moment
    '''
    antfile = AntFile('', code)
    issues = antfile.get_issues()
    assert len(issues) == issue_num

    assert issues[issue_index].range == SrcRange(SrcPosition(range_[0], range_[1]),
                                       SrcPosition(range_[2], range_[3]))
    assert isinstance(issues[issue_index], type_)