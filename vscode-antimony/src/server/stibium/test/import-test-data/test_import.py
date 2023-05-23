import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)

from stibium.ant_types import Import, Name
from stibium.types import SrcPosition, SrcRange, SymbolType
from stibium.symbols import BaseScope, QName
from stibium.api import AntFile
from stibium.parse import AntimonyParser

from pygls.workspace import Document

import pytest

parser = AntimonyParser()
directory = os.path.join(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("file_name, parse_tree_str", [
    ("base", "Tree('root', [Tree('simple_stmt', [Tree('import', [Token('IMPORT', 'import'), Token('ESCAPED_STRING', '\"import.ant\"')]), Token('NEWLINE', '\\n\\n')]), Tree('simple_stmt', [Tree('assignment', [Tree('namemaybein', [Tree('var_name', [None, Token('NAME', 'test')]), None]), Token('EQUAL', '='), Token('NUMBER', '4')]), Token('NEWLINE', '')])])"),
])
def test_import(file_name, parse_tree_str):
    file = os.path.join(directory, file_name + ".ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"
    actual_str = parser.get_parse_tree_str(ant_file.text)
    assert parse_tree_str == actual_str, "Incorrect contents imported"


@pytest.mark.parametrize("assign_vals", [
    (["10", "4", "4 mass"]),
])
def test_assign(assign_vals):
    file = os.path.join(directory, "assign.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"

    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test first assignment within base file
    assignment = ant_file.analyzer.table.get(QName(BaseScope(), Name(range=SrcRange(SrcPosition(3, 5), SrcPosition(3, 6)), text='a')))[0].value_node
    cur_val = assignment.get_value().text
    assert assign_vals[0] == cur_val, "Incorrect assignment"

    # Test second assignment from imported file
    assignment = ant_file.analyzer.table.get(QName(BaseScope(), Name(range=SrcRange(SrcPosition(3, 9), SrcPosition(3, 10)), text='b')))[0].value_node
    cur_val = assignment.get_value().text
    assert assign_vals[1] == cur_val, "Incorrect assignment"

    # Test third assignmetn from imported file with unit in base file
    assignment = ant_file.analyzer.table.get(QName(BaseScope(), Name(range=SrcRange(SrcPosition(3, 9), SrcPosition(3, 10)), text='b')))[0].value_node
    cur_val = assignment.get_value().text
    cur_val +=  " " + assignment.get_type().get_name_text()
    assert assign_vals[2] == cur_val, "Incorrect assignment"


@pytest.mark.parametrize("assign_vals", [
    (["\"in base file\"", "\"not imported\""]),
])
def test_is_assign(assign_vals):
    file = os.path.join(directory, "assign.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"

    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test first assignment within base file
    assignment = ant_file.analyzer.table.get(QName(BaseScope(), Name(range=SrcRange(SrcPosition(3, 9), SrcPosition(3, 10)), text='b')))[0].display_name
    assert assign_vals[1] == assignment, "Incorrect display name"

    # Test second assignment from imported file
    assignment = ant_file.analyzer.table.get(QName(BaseScope(), Name(range=SrcRange(SrcPosition(4, 1), SrcPosition(4, 2)), text='a')))[0].display_name
    assert assign_vals[0] == assignment, "Incorrect display name"


@pytest.mark.parametrize("assign_vals", [
    (["vol", "mass"])
])
def test_unit_assign(assign_vals):
    file = os.path.join(directory, "assign.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"

    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test first assignment within base file
    assignment = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(3, 9), SrcPosition(3, 10)), text='b')))[0].value_node.unit.get_name().text
    assert assign_vals[1] == assignment, "Incorrect unit"

    # Test second assignment from imported file
    assignment = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(4, 1), SrcPosition(4, 2)), text='a')))[0].value_node.unit.get_name().text
    assert assign_vals[0] == assignment, "Incorrect unit"


