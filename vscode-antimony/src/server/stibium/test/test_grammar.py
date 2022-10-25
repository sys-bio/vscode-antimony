import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from stibium.api import AntFile
from stibium.parse import AntimonyParser

from pygls.workspace import Document

import pytest

import json


parser = AntimonyParser()
directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-data")

f = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parsed_test_data.json'))
parsed_data = json.load(f)

# some of the following test data are from Lucian Smith, https://github.com/sys-bio/antimony/tree/develop/src/test/test-data

    

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
    assert len(antfile.get_issues()) == 0,\
        f"this test has no dependencies"
    tree = parser.get_parse_tree_str(code)
    assert str(tree) == expected_parse_tree_str,\
        f"this test has no dependencies"
        
        
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('reaction001', parsed_data['reaction001']),
    ('reactionIn',parsed_data['reactionIn']),
    ('reactionIn_rt',parsed_data['reactionIn_rt']),
    ('reaction',parsed_data['reaction']),
    ('reaction_rt', parsed_data['reaction_rt']),
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
    assert error_count == 0,\
        f"this test has no dependencies"
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
        f"this test has no dependencies"
        
        
@pytest.mark.parametrize('code,file_name,expected_parse_tree_str', [
    ('a = ;','',"Tree('root', [])"),
    ('','initialAmount',parsed_data['initialAmount']),
    ('','initialAmount_rt',parsed_data['initialAmount_rt']),
    ('','initialAssignment',parsed_data['initialAssignment']),
    ('','initialAssignment_rt',parsed_data['initialAssignment_rt']),
    ('','initialConcentration',parsed_data['initialConcentration']),
    ('','initialConcentration_rt',parsed_data['initialConcentration_rt']),
    ('','initialValue',parsed_data['initialValue']),
    ('','initialValue_rt',parsed_data['initialValue_rt']),
    ('','parameter',parsed_data['parameter']),
    ('','parameter_rt',parsed_data['parameter_rt']),
    ('','parameter_inf',parsed_data['parameter_inf']),
    ('','parameter_inf_rt',parsed_data['parameter_inf_rt']),
    ('','parameter_nan',parsed_data['parameter_nan']),
    ('','parameter_nan_rt',parsed_data['parameter_nan_rt']),
    ('','parameter_neginf',parsed_data['parameter_neginf']),
    ('','parameter_neginf_rt',parsed_data['parameter_neginf_rt']),
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
    ('species',parsed_data['species']),
    ('species_rt',parsed_data['species_rt']),
    ('compartment_rt',parsed_data['compartment_rt']),
])
def test_defining_species_compartments(file_name, expected_parse_tree_str):
    f = os.path.join(directory, file_name + '.ant')
    doc = Document(os.path.abspath(f))
    ant_file = AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    assert error_count == 0,\
        f"this test has no dependencies"
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
        f"this test has no dependencies"
            

@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('default_compartment',parsed_data['default_compartment']),
    ('defaultOrNotCompartment_rt',parsed_data['defaultOrNotCompartment_rt']),
    ('defaultOrNotCompartment',parsed_data['defaultOrNotCompartment']),
    ('defaultSubCompartment',parsed_data['defaultSubCompartment']),
    ('defaultSubCompartment_rt',parsed_data['defaultSubCompartment_rt']),
    ('defaultSubSubCompartment',parsed_data['defaultSubSubCompartment']),
    ('defaultSubSubCompartment_rt',parsed_data['defaultSubSubCompartment_rt']),
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
    assert error_count == 0,\
        f"this test has no dependencies"
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f"this test has no dependencies"

            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('BIOMD0000000118',""),
    ('function_name',parsed_data['function_name']),
    ('function_name_rt',parsed_data['function_name_rt']),
    ('SBO_function', parsed_data['SBO_function']),
    ('SBO_function_rt', parsed_data['SBO_function_rt']),
    
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
    assert error_count == 0,\
        f"this test has no dependencies"
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
        f"this test has no dependencies"
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('identity',parsed_data['identity']),
    ('identity_rt',parsed_data['identity_rt']),
    ('hasPart',parsed_data['hasPart']),
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
    assert error_count == 0,\
    f"this test has no dependencies"
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
        f"this test has no dependencies"

    