@pytest.mark.parametrize("reaction_vals", [
    (["a", "b", "kfc"])
])
def test_reaction(reaction_vals):
    file = os.path.join(directory, "reaction.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"

    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test first reaction within base file
    reaction = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(6, 1), SrcPosition(6, 3)), text='J4')))[0].decl_node
    reactants = reaction.get_reactants()
    products = reaction.get_products()
    constants = reaction.get_rate_law()
    assert reaction_vals[0] == reactants[0].get_name_text(), "Incorrect species"
    assert reaction_vals[1] == reactants[1].get_name_text(), "Incorrect species"
    assert reaction_vals[1] == products[0].get_name_text(), "Incorrect species"
    assert reaction_vals[2] == constants.get_name_text(), "Incorrect constant"

    # Test second reaction from imported file
    reaction = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(7, 1), SrcPosition(7, 3)), text='J0')))[0].decl_node
    reactants = reaction.get_reactants()
    products = reaction.get_products()
    constants = reaction.get_rate_law()
    assert reaction_vals[0] == reactants[0].get_name_text(), "Incorrect species"
    assert reaction_vals[1] == products[0].get_name_text(), "Incorrect species"
    assert reaction_vals[2] == constants.get_name_text(), "Incorrect constant"


def test_mmodel_call():
    file = os.path.join(directory, "mmodel_calls.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 1, "Import unsuccessful"

    # Test for duplicate mmodel call
    error_msg = "The modular model call 'MC' has been duplicated, please make sure there is only one modular model call of this name"
    assert error_msg == issues[0].message, "Incorrect error encountered"

    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test imported mmodel call
    call = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(11, 1), SrcPosition(11, 4)), text='MC2')))[0].value_node
    assert call.get_mmodel_name_str() == "foo"


def test_func_call():
    file = os.path.join(directory, "func_calls.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"

    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test first function call within base file
    call = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(8, 1), SrcPosition(8, 3)), text='FC')))[0].value_node
    assert call.get_value().get_function_name().get_name_text() == "constant"

    # Test second function call from imported file
    call = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(9, 1), SrcPosition(9, 4)), text='FC2')))[0].value_node
    assert call.get_value().get_function_name().get_name_text() == "varsum"

    # Test function call for function in imported file and call in base file
    call = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(10, 1), SrcPosition(10, 4)), text='FC3')))[0].value_node
    assert call.get_value().get_function_name().get_name_text() == "varsum"


def test_annot():
    file = os.path.join(directory, "annot.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"

    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test number of annotations for variable in current and imported files
    annot_list = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(4, 1), SrcPosition(4, 2)), text='b')))[0].annotations
    assert len(annot_list) == 2, "Incorrect annotations"

    # Test number of annotations for variable in current file
    annot_list = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(3, 1), SrcPosition(3, 2)), text='a')))[0].annotations
    assert len(annot_list) == 1, "Incorrect annotations"


def test_dupe_mmodel():
    file = os.path.join(directory, "mmodel.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 1, "Import unsuccessful"

    # Test for duplicate mmodel
    error_msg = "Model 'foo' is already defined, or there is a circular import"
    assert error_msg == issues[0].message, "Incorrect error encountered"


def test_dupe_func():
    file = os.path.join(directory, "func.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 1, "Import unsuccessful"

    # Test for duplicate function
    error_msg = "Function 'varsum' is already defined"
    assert error_msg == issues[0].message, "Incorrect error encountered"


def test_imp_hierarchy():
    file = os.path.join(directory, "multi_import.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"

    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)
    stmt = ant_file.tree.children[1].get_stmt()
    assert isinstance(stmt, Import)

    # Testing import hierarchy by checking for values of variables from either the base file or the latest import that has the variable
    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(4, 1), SrcPosition(4, 2)), text='c')))[0]
    value = var.value_node.get_value().text
    assert value == "6", "Incorrect value"

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(5, 1), SrcPosition(5, 2)), text='d')))[0]
    value = var.value_node.get_value().text
    assert value == "10", "Incorrect value"

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(10, 1), SrcPosition(10, 2)), text='a')))[0]
    value = var.value_node.get_value().text
    assert value == "5", "Incorrect value"
    display_name = var.display_name
    assert display_name == "\"from the second file\"", "Incorrect display name"

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(27, 1), SrcPosition(27, 2)), text='b')))[0]
    annot_list = var.annotations
    assert len(annot_list) == 1, "Incorrect annotations"

    # Testing imported mmodel call
    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(22, 1), SrcPosition(22, 3)), text='T3')))[0]
    mmodel = var.value_node.get_mmodel_name_str()
    assert mmodel == "test3", "Incorrect mmodel call"


def test_decl():
    file = os.path.join(directory, "decl.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"
    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Testing different components of declarations from imported file
    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(14, 1), SrcPosition(14, 5)), text='decl')))[0]
    assert var.value_node.get_value().text == "3"
    assert var.type == SymbolType.Compartment
    assert var.is_const
    assert not var.is_sub
    assert var.display_name is None

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(10, 1), SrcPosition(10, 3)), text='A1')))[0]
    assert var.value_node.get_value().text == "2"
    assert var.type == SymbolType.Species
    assert var.comp == "decl"
    assert var.is_const
    assert not var.is_sub
    assert var.display_name is None

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(11, 1), SrcPosition(11, 3)), text='A2')))[0]
    assert var.value_node.get_value().text == "4"
    assert var.type == SymbolType.Species
    assert var.comp == "decl"
    assert var.is_const
    assert not var.is_sub
    assert var.display_name is None

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(13, 1), SrcPosition(13, 3)), text='S1')))[0]
    assert var.value_node.get_value().text == "7"
    assert var.type == SymbolType.Species
    assert var.comp == "decl"
    assert not var.is_const
    assert var.is_sub
    assert var.display_name == "\"a species\""

    # Testing different components of declarations from base file
    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(3, 9), SrcPosition(3, 11)), text='A3')))[0]
    assert var.value_node.get_value().text == "6"
    assert var.type == SymbolType.Species
    assert var.comp == "decl"
    assert not var.is_const
    assert not var.is_sub
    assert var.display_name is None


def test_var_in():
    file = os.path.join(directory, "var_in.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"
    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Testing variable in compartments from imported and base files
    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(34, 1), SrcPosition(34, 2)), text='f')))[0]
    assert var.comp == "test"

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(3, 1), SrcPosition(3, 2)), text='g')))[0]
    assert var.comp == "test"


def test_failed_import():
    file = os.path.join(directory, "bad.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 1, "Import unsuccessful"

    # Test for import file error message
    error_msg = "The grammar contains issues, please fix before importing\n"
    error_msg += "File not found\n"
    error_msg += "Function 'failed_func' not defined\n"
    assert error_msg == issues[0].message, "Incorrect error encountered"


def test_sboterm():
    file = os.path.join(directory, "sboterm.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"
    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test sboterms for imported assignments
    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(3, 1), SrcPosition(3, 3)), text='S1')))[0]
    assert var.sboterms[0].get_val() == "15"

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(4, 1), SrcPosition(4, 3)), text='S2')))[0]
    assert var.sboterms[0].get_val() == "12"

def test_rate_rule():
    file = os.path.join(directory, "rate_rule.ant")
    doc = Document(os.path.abspath(file))
    ant_file = AntFile(doc.path, doc.source)
    issues = ant_file.get_issues()
    error_count = 0
    for issue in issues:
        if str(issue.severity.__str__()) == "IssueSeverity.Error":
            error_count += 1
    assert error_count == 0, "Import unsuccessful"
    assert len(issues) == 1, "Incorrect issue count"
    stmt = ant_file.tree.children[0].get_stmt()
    assert isinstance(stmt, Import)

    # Test imported rate rule and base file rate rule
    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(1, 1), SrcPosition(1, 3)), text='S1')))[0]
    assert var.rate_rule == "kfc * S2"

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(3, 1), SrcPosition(3, 3)), text='S2')))[0]
    assert var.rate_rule == "kfc - (S1 * S2)"

    var = ant_file.analyzer.table.get(QName(BaseScope(), name=Name(range=SrcRange(SrcPosition(2, 1), SrcPosition(2, 3)), text='S3')))[0]
    assert var.rate_rule == "(S1 - S3) * k1"