@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('BIOMD0000000696',parsed_data['BIOMD0000000696']),
    ('hierarchy',parsed_data['hierarchy']),
    ('hierarchy_rt',parsed_data['hierarchy_rt']),
    ('module_name',parsed_data['module_name']),
    ('module_name_rt',parsed_data['module_name_rt']),
    ('port',parsed_data['port']),
    ('port_rt',parsed_data['port_rt']),
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
    ('substance_only_species',parsed_data['substance_only_species']),
    ('substance_only_species_rt',parsed_data['substance_only_species_rt']),
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
    ('assignmentRule',parsed_data['assignmentRule']),
    ('assignmentRule_rt',parsed_data['assignmentRule_rt']),
    # these four test cases are dependent many other tests
    #('deleteAssignmentRuleDirect',parsed_data['deleteAssignmentRuleDirect']),
    #('deleteAssignmentRuleDirect_rt',parsed_data['deleteAssignmentRuleDirect_rt']),
    #('deleteAssignmentRuleIndirect',parsed_data['deleteAssignmentRuleIndirect']),
    #('deleteAssignmentRuleIndirect_rt', parsed_data['deleteAssignmentRuleIndirect_rt']),
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
    ('names',parsed_data['names']),
    ('names_rt',parsed_data['names_rt']),
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
    ('compound_units1',parsed_data['compound_units1']),
    ('compound_units1_rt',parsed_data['compound_units1_rt']),
    ('compound_units2',parsed_data['compound_units2']),
    ('compound_units2_rt',parsed_data['compound_units2_rt']),
    ('compound_units3',parsed_data['compound_units3']),
    ('compound_units3_rt',parsed_data['compound_units3_rt']),
    ('compound_units4',parsed_data['compound_units4']),
    ('compound_units4_rt',parsed_data['compound_units4_rt']),
    ('global_units',parsed_data['global_units']),
    ('global_units_rt',parsed_data['global_units_rt']),
    ('same_unit_name',parsed_data['same_unit_name']),
    ('units',parsed_data['units']),
    ('units_rt',parsed_data['units_rt']),
    
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
    ('negparen',parsed_data['negparen']),
    ('negparen_rt',parsed_data['negparen_rt']),
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
    assert error_count == 0,\
        f"This test is independent."
    if error_count == 0:
        actual_str = parser.get_parse_tree_str(ant_file.text)
        assert expected_parse_tree_str == actual_str,\
            f'''Logging actual {repr(actual_str)} \n'''
            
            
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    # ('replaceAssignmentRule',""),
    # ('replaceAssignmentRule_rt',""),
    # ('replaceCompartment',""),
    # ('replaceCompartment_rt',""),
    # ('replaceInitialAssignment',""),
    # ('replaceInitialAssignment_rt',""),
    # ('replaceParameter',""),
    # ('replaceParameter_rt',""),
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
    
    
@pytest.mark.parametrize('file_name,expected_parse_tree_str', [
    ('boolean_event_delays',''),
    ('boolean_triggers',''),
    ('event',parsed_data['event']),
    # ('event_rt',parsed_data['event_rt']),
    # ('eventDelay',parsed_data['eventDelay']),
    # ('eventDelay_rt',parsed_data['eventDelay_rt']),
    ('eventFromTrigger',parsed_data['eventFromTrigger']),
    # ('eventFromTrigger_rt',parsed_data['eventFromTrigger_rt']),
    ('eventPersistent',parsed_data['eventPersistent']),
    # ('eventPersistent_rt',parsed_data['eventPersistent_rt']),
    ('eventPriority',parsed_data['eventPriority']),
    # ('eventPriority_rt',parsed_data['eventPriority_rt']),
    ('eventT0',parsed_data['eventT0']),
    # ('eventT0_rt',parsed_data['eventT0_rt']),
])
# Note: these commented test cases fail because assignment is not complete, not event problem
def test_event(file_name, expected_parse_tree_str):
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
        # assert expected_parse_tree_str == actual_str,\
        #     f'''Logging actual {repr(actual_str)} \n'''