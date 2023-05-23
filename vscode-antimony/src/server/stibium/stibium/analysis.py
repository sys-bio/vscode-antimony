from collections import defaultdict
import logging
import os
import requests
from bioservices import ChEBI, UniProt, Rhea
from stibium.ant_types import Interaction, UnitAssignment, FuncCall, IsAssignment, VariableIn, NameMaybeIn, FunctionCall, ModularModelCall, Number, Operator, VarName, DeclItem, UnitDeclaration, Parameters, ModularModel, Function, SimpleStmtList, End, Keyword, Sbo, Annotation, Sboterm, ArithmeticExpr, Assignment, Declaration, ErrorNode, ErrorToken, FileNode, Function, InComp, LeafNode, Model, Name, RateRules, Reaction, Event, SimpleStmt, TreeNode, TrunkNode, Import, StringLiteral
from .types import FunctionAlreadyExists, CircularImportFound, DuplicateImportedMModelCall, FileAlreadyImported, GrammarHasIssues, ModelAlreadyExists, NoImportFile, ObscuredEventTrigger, ReservedName, UninitRateLaw, OverridingDisplayName, SubError, VarNotFound, SpeciesUndefined, IncorrectParamNum, ParamIncorrectType, UninitFunction, UninitMModel, UninitCompt, UnusedParameter, RefUndefined, ASTNode, Issue, SymbolType, SyntaxErrorIssue, UnexpectedEOFIssue, UnexpectedNewlineIssue, UnexpectedTokenIssue, Variability, SrcPosition, RateRuleOverRidden, RateRuleNotInReaction
from .symbols import FuncSymbol, AbstractScope, BaseScope, FunctionScope, MModelSymbol, ModelScope, QName, SymbolTable, ModularModelScope
import stibium.functions as functions

from dataclasses import dataclass
from typing import Any, List, Optional, Set, cast
from itertools import chain
from lark.lexer import Token
from lark.tree import Tree

SLASH = "/"
HTTP = "http"
RHEA_URL = "www.rhea-db.org"
IDENTIFIERS_ORG = "identifiers.org"
CHEBI_LOWER = "chebi"
EQUATION_LOWER = "equation"
EQUATION_CAP = "Equation"
UNDERSCORE = "_"
ONTOLOGIES_URL = "http://www.ebi.ac.uk/ols/api/ontologies/"
ONTOLOGIES_URL_SECOND_PART = "/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F"
vscode_logger = logging.getLogger("vscode-antimony logger")

def get_qname_at_position(root: FileNode, pos: SrcPosition) -> Optional[QName]:
    '''Returns (context, token) the given position. `token` may be None if not found.
    '''
    def within_range(pos: SrcPosition, node: TreeNode):
        return pos >= node.range.start and pos < node.range.end

    node: TreeNode = root
    model: Optional[Name] = None
    func: Optional[Name] = None
    mmodel: Optional[Name] = None
    
    while not isinstance(node, LeafNode):
        if isinstance(node, Model):
            assert model is None
            model = node.get_name()
        elif isinstance(node, Function):
            assert func is None
            func = node.get_name()
        elif isinstance(node, ModularModel):
            assert mmodel is None
            mmodel = node.get_name()

        for child in node.children:
            if child is None:
                continue

            if within_range(pos, child):
                node = child
                break
        else:
            # Didn't find it
            return None

    # can't have nested models/functions
    assert not (model is not None and func is not None)
    if model:
        scope = ModelScope(str(model))
    elif func:
        scope = FunctionScope(str(func))
    elif mmodel:
        scope = ModularModelScope(str(mmodel))
    else:
        scope = BaseScope()
    return QName(scope, node)


class AntTreeAnalyzer:
    def __init__(self, root: FileNode, path: str):
        self.table = SymbolTable()
        self.import_table = SymbolTable()
        self.root = root
        self.inserted = defaultdict(bool)
        self.inserted_decl = defaultdict(bool)
        self.unit_vals = defaultdict()
        self.unit_names = []
        self.pending_is_assignments = []
        self.pending_annotations = []
        self.pending_imports = []
        self.cur_file_name = os.path.basename(path)
        self.pending_interactions = []
        self.pending_sboterms = []
        # for dealing with rate rules not yet declared
        self.pending_rate_rules = []
        self.pending_sboterms = []
        self.pending_events = []
        self.unnamed_events_num = 0
        base_scope = BaseScope()
        self.reaction_item = set()
        for child in root.children:
            if isinstance(child, ErrorToken):
                continue
            if isinstance(child, ErrorNode):
                continue
            if isinstance(child, Model):
                scope = ModelScope(str(child.get_name()))
                for cchild in child.children:
                    if isinstance(cchild, ErrorToken):
                        continue
                    if isinstance(cchild, ErrorNode):
                        continue
                    if isinstance(cchild, SimpleStmtList):
                        for st in cchild.children:
                            if isinstance(st, ErrorToken):
                                continue
                            if isinstance(st, ErrorNode):
                                continue
                            stmt = st.get_stmt()
                            if stmt is None:
                                continue
                            {
                                'Reaction': self.handle_reaction,
                                'Event': self.pre_handle_event,
                                'Assignment': self.handle_assignment,
                                'Declaration': self.handle_declaration,
                                'Annotation': self.pre_handle_annotation,
                                'Sboterm': self.pre_handle_sboterm,
                                'UnitDeclaration': self.handle_unit_declaration,
                                'UnitAssignment' : self.handle_unit_assignment,
                                'ModularModelCall' : self.handle_mmodel_call,
                                'FunctionCall' : self.handle_function_call,
                                'VariableIn' : self.handle_variable_in,
                                'IsAssignment' : self.pre_handle_is_assignment,
                                'Interaction' : self.pre_handle_interaction,
                                'RateRules' : self.pre_handle_rate_rule,
                            }[stmt.__class__.__name__](scope, stmt, False)
                            self.handle_child_incomp(scope, stmt, False)
                            self.handle_is_const(scope, stmt, False)
            if isinstance(child, ModularModel):
                scope = ModularModelScope(str(child.get_name()))
                for cchild in child.children:
                    if isinstance(cchild, ErrorToken):
                        continue
                    if isinstance(cchild, ErrorNode):
                        continue
                    if isinstance(cchild, SimpleStmtList):
                        for st in cchild.children:
                            if isinstance(st, ErrorToken):
                                continue
                            if isinstance(st, ErrorNode):
                                continue
                            stmt = st.get_stmt()
                            if stmt is None:
                                continue
                            {
                                'Reaction': self.handle_reaction,
                                'Event': self.pre_handle_event,
                                'Assignment': self.handle_assignment,
                                'Declaration': self.handle_declaration,
                                'Annotation': self.pre_handle_annotation,
                                'Sboterm': self.pre_handle_sboterm,
                                'UnitDeclaration': self.handle_unit_declaration,
                                'UnitAssignment' : self.handle_unit_assignment,
                                'ModularModelCall' : self.handle_mmodel_call,
                                'FunctionCall' : self.handle_function_call,
                                'VariableIn' : self.handle_variable_in,
                                'IsAssignment' : self.pre_handle_is_assignment,
                                'Interaction' : self.pre_handle_interaction,
                                'RateRules' : self.pre_handle_rate_rule,
                            }[stmt.__class__.__name__](scope, stmt, False)
                            self.handle_child_incomp(scope, stmt, False)
                            self.handle_is_const(scope, stmt, False)
                    if isinstance(cchild, Parameters):
                        self.handle_parameters(scope, cchild, False)
                self.handle_mmodel(child, False)
            if isinstance(child, Function):
                scope = FunctionScope(str(child.get_name()))
                for cchild in child.children:
                    if isinstance(cchild, ErrorToken):
                        continue
                    if isinstance(cchild, ErrorNode):
                        continue
                    if isinstance(cchild, ArithmeticExpr):
                        self.handle_arith_expr(scope, cchild, False)
                    if isinstance(cchild, Parameters):
                        self.handle_parameters(scope, cchild, False)
                self.handle_function(child, False)
            if isinstance(child, SimpleStmt):
                if isinstance(child, ErrorToken):
                    continue
                if isinstance(child, ErrorNode):
                    continue
                stmt = child.get_stmt()
                if isinstance(stmt, Import):
                    self.pre_handle_import(base_scope, stmt)
                    continue
                if isinstance(stmt, UnitAssignment):
                    qname = QName(base_scope, stmt.get_var_name().get_name())
                    self.unit_vals[qname] = stmt.get_sum()
                    self.unit_names.append(qname)
                if stmt is None:
                    continue
                {
                    'Reaction': self.handle_reaction,
                    'Event': self.pre_handle_event,
                    'Assignment': self.handle_assignment,
                    'Declaration': self.handle_declaration,
                    'Annotation': self.pre_handle_annotation,
                    'Sboterm': self.pre_handle_sboterm,
                    'UnitDeclaration': self.handle_unit_declaration,
                    'UnitAssignment' : self.handle_unit_assignment,
                    'ModularModelCall' : self.handle_mmodel_call,
                    'FunctionCall' : self.handle_function_call,
                    'VariableIn' : self.handle_variable_in,
                    'IsAssignment' : self.pre_handle_is_assignment,
                    'Interaction' : self.pre_handle_interaction,
                    'RateRules' : self.pre_handle_rate_rule,
                }[stmt.__class__.__name__](base_scope, stmt, False)
                self.handle_child_incomp(base_scope, stmt, False)
                self.handle_is_const(base_scope, stmt, False)
        
        # get list of errors from the symbol table
        self.error = self.table.error
        # get list of warnings
        self.warning = self.table.warning
        self.handle_annotation_list()
        self.handle_sboterm_list()
        self.get_annotation_descriptions()
        self.handle_is_assignment_list()
        self.handle_import_list()
        self.handle_interactions()
        # handle all rate rules after appended to list and finished parsing
        self.handle_rate_rules()
        self.pending_is_assignments = []
        self.pending_imports = []
        self.check_parse_tree(self.root, BaseScope())

    def resolve_qname(self, qname: QName):
        return self.table.get(qname)
    
    def resolve_import_qname(self, qname: QName):
        return self.import_table.get(qname)

    def get_all_names(self) -> Set[str]:
        # TODO temporary method to satisfy auto-completion
        return self.table.get_all_names()

    def get_all_import_names(self) -> Set[str]:
        return self.import_table.get_all_names()

    def get_issues(self) -> List[Issue]:
        return (self.warning + self.error).copy()
    
    def replace_assign(self, given_qname: QName, stmt):
        self.table.remove(given_qname)
        if isinstance(stmt, UnitDeclaration):
            self.handle_unit_declaration(BaseScope(), stmt, False)
        if isinstance(stmt, Reaction):
            self.handle_reaction(BaseScope(), stmt, False)
        if isinstance(stmt, FunctionCall):
            self.handle_function_call(BaseScope(), stmt, False)
        if isinstance(stmt, Interaction):
            self.handle_interaction(BaseScope(), stmt, False)
        if isinstance(stmt, RateRules):
            self.handle_rate_rule(BaseScope(), stmt, False)

    def check_parse_tree(self, root, scope):
        # 1. check rate laws:
        #   1.1 referencing undefined parameters
        #   1.2 unused parameters in function/mmodel
        # 2. syntax issue when parsing the grammar
        #   Note: this could be due to partially implemented grammar at this moment
        # 3. referencing undefined compartment
        # 4. calling undefined function/modular model
        # 5. check parameters
        # 6. check "is" assignment
        for node in root.children:
            if node is None:
                continue
            elif type(node) == Model:
                self.check_parse_tree(node.get_stmt_list(), ModelScope(str(node.get_name())))
            elif type(node) == Function:
                self.check_parse_tree_function(node, FunctionScope(str(node.get_name())))
            elif type(node) == ModularModel:
                self.check_parse_tree_mmodel(node, ModularModelScope(str(node.get_name())))
            elif type(node) == ErrorToken:
                self.process_error_token(node)
            elif type(node) == ErrorNode:
                self.process_error_node(node)
            elif type(node) == SimpleStmt:
                if type(node.get_stmt()) == Declaration:
                    self.process_declaration(node, scope)
                elif type(node.get_stmt()) == VariableIn:
                    self.process_variablein(node, scope)
                elif type(node.get_stmt()) == Reaction:
                    reaction = node.get_stmt()
                    rate_law = reaction.get_rate_law()
                    if rate_law is not None:
                        self.check_rate_law(rate_law, scope)
                    self.process_reaction(node, scope)
                elif type(node.get_stmt()) == ModularModelCall:
                    self.process_mmodel_call(node, scope)
                elif type(node.get_stmt()) == IsAssignment:
                    self.process_is_assignment(node, scope)
                elif type(node.get_stmt()) == Assignment:
                    self.process_maybein(node, scope)
                    if type(node.get_stmt().get_value()) == FuncCall:
                        self.process_function_call(node, scope)
                elif type(node.get_stmt()) == Sboterm or type(node.get_stmt()) == Annotation:
                    self.process_annotation(node, scope)
                elif type(node.get_stmt()) == Event:
                    self.process_event(node, scope)

    def check_parse_tree_function(self, function, scope):
        # check the expression
        params = function.get_params()
        if params == None:
            return
        params = params.get_items()
        expr = function.get_expr()
        used = self.check_expr_undefined(params, expr)
        self.check_param_unused(used, params)

    def check_expr_undefined(self, params, expr):
        used = set()
        #   1.1 referencing undefined parameters
        for child in expr.children:
            if child is None or isinstance(child, Operator) or isinstance(child, Number):
                continue
            if isinstance(child, Name):
                used.add(child)
                if child not in params:
                    self.error.append(RefUndefined(child.range, child.text))
            elif isinstance(child, VarName):
                name = child.get_name()
                used.add(name)
                if name not in params:
                    self.error.append(RefUndefined(name.range, name.text))
            elif hasattr(child, 'children') and child.children != None:
                used = set.union(used, self.check_expr_undefined(params, child))
        return used
    
    def check_param_unused(self, used, params):
        for param in params:
            if param not in used:
                self.warning.append(UnusedParameter(param.range, param.text))
          
    def check_parse_tree_mmodel(self, mmodel, scope):
        used = set()
        stmt_list = mmodel.get_stmt_list()
        params = mmodel.get_params()
        if params == None:
            params = set()
        else:
            params = set(params.get_items())
        for node in stmt_list.children:
            if node is None:
                continue
            elif type(node) == ErrorToken:
                self.process_error_token(node)
            elif type(node) == ErrorNode:
                self.process_error_node(node)
            elif type(node) == SimpleStmt:
                if type(node.get_stmt()) == Declaration:
                    self.process_declaration(node, scope)
                elif type(node.get_stmt()) == VariableIn:
                    self.process_variablein(node, scope)
                elif type(node.get_stmt()) == Reaction:
                    reaction = node.get_stmt()
                    rate_law = reaction.get_rate_law()
                    if rate_law is not None:
                        used = set.union(used, self.check_rate_law(rate_law, scope, params))
                    self.process_reaction(node, scope)
                elif type(node.get_stmt()) == ModularModelCall:
                    self.process_mmodel_call(node, scope)
                elif type(node.get_stmt()) == IsAssignment:
                    self.process_is_assignment(node, scope)
                elif type(node.get_stmt()) == Assignment:
                    self.process_maybein(node, scope)
                    if type(node.get_stmt().get_value()) == FuncCall:
                        self.process_function_call(node, scope)
                elif type(node.get_stmt()) == Sboterm or type(node.get_stmt()) == Annotation:
                    self.process_annotation(node, scope)
                elif type(node.get_stmt()) == Event:
                    self.process_event(node, scope)
        self.check_param_unused(used, params)

    def check_rate_law(self, rate_law, scope, params=set()):
        used = set()
        for leaf in rate_law.scan_leaves():
            if isinstance(leaf, FuncCall):
                function_name = leaf.get_function_name().get_name()
                function = self.table.get(QName(BaseScope(), function_name))
                if len(function) == 0:
                    function = self.import_table.get(QName(BaseScope(), function_name))
                if len(function) == 0:
                    function = [functions.is_builtin_func(function_name.text)]
                if len(function) == 0:
                    self.error.append(UninitFunction(function_name.range, function_name.text))
                else:
                    if functions.is_builtin_func(function_name.text) == function[0]:
                        if leaf.get_params() is None:
                            params = []
                        else:
                            params = leaf.get_params().get_items()
                        if not functions.has_correct_args(function[0], len(params)):
                            self.error.append(IncorrectParamNum(leaf.range, functions.get_builtin_func_arg_counts(function[0]), len(params)))
                        continue
                    call_params = leaf.get_params().get_items() if leaf.get_params() is not None else []
                    if len(function[0].parameters) != len(call_params):
                        self.error.append(IncorrectParamNum(leaf.range, len(function[0].parameters), len(call_params)))
                    else:
                        for index in range(len(function[0].parameters)):
                            expec = function[0].parameters[index][0] if len(function[0].parameters[index]) != 0 else None
                            expec_type = expec.type if expec is not None else None
                            call = leaf.get_params().get_items()[index]
                            # parameters can be arithmetic expression
                            if isinstance(call, ArithmeticExpr):
                                continue
                            call_name = self.table.get(QName(scope, call))
                            if len(call_name) == 0:
                                call_name = self.import_table.get(QName(scope, call))
                            call_type = call_name[0].type if len(call_name) != 0 else None
                            if not expec_type is None and not call_type is None and not call_type.derives_from(expec_type):
                                self.error.append(ParamIncorrectType(call.range, expec_type, call_type))
            elif isinstance(leaf, Name):
                text = leaf.text
                used.add(leaf)
                sym = self.table.get(QName(scope, leaf))
                val = sym[0].value_node
                if val is None and sym[0].type != SymbolType.Species and leaf not in params:
                    self.error.append(RefUndefined(leaf.range, text))
                if val is None and sym[0].type == SymbolType.Species:
                    self.warning.append(SpeciesUndefined(leaf.range, text))
        return used

    def get_unique_name(self, prefix: str):
        return self.table.get_unique_name(prefix)

    def handle_child_incomp(self, scope: AbstractScope, node: TrunkNode, insert: bool):
        '''Find all `incomp` nodes among the descendants of node and record the compartment names.'''
        for child in node.descendants():
            # isinstance() is too slow here
            if child and type(child) == InComp:
                child = cast(InComp, child)
                if insert:
                    self.import_table.insert(QName(scope, child.get_comp().get_name()), SymbolType.Compartment)
                else:
                    self.table.insert(QName(scope, child.get_comp().get_name()), SymbolType.Compartment)

    def handle_is_const(self, scope: AbstractScope, node: TrunkNode, insert: bool):
        indicator = False
        for child in node.descendants():
            if indicator and child and type(child) == Name:
                
                child = cast(Name, child)
                
                if insert:
                    self.import_table.insert(QName(scope, child), SymbolType.Unknown, is_const=True)
                else:
                    self.table.insert(QName(scope, child), SymbolType.Unknown, is_const=True)
            indicator = False
            if child and type(child) == Operator:
                child = cast(Operator, child)
                if child.text == "$":
                    indicator = True

    def handle_arith_expr(self, scope: AbstractScope, expr: TreeNode, insert: bool):
        # TODO handle dummy tokens
        if not hasattr(expr, 'children'):
            if type(expr) == Name:
                leaf = cast(Name, expr)
                if insert:
                    self.import_table.insert(QName(scope, leaf), SymbolType.Parameter)
                else:
                    self.table.insert(QName(scope, leaf), SymbolType.Parameter)
        else:
            expr = cast(TrunkNode, expr)
            for leaf in expr.scan_leaves():
                if type(leaf) == Name:
                    leaf = cast(Name, leaf)
                    if insert:
                        self.import_table.insert(QName(scope, leaf), SymbolType.Parameter)
                    else:
                        self.table.insert(QName(scope, leaf), SymbolType.Parameter)
                    
    def handle_bool_expr(self, scope: AbstractScope, expr: TreeNode):
        if not hasattr(expr, 'children'):
            if type(expr) == Name:
                leaf = cast(Name, expr)
                self.table.insert(QName(scope, leaf), SymbolType.Parameter)
        else:
            expr = cast(TrunkNode, expr)
            for leaf in expr.scan_leaves():
                if type(leaf) == Name:
                    leaf = cast(Name, leaf)
                    self.table.insert(QName(scope, leaf), SymbolType.Parameter)

    def handle_reaction(self, scope: AbstractScope, reaction: Reaction, insert: bool):
        name = reaction.get_name()
        comp = None
        if reaction.get_maybein() != None and reaction.get_maybein().is_in_comp():
            comp = reaction.get_maybein().get_comp().get_name_text()
        if reaction.get_comp():
            comp = reaction.get_comp().get_comp().get_name_text()

        if name is not None:
            if insert:
                self.import_table.insert(QName(scope, name), SymbolType.Reaction, reaction, comp=comp)
            else:
                self.table.insert(QName(scope, name), SymbolType.Reaction, reaction, comp=comp)

        for species in chain(reaction.get_reactants(), reaction.get_products()):
            if insert:
                self.import_table.insert(QName(scope, species.get_name()), SymbolType.Species, comp=comp)
                self.import_table.get(QName(scope, species.get_name()))[0].in_reaction = True
            else:
                self.table.insert(QName(scope, species.get_name()), SymbolType.Species, comp=comp)
                self.table.get(QName(scope, species.get_name()))[0].in_reaction = True
        rate_law = reaction.get_rate_law()
        if rate_law is not None:
            self.handle_arith_expr(scope, rate_law, insert)
        self.handle_arith_expr(scope, reaction.get_rate_law(), insert)
    
    # Events currently not supported through import    
    def pre_handle_event(self, scope: AbstractScope, event: Event, insert: bool):
        self.pending_events.append((scope, event))
        name = event.get_name()
        comp = None
        if event.get_maybein() is not None and event.get_maybein().is_in_comp():
            comp = event.get_maybein().get_comp().get_name_text()
            
        if name is not None:
            self.table.insert(QName(scope, name), SymbolType.Event, event, comp=comp)
        else:
            self.unnamed_events_num += 1
            event.unnamed_label = self.unnamed_events_num
        event_delay = event.get_event_delay()
        if event_delay:
            expr = event_delay.get_expr()
            self.handle_bool_expr(scope ,expr)
        condition = event.get_condition()
        self.handle_bool_expr(scope, condition)

        for assignment in event.get_assignments():
            qname = QName(scope, assignment.get_name())
            self.table.insert_event(qname, event)
            self.handle_arith_expr(scope, assignment, insert)

    def handle_assignment(self, scope: AbstractScope, assignment: Assignment, insert: bool):
        comp = None
        if functions.is_reserved_name(assignment.get_name_text()):
            self.table.error.append(ReservedName(assignment.get_name().range, assignment.get_name_text()))
            return
        if type(assignment.get_value()) == FuncCall:
            self.handle_function_call(scope, assignment, insert)
            return
        if assignment.get_maybein() != None and assignment.get_maybein().is_in_comp():
            comp = assignment.get_maybein().get_comp().get_name_text()
        if insert:
            self.import_table.insert(QName(scope, assignment.get_name()), SymbolType.Parameter,
                            value_node=assignment, comp=comp)
        else:
            self.table.insert(QName(scope, assignment.get_name()), SymbolType.Parameter,
                            value_node=assignment, comp=comp)
        self.handle_arith_expr(scope, assignment.get_value(), insert)

    def resolve_variab(self, tree) -> Variability:
        return {
            'var': Variability.VARIABLE,
            'const': Variability.CONSTANT,
        }[tree.data]

    def resolve_var_type(self, tree) -> SymbolType:
        return {
            'species': SymbolType.Species,
            'compartment': SymbolType.Compartment,
            'formula': SymbolType.Parameter,
        }[tree.data]

    def handle_declaration(self, scope: AbstractScope, declaration: Declaration, insert: bool):
        modifiers = declaration.get_modifiers()
        variab = modifiers.get_variab()
        sub = modifiers.get_sub_modifier()

        stype = modifiers.get_type()
        is_const = (variab == Variability.CONSTANT)
        is_sub = (sub is not None)

        # Skip comma separators
        for item in declaration.get_items():
            name = item.get_maybein().get_var_name().get_name()
            value = item.get_value()

            comp = None
            if item.get_maybein() != None and item.get_maybein().is_in_comp():
                comp = item.get_maybein().get_comp().get_name_text()

            # TODO update variability
            # If there is value assignment (value is not None), then record the declaration item
            # as the value node. Otherwise put None. See that we can't directly put "value" as
            # argument "valud_node" since they are different things
            value_node = item if value else None
            if insert:
                self.import_table.insert(QName(scope, name), stype, declaration, value_node,
                                is_const=is_const, comp=comp, is_sub=is_sub)
            else:
                self.table.insert(QName(scope, name), stype, declaration, value_node, 
                                is_const=is_const, comp=comp, is_sub=is_sub)
            if value:
                self.handle_arith_expr(scope, value, insert)
    
    def pre_handle_annotation(self, scope: AbstractScope, annotation: Annotation, insert: bool):
        self.pending_annotations.append((scope, annotation, insert))
    
    def handle_annotation_list(self):
        for scope, annotation, insert in self.pending_annotations:
            self.handle_annotation(scope, annotation, insert)
    
    def handle_annotation(self, scope: AbstractScope, annotation: Annotation, insert: bool):
        name = annotation.get_var_name().get_name()
        # TODO(Gary) maybe we can have a narrower type here, since annotation is restricted only to
        # species or compartments? I'm not sure. If that's the case though, we'll need union types.
        qname = QName(scope, name)
        if insert:
            self.import_table.insert(qname, SymbolType.Unknown)
            self.import_table.insert_annotation(qname, annotation)
        else:
            self.table.insert(qname, SymbolType.Unknown)
            self.table.insert_annotation(qname, annotation)
    
    def pre_handle_import(self, scope: AbstractScope, imp: Import):
        self.pending_imports.append((scope, imp))
    
    def handle_import_list(self):
        for scope, imp in self.pending_imports:
            self.handle_import(scope, imp)
        for name in self.unit_names:
            value = self.table.get(name)[0]
            value.value_node.unit = self.unit_vals[name]

    def handle_import(self, scope: AbstractScope, imp: Import):
        name = imp.get_file_name()
        if self.cur_file_name == name.get_str():
            self.error.append(CircularImportFound(name.range))
            return
        qname = QName(scope, name)
        file_str = imp.get_file()
        if file_str is None:
            self.error.append(NoImportFile(name.range))
        elif self.import_table.get(qname):
            self.error.append(FileAlreadyImported(name.range, name.get_str()))
            self.import_table.remove(qname)
        elif file_str.get_issues():
            issues = list()
            for issue in file_str.get_issues():
                issues.append(issue.message.strip())
            self.error.append(GrammarHasIssues(name.range, issues))
        else:
            for node in file_str.tree.children:
                if isinstance(node, ErrorToken):
                    continue
                if isinstance(node, ErrorNode):
                    continue
                if isinstance(node, SimpleStmt):
                    scope = BaseScope()
                    if isinstance(node, ErrorToken):
                        continue
                    if isinstance(node, ErrorNode):
                        continue
                    stmt = node.get_stmt()
                    if isinstance(stmt, Import):
                        self.pre_handle_import(BaseScope(), stmt)
                        continue
                    if stmt is not None:
                        self.handle_child_incomp(scope, stmt, True)
                    if isinstance(stmt, ModularModelCall):
                        self.handle_mmodel_call_overwrite(stmt, name)
                        continue
                    if isinstance(stmt, Interaction):
                        self.handle_interaction(scope, stmt, True)
                        continue
                    if stmt is None:
                        continue
                    {
                        'Reaction': self.handle_reaction_overwrite,
                        'Assignment': self.handle_assignment_overwrite,
                        'Declaration': self.handle_decl_overwrite,
                        'Annotation': self.handle_annot_add,
                        'UnitDeclaration': self.handle_unit_decl_overwrite,
                        'UnitAssignment' : self.handle_unit_assign_overwrite,
                        'FunctionCall' : self.handle_func_call_overwrite,
                        'VariableIn' : self.handle_var_in_overwrite,
                        'IsAssignment' : self.handle_is_assign_overwrite,
                        'Sboterm' : self.handle_sboterm_overwrite,
                        'RateRules' : self.handle_rate_rule_overwrite,
                    }[stmt.__class__.__name__](scope, stmt)
                if isinstance(node, Model):
                    scope = ModelScope(str(node.get_name()))
                    if self.table.get(QName(BaseScope(), node.get_name())):
                        self.error.append(ModelAlreadyExists(name.range, node.get_name_str()))
                        return
                    for child in node.children:
                        if isinstance(child, ErrorToken):
                            continue
                        if isinstance(child, ErrorNode):
                            continue
                        if isinstance(child, SimpleStmtList):
                            for st in child.children:
                                if isinstance(st, ErrorToken):
                                    continue
                                if isinstance(st, ErrorNode):
                                    continue
                                stmt = st.get_stmt()
                                if stmt is None:
                                    continue
                                {
                                    'Reaction': self.handle_reaction,
                                    'Assignment': self.handle_assignment,
                                    'Declaration': self.handle_declaration,
                                    'Annotation': self.pre_handle_annotation,
                                    'UnitDeclaration': self.handle_unit_declaration,
                                    'UnitAssignment' : self.handle_unit_assignment,
                                    'ModularModelCall' : self.handle_mmodel_call,
                                    'FunctionCall' : self.handle_function_call,
                                    'VariableIn' : self.handle_variable_in,
                                    'IsAssignment' : self.pre_handle_is_assignment,
                                    'Interaction' : self.pre_handle_interaction,
                                    'RateRules' : self.pre_handle_rate_rule,
                                    'Sboterm' : self.pre_handle_sboterm,
                                    'Event' : self.pre_handle_event,
                                }[stmt.__class__.__name__](scope, stmt, True)
                                self.handle_child_incomp(scope, stmt, True)
                if isinstance(node, ModularModel):
                    scope = ModularModelScope(str(node.get_name()))
                    if self.table.get(QName(BaseScope(), node.get_name())):
                        self.error.append(ModelAlreadyExists(name.range, node.get_name_str()))
                        return
                    for child in node.children:
                        if isinstance(child, ErrorToken):
                            continue
                        if isinstance(child, ErrorNode):
                            continue
                        if isinstance(child, SimpleStmtList):
                            for st in child.children:
                                if isinstance(st, ErrorToken):
                                    continue
                                if isinstance(st, ErrorNode):
                                    continue
                                stmt = st.get_stmt()
                                if stmt is None:
                                    continue
                                {
                                    'Reaction': self.handle_reaction,
                                    'Assignment': self.handle_assignment,
                                    'Declaration': self.handle_declaration,
                                    'Annotation': self.pre_handle_annotation,
                                    'UnitDeclaration': self.handle_unit_declaration,
                                    'UnitAssignment' : self.handle_unit_assignment,
                                    'ModularModelCall' : self.handle_mmodel_call,
                                    'FunctionCall' : self.handle_function_call,
                                    'VariableIn' : self.handle_variable_in,
                                    'IsAssignment' : self.pre_handle_is_assignment,
                                    'Interaction' : self.pre_handle_interaction,
                                    'RateRules' : self.pre_handle_rate_rule,
                                    'Sboterm' : self.pre_handle_sboterm,
                                    'Event' : self.pre_handle_event,
                                }[stmt.__class__.__name__](scope, stmt, True)
                                self.handle_child_incomp(scope, stmt, True)
                        if isinstance(child, Parameters):
                            self.handle_parameters(scope, child, True)
                    self.handle_mmodel(node, True)
                if isinstance(node, Function):
                    if self.table.get(QName(BaseScope(), node.get_name())):
                        func_name = QName(BaseScope(), node.get_name()).name.text
                        self.error.append(FunctionAlreadyExists(name.range, func_name))
                        return
                    scope = FunctionScope(str(node.get_name()))
                    for child in node.children:
                        if isinstance(child, ErrorToken):
                            continue
                        if isinstance(child, ErrorNode):
                            continue
                        if isinstance(child, ArithmeticExpr):
                            self.handle_arith_expr(scope, child, True)
                        if isinstance(child, Parameters):
                            self.handle_parameters(scope, child, True)
                    self.handle_function(node, True)
            self.import_table.insert(qname, SymbolType.Import, imp=file_str.text)
    
    def handle_assignment_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_name())
        in_table = self.table.get(cur_qname)
        if not in_table or in_table[0].value_node is None:
            self.handle_assignment(scope, stmt, False)
            self.inserted[self.table.get(cur_qname)[0].name] = True
        elif in_table[0].value_node is not None and self.inserted[in_table[0].name]:
            in_table[0].value_node = stmt
            self.handle_arith_expr(scope, stmt.get_value(), False)
        self.handle_assignment(scope, stmt, True)
    
    def handle_is_assign_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_var_name())
        in_table = self.table.get(cur_qname)
        is_assign_ind = in_table[0].name + " is_assign"
        if not in_table or in_table[0].display_name is None:
            self.handle_is_assignment(scope, stmt, False)
            self.inserted[is_assign_ind] = True
        elif in_table[0].display_name is not None and self.inserted[is_assign_ind]:
            in_table[0].display_name = stmt.get_display_name().text
        self.handle_is_assignment(scope, stmt, True)

    def handle_unit_decl_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_var_name().get_name())
        in_table = self.table.get(cur_qname)
        if not in_table:
            self.handle_unit_declaration(scope, stmt, False)
            self.inserted[stmt.get_var_name().get_name()] = True
        elif in_table and self.inserted[stmt.get_var_name().get_name()]:
            self.replace_assign(cur_qname, stmt)
        self.handle_unit_declaration(scope, stmt, True)
    
    def handle_sboterm_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_var_name().get_name())
        in_table = self.table.get(cur_qname)
        sboterm_ind = in_table[0].name + " sboterm"
        if not in_table or not in_table[0].sboterms:
            self.handle_sboterm(scope, stmt, False)
            self.inserted[sboterm_ind] = True
        elif in_table and self.inserted[sboterm_ind]:
            in_table[0].sboterms[0].children[3].text = stmt.get_val()
        self.handle_sboterm(scope, stmt, True)
    
    def handle_rate_rule_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_name())
        in_table = self.table.get(cur_qname)
        rate_rule_ind = in_table[0].name + " rate_rule"
        if not in_table:
            self.handle_rate_rule(scope, stmt, False)
            self.inserted[rate_rule_ind] = True
        elif in_table and self.inserted[rate_rule_ind]:
            self.replace_assign(cur_qname, stmt)
        self.handle_rate_rule(scope, stmt, True)

    def handle_mmodel_call_overwrite(self, stmt, name):
        if stmt.get_name() is None:
            mmodel_name = stmt.get_mmodel_name()
        else:
            mmodel_name = stmt.get_name()
        cur_qname = QName(BaseScope(), mmodel_name)
        in_table = self.table.get(cur_qname)
        if in_table:
            self.error.append(DuplicateImportedMModelCall(name.range, mmodel_name.text))
        elif not in_table or in_table[0].value_node is None:
            self.handle_mmodel_call(BaseScope(), stmt, False)
        self.handle_mmodel_call(BaseScope(), stmt, True)
    
    def handle_decl_overwrite(self, scope, stmt):
        modifiers = stmt.get_modifiers()
        variab = modifiers.get_variab()
        sub = modifiers.get_sub_modifier()

        stype = modifiers.get_type()
        is_const = (variab == Variability.CONSTANT)
        is_sub = (sub is not None)
        
        for decl in stmt.get_items():
            name = decl.get_maybein().get_var_name().get_name()
            value = decl.get_value()

            comp = None
            if decl.get_maybein() != None and decl.get_maybein().is_in_comp():
                comp = decl.get_maybein().get_comp().get_name_text()
                
            value_node = decl if value else None
            cur_qname = QName(scope, decl.get_maybein().get_var_name().get_name())
            in_table = self.table.get(cur_qname)

            if not in_table or in_table[0].decl_node is None:
                self.table.insert(QName(scope, name), stype, stmt, value_node,
                                is_const=is_const, comp=comp, is_sub=is_sub)
                self.inserted_decl[self.table.get(cur_qname)[0].name] = True
            elif in_table[0].decl_node is not None and self.inserted_decl[in_table[0].name]:
                in_table[0].comp = comp
                if not stype == SymbolType.Unknown:
                    in_table[0].type = stype
                if value_node is not None:
                    in_table[0].value_node = value_node
                in_table[0].decl_node = stmt
                in_table[0].is_const = is_const
                in_table[0].is_sub = is_sub
        self.handle_declaration(scope, stmt, True)
        
    def handle_reaction_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_name())
        in_table = self.table.get(cur_qname)
        if not in_table or in_table[0].decl_node is None:
            self.handle_reaction(scope, stmt, False)
            self.inserted[self.table.get(cur_qname)[0].name] = True
        elif in_table[0].decl_node is not None and self.inserted[in_table[0].name]:
            self.replace_assign(cur_qname, stmt)
        self.handle_reaction(scope, stmt, True)
    
    def handle_unit_assign_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_var_name().get_name())
        in_table = self.table.get(cur_qname)
        unit_assign_ind = in_table[0].name + " unit_assign"
        if not in_table or in_table[0].value_node.unit is None:
            self.handle_unit_assignment(scope, stmt, False)
            self.inserted[unit_assign_ind] = True
        elif in_table[0].value_node.unit is not None and self.inserted[unit_assign_ind]:
            in_table[0].value_node.unit = stmt.get_sum()
        self.handle_unit_assignment(scope, stmt, True)
    
    def handle_annot_add(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_var_name().get_name())
        in_table = self.table.get(cur_qname)
        if in_table[0].annotations:
            for annot in in_table[0].annotations:
                if annot.get_uri() == stmt.get_uri():
                    self.handle_annotation(scope, stmt, True)
                    return
        self.handle_annotation(scope, stmt, False)
        self.handle_annotation(scope, stmt, True)
    
    def handle_var_in_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_name().get_name())
        in_table = self.table.get(cur_qname)
        var_in_ind = in_table[0].name + " var_in"
        if not in_table or in_table[0].decl_node is None:
            self.handle_variable_in(scope, stmt, False)
            self.inserted[var_in_ind] = True
        elif in_table[0].decl_node is not None and self.inserted[var_in_ind]:
            in_table[0].decl_node = stmt
            in_table[0].comp = stmt.get_incomp().get_comp().get_name_text()
        self.handle_variable_in(scope, stmt, True)
    
    def handle_func_call_overwrite(self, scope, stmt):
        cur_qname = QName(scope, stmt.get_name())
        in_table = self.table.get(cur_qname)
        if not in_table or in_table[0].value_node is None:
            self.handle_function_call(scope, stmt, False)
            self.inserted[self.table.get(cur_qname)[0].name] = True
        elif in_table[0].value_node is not None and self.inserted[in_table[0].name]:
            self.replace_assign(cur_qname, stmt)
        self.handle_function_call(scope, stmt, True)

    def pre_handle_rate_rule(self, scope, rate_rule, insert: bool):
        self.pending_rate_rules.append((scope, rate_rule, insert))

    def handle_rate_rules(self):
        for scope, rate_rule, insert in self.pending_rate_rules:
            self.handle_rate_rule(scope, rate_rule, insert)

    def handle_rate_rule(self, scope, rate_rule : RateRules, insert: bool):
        name = rate_rule.get_name()
        qname = QName(scope, name)
        expression = rate_rule.get_value()
        all_names = self.table.get_all_names()
        import_names = self.import_table.get_all_names()
        if len(self.table.get(qname)) != 0 or len(self.import_table.get(qname)) != 0:
            if len(self.table.get(qname)) == 0:
                var = self.import_table.get(qname)[0]
            else:
                var = self.table.get(qname)[0]
            if var.type == SymbolType.Species and var.in_reaction and not var.is_const:
                self.error.append(RateRuleNotInReaction(rate_rule.range, name.text))
            rate_rule_string = ""
            for leaf in expression.scan_leaves():
                if isinstance(leaf, Name) and leaf.text not in all_names and leaf.text not in import_names:
                    self.warning.append(VarNotFound(leaf.range, leaf.text))
                if isinstance(leaf, FuncCall):
                    continue
                if leaf.text == "+" or leaf.text == "-" or leaf.text == "*" or leaf.text == "/":
                    rate_rule_string += " " + (leaf.text) + " "
                else:
                    rate_rule_string += (leaf.text)
            if var.rate_rule != None:
                self.warning.append(RateRuleOverRidden(rate_rule.get_name().range, rate_rule.get_name().text, var))
            var.rate_rule = rate_rule_string
        else:
            self.warning.append(VarNotFound(rate_rule.get_name().range, rate_rule.get_name().text))
            
    def pre_handle_sboterm(self, scope: AbstractScope, sboterm: Sboterm, insert: bool):
        self.pending_sboterms.append((scope, sboterm, insert))
    
    def handle_sboterm_list(self):
        for scope, sboterm, insert in self.pending_sboterms:
            self.handle_sboterm(scope, sboterm, insert)
    
    def handle_sboterm(self, scope: AbstractScope, sboterm: Sboterm, insert: bool):
        name = sboterm.get_var_name().get_name()
        qname = QName(scope, name)
        if insert:
            symbol_list = self.import_table.get(qname)
        else:
            symbol_list = self.table.get(qname)
        if len(symbol_list) == 0:
            if insert:
                self.import_table.insert(qname, SymbolType.Parameter)
            else:
                self.table.insert(qname, SymbolType.Parameter)
        if insert:
            self.import_table.insert_sboterm(qname, sboterm)
        else:
            self.table.insert_sboterm(qname, sboterm)

    def get_annotation_descriptions(self):
        for scope, annotation, insert in self.pending_annotations:
            self.get_annotation_description(scope, annotation)
    
    def get_annotation_description(self, scope: AbstractScope, annotation: Annotation):
        name = annotation.get_var_name().get_name()
        qname = QName(scope, name)
        symbol = self.table.get(qname)
        if symbol:
            uri = annotation.get_uri()
            if uri[0:4] != HTTP:
                return
            if uri in symbol[0].queried_annotations.keys():
                return
            uri_split = uri.split(SLASH)
            website = uri_split[2]
            chebi_id = uri_split[4]
            if website == IDENTIFIERS_ORG:
                if uri_split[3] == CHEBI_LOWER:
                    chebi = ChEBI()
                    res = chebi.getCompleteEntity(chebi_id)
                    name = res.chebiAsciiName
                    definition = res.definition
                    queried = '\n{}\n\n{}\n'.format(name, definition)
                    symbol[0].queried_annotations[uri] = queried
                else:
                    return
                    # uniport = UniProt()
            elif website == RHEA_URL:
                rhea = Rhea()
                df_res = rhea.query(uri_split[4], columns=EQUATION_LOWER, limit=10)
                equation = df_res[EQUATION_CAP]
                queried = '\n{}\n'.format(equation[0])
                df_res += queried
                symbol[0].queried_annotations[uri] = queried
            else:
                ontology_info = uri_split[-1]
                ontology_info_split = ontology_info.split('_')
                ontology_name = ontology_info_split[0].lower()
                iri = uri_split[-1]
                
                response = requests.get(ONTOLOGIES_URL + ontology_name + ONTOLOGIES_URL_SECOND_PART + iri)
                if response.status_code == 406:
                    return
                response = response.json()
                if ontology_name == 'pr' or ontology_name == 'ma' or ontology_name == 'obi' or ontology_name == 'fma':
                    definition = response['description']
                else:
                    response_annot = response['annotation']
                    definition = response_annot['definition']
                name = response['label']
                queried =  '\n{}\n'.format(name)
                if definition:
                    queried += '\n{}\n'.format(definition[0])
                symbol[0].queried_annotations[uri] = queried

    def pre_handle_is_assignment(self, scope: AbstractScope, is_assignment: IsAssignment, insert: bool):
        self.pending_is_assignments.append((scope, is_assignment, insert))
    
    def handle_is_assignment_list(self):
        for scope, is_assignment, insert in self.pending_is_assignments:
            self.handle_is_assignment(scope, is_assignment, insert)
    
    def handle_is_assignment(self, scope: AbstractScope, is_assignment: IsAssignment, insert: bool):
        name = is_assignment.get_var_name()
        qname = QName(scope, name)
        if insert:
            var = self.import_table.get(qname)
        else:
            var = self.table.get(qname)
        display_name = is_assignment.get_display_name().text
        if len(var) != 0:
            if var[0].display_name != None:
                if insert:
                    self.import_table.insert_warning(OverridingDisplayName(is_assignment.range, name.text))
                else:
                    self.table.insert_warning(OverridingDisplayName(is_assignment.range, name.text))
            var[0].display_name = display_name
            if isinstance(var[0], FuncSymbol):
                qname_f = QName(FunctionScope(str(var[0].type_name)), name)
                if insert:
                    f_var = self.import_table.get(qname_f)
                else:
                    f_var = self.table.get(qname_f)
                if len(f_var) != 0:
                    f_var[0].display_name = display_name
                qname_b = QName(BaseScope(), name)
                if insert:
                    base_var = self.import_table.get(qname_b)
                else:
                    base_var = self.table.get(qname_b)
                if len(base_var) != 0:
                    base_var[0].display_name = display_name
            elif isinstance(var[0], MModelSymbol):
                qname_m = QName(ModularModelScope(str(var[0].type_name)), name)
                if insert:
                    m_var = self.import_table.get(qname_m)
                else:
                    m_var = self.table.get(qname_m)
                if len(m_var) != 0:
                    m_var[0].display_name = display_name
                qname_b = QName(BaseScope(), name)
                if insert:
                    base_var = self.import_table.get(qname_b)
                else:
                    base_var = self.table.get(qname_b)
                if len(base_var) != 0:
                    base_var[0].display_name = display_name
    
    def pre_handle_interaction(self, scope, Interaction, insert: bool):
        self.pending_interactions.append((scope, Interaction, insert))

    def handle_interactions(self):
        for scope, interaction, insert in self.pending_interactions:
            self.handle_interaction(scope, interaction, insert)

    def handle_interaction(self, scope, interaction : Interaction, insert: bool):
        name = interaction.get_species().get_name()
        reaction = interaction.get_reaction_namemaybein()
        if insert:
            self.import_table.insert(QName(scope, reaction.get_var_name().get_name()), SymbolType.Reaction)
        else:
            self.table.insert(QName(scope, reaction.get_var_name().get_name()), SymbolType.Reaction)
        opr = interaction.get_opr().text
        interaction_str = ''
        if opr == '-o':
            interaction_str += 'activation'
        elif opr == '-|':
            interaction_str += 'inhibition'
        elif opr == '-(':
            interaction_str += 'unknown interaction'
        # interaction_str += ' in reaction: ' + reaction.text
        if insert:
            self.import_table.insert(QName(scope, name), SymbolType.Unknown)
        else:
            self.table.insert(QName(scope, name), SymbolType.Unknown)
        interaction_name = interaction.get_name()
        if interaction_name:
            if insert:
                self.import_table.insert(QName(scope, interaction_name.get_name()), SymbolType.Interaction)
                self.import_table.get(QName(scope, interaction_name.get_name()))[0].interaction = interaction_str
            else:
                self.table.insert(QName(scope, interaction_name.get_name()), SymbolType.Interaction)
                self.table.get(QName(scope, interaction_name.get_name()))[0].interaction = interaction_str

    def handle_unit_declaration(self, scope: AbstractScope, unitdec: UnitDeclaration, insert: bool):
        varname = unitdec.get_var_name().get_name()
        unit_sum = unitdec.get_sum()
        qname = QName(scope, varname)
        if insert:
            self.import_table.insert(qname, SymbolType.Unit)
        else:
            self.table.insert(qname, SymbolType.Unit)
    
    def handle_unit_assignment(self, scope: AbstractScope, unitdec: UnitDeclaration, insert: bool):
        varname = unitdec.get_var_name().get_name()
        unit_sum = unitdec.get_sum()
        if insert:
            symbols = self.import_table.get(QName(scope, varname))
        else:
            symbols = self.table.get(QName(scope, varname))
        if symbols:
            sym = symbols[0]
            value_node = sym.value_node
            if isinstance(value_node, Assignment):
                value_node.unit = unit_sum
            elif isinstance(value_node, DeclItem):
                decl_assignment = value_node.children[1]
                decl_assignment.unit = unit_sum
    
    def handle_mmodel_call(self, scope: AbstractScope, mmodel_call: ModularModelCall, insert: bool):
        if mmodel_call.get_name() is None:
            name = mmodel_call.get_mmodel_name()
        else:
            name = mmodel_call.get_name()
        comp = None
        if mmodel_call.get_maybein() != None and mmodel_call.get_maybein().is_in_comp():
            comp = mmodel_call.get_maybein().get_comp().get_name_text()
        if insert:
            self.import_table.insert(QName(scope, name), SymbolType.Parameter,
                    value_node=mmodel_call, comp=comp)
        else:
            self.table.insert(QName(scope, name), SymbolType.Parameter,
                        value_node=mmodel_call, comp=comp)

    def handle_function_call(self, scope: AbstractScope, function_call: FunctionCall, insert: bool):
        comp = None
        if function_call.get_maybein() != None and function_call.get_maybein().is_in_comp():
            comp = function_call.get_maybein().get_comp().get_name_text()
        if insert:
            self.import_table.insert(QName(scope, function_call.get_name()), SymbolType.Parameter,
                    value_node=function_call, comp=comp)
        else:
            self.table.insert(QName(scope, function_call.get_name()), SymbolType.Parameter,
                        value_node=function_call, comp=comp)

    def handle_variable_in(self, scope: AbstractScope, variable_in: VariableIn, insert: bool):
        name = variable_in.get_name().get_name()
        comp = variable_in.get_incomp().get_comp().get_name_text()
        if insert:
            self.import_table.insert(QName(scope, name), SymbolType.Variable, decl_node=variable_in, comp=comp)
        else:
            self.table.insert(QName(scope, name), SymbolType.Variable, decl_node=variable_in, comp=comp)

    def handle_parameters(self, scope: AbstractScope, parameters: Parameters, insert: bool):
        for parameter in parameters.get_items():
            qname = QName(scope, parameter)
            if insert:
                self.import_table.insert(qname, SymbolType.Parameter)
            else:
                self.table.insert(qname, SymbolType.Parameter)
    
    def handle_function(self, function, insert: bool):
        if functions.is_reserved_name(function.get_name_str()):
            self.table.error.append(ReservedName(function.get_name().range, function.get_name_str()))
            return
        if function.get_params() is not None:
            params = function.get_params().get_items()
        else:
            params = []
        scope = FunctionScope(str(function.get_name()))
        parameters = []
        for name in params:
            # get symbols
            if insert:
                qname = self.resolve_import_qname(QName(scope, name))
            else:
                qname = self.resolve_qname(QName(scope, name))
            parameters.append(qname)
        if insert:
            self.import_table.insert_function(QName(BaseScope(), function), SymbolType.Function, parameters)
            self.import_table.insert_function(QName(FunctionScope(str(function.get_name())), function),
                                    SymbolType.Function, parameters)
        else:
            self.table.insert_function(QName(BaseScope(), function), SymbolType.Function, parameters)
            self.table.insert_function(QName(FunctionScope(str(function.get_name())), function), SymbolType.Function, parameters)

    def handle_mmodel(self, mmodel, insert: bool):
        if functions.is_reserved_name(mmodel.get_name_str()):
            self.table.error.append(ReservedName(mmodel.get_name().range, mmodel.get_name_str()))
            return
        if mmodel.get_params() is not None:
            params = mmodel.get_params().get_items()
        else:
            params = []
        scope = ModularModelScope(str(mmodel.get_name()))
        parameters = []
        for name in params:
            if insert:
                qname = self.resolve_import_qname(QName(scope, name))
            else:
                qname = self.resolve_qname(QName(scope, name))
            parameters.append(qname)
        if insert:
            self.import_table.insert_mmodel(QName(BaseScope(), mmodel), SymbolType.ModularModel, parameters)
            self.import_table.insert_mmodel(QName(ModularModelScope(str(mmodel.get_name())), mmodel),
                                    SymbolType.ModularModel, parameters)
        else:
            self.table.insert_mmodel(QName(BaseScope(), mmodel), SymbolType.ModularModel, parameters)
            self.table.insert_mmodel(QName(ModularModelScope(str(mmodel.get_name())), mmodel), SymbolType.ModularModel, parameters)

    def process_error_token(self, node):
        node = cast(ErrorToken, node)
        if node.text.strip() == '':
            # this must be an unexpected newline
            self.error.append(UnexpectedNewlineIssue(node.range.start))
        else:
            self.error.append(UnexpectedTokenIssue(node.range, node.text))
    
    def process_error_node(self, node):
        node = cast(ErrorNode, node)
        last_leaf = node.last_leaf()
        if last_leaf and last_leaf.next is None:
            self.error.append(UnexpectedEOFIssue(last_leaf.range))
    
    def process_declaration(self, node, scope):
        type = node.get_stmt().get_modifiers().get_type()
        sub = node.get_stmt().get_modifiers().get_sub_modifier()
        # sub only works with species
        if sub is not None and type != SymbolType.Species:
            self.error.append(SubError(node.get_stmt().range))
        for item in node.get_stmt().get_items():
            maybein = item.get_maybein()
            if maybein is not None and maybein.is_in_comp():
                comp = maybein.get_comp()
                compt = self.table.get(QName(scope, comp.get_name()))
                if compt[0].value_node is None:
                    compt = self.import_table.get(QName(scope, comp.get_name()))
                if not compt or compt[0].value_node is None:
                    # 3. add warning
                    self.warning.append(UninitCompt(comp.get_name().range, comp.get_name_text()))
    
    def process_variablein(self, node, scope):
        comp = node.get_stmt().get_incomp().get_comp()
        compt = self.table.get(QName(scope, comp.get_name()))
        if compt[0].value_node is None:
            compt = self.import_table.get(QName(scope, comp.get_name()))
        if not compt or compt[0].value_node is None:
            # 3. add warning
            self.warning.append(UninitCompt(comp.get_name().range, comp.get_name_text()))
        # also check if the parameter is defined or not
        param_name = node.get_stmt().get_name()
        matched_param = self.table.get(QName(scope, param_name.get_name()))
        if matched_param[0].value_node is None:
            matched_param = self.import_table.get(QName(scope, param_name.get_name()))
        if not matched_param or matched_param[0].value_node is None:
            self.error.append(RefUndefined(param_name.get_name().range, param_name.get_name_text()))
    
    def process_reaction(self, node, scope):
        reaction = node.get_stmt()
        rate_law = reaction.get_rate_law()
        if rate_law is None:
            self.warning.append(UninitRateLaw(reaction.range, reaction.get_name_text()))
        # check if all species have been initialized
        species_list = []
        for species in reaction.get_reactants():
            species_list.append(species)
        for species in reaction.get_products():
            species_list.append(species)
        for species in species_list:
            species_name = species.get_name()
            matched_species = self.table.get(QName(scope, species_name))
            if matched_species[0].value_node is None:
                matched_species = self.import_table.get(QName(scope, species_name))
            if not matched_species or matched_species[0].value_node is None:
                self.warning.append(SpeciesUndefined(species.range, species_name.text))
        self.process_maybein(node, scope)
    
    def process_mmodel_call(self, node, scope):
        mmodel_name = node.get_stmt().get_mmodel_name()
        mmodel = self.table.get(QName(BaseScope(), mmodel_name))
        if len(mmodel) == 0:
            mmodel = self.import_table.get(QName(BaseScope(), mmodel_name))
        if len(mmodel) == 0:
            self.error.append(UninitMModel(mmodel_name.range, mmodel_name.text))
        else:
            call_params = node.get_stmt().get_params().get_items() if node.get_stmt().get_params() is not None else []
            if len(mmodel[0].parameters) != len(call_params):
                self.error.append(IncorrectParamNum(node.range, len(mmodel[0].parameters), len(call_params)))
            else:
                for index in range(len(mmodel[0].parameters)):
                    expec = mmodel[0].parameters[index][0] if len(mmodel[0].parameters[index]) != 0 else None
                    expec_type = expec.type if expec is not None else None
                    call = node.get_stmt().get_params().get_items()[index] if node.get_stmt().get_params() is not None else []
                    call_name = self.table.get(QName(scope, call))
                    if len(call_name) == 0:
                        call_name = self.import_table.get(QName(scope, call))
                    call_type = call_name[0].type if len(call_name) != 0 else None
                    if not expec_type is None and not call_type is None and not call_type.derives_from(expec_type):
                        self.error.append(ParamIncorrectType(call.range, expec_type, call_type))
        self.process_maybein(node, scope)
    
    def process_function_call(self, node, scope):
        cur_func = node.get_stmt().get_value()
        function_name = cur_func.get_function_name().get_name()
        function = self.table.get(QName(BaseScope(), function_name))
        if len(function) == 0:
            function = self.import_table.get(QName(BaseScope(), function_name))
        if len(function) == 0:
            function = functions.is_builtin_func(function_name.text)
        if len(function) == 0:
            self.error.append(UninitFunction(function_name.range, function_name.text))
        else:
            builtin_func = functions.is_builtin_func(function_name.text)
            if builtin_func and builtin_func[0] == function[0]:
                if cur_func.get_params() is None:
                    params = []
                else:
                    params = cur_func.get_params().get_items()
                if not functions.has_correct_args(function[0], len(params)):
                    self.error.append(IncorrectParamNum(node.range, functions.get_builtin_func_arg_counts(function[0]), len(params)))
            else:
                call_params = cur_func.get_params().get_items() if cur_func.get_params() is not None else []
                if len(function[0].parameters) != len(call_params):
                    self.error.append(IncorrectParamNum(node.range, len(function[0].parameters), len(call_params)))
                else:
                    for index in range(len(function[0].parameters)):
                        expec = function[0].parameters[index][0] if len(function[0].parameters[index]) != 0 else None
                        expec_type = expec.type if expec is not None else None
                        call = cur_func.get_params().get_items()[index]
                        # parameter can be arithmetic expression
                        if isinstance(call, ArithmeticExpr):
                            continue
                        call_name = self.table.get(QName(scope, call))
                        if len(call_name) == 0:
                            call_name = self.import_table.get(QName(scope, call))
                        call_type = call_name[0].type if len(call_name) != 0 else None
                        if not expec_type is None and not call_type is None and not call_type.derives_from(expec_type):
                            self.error.append(ParamIncorrectType(call.range, expec_type, call_type))
        self.process_maybein(node, scope)

    def process_maybein(self, node, scope):
        maybein = node.get_stmt().get_maybein()
        if maybein is not None and maybein.is_in_comp():
            comp = maybein.get_comp()
            compt = self.table.get(QName(scope, comp.get_name()))
            if compt[0].value_node is None:
                compt = self.import_table.get(QName(scope, comp.get_name()))
            if not compt or compt[0].value_node is None:
                # 3. add warning
                self.warning.append(UninitCompt(comp.get_name().range, comp.get_name_text()))
    
    def process_is_assignment(self, node, scope):
        name = node.get_stmt().get_var_name()
        qname = QName(scope, name)
        var = self.table.get(qname)
        if len(var) == 0:
            var = self.import_table.get(qname)
        if len(var) == 0:
            self.warning.append(VarNotFound(name.range, name.text))
            
    def process_annotation(self, node, scope):
        name = node.get_stmt().get_var_name().get_name()
        qname = QName(scope, name)
        var = self.table.get(qname)
        if var[0].value_node is None and var[0].type == SymbolType.Species:
            self.error.append(RefUndefined(name.range, name.text))
            
    def process_sbo(self, node, scope):
        name = node.get_stmt().get_var_name().get_name()
        qname = QName(scope, name)
        var = self.table.get(qname)
        if var[0].value_node is None and var[0].type == SymbolType.Species:
            self.error.append(RefUndefined(name.range, name.text))
        
        
    def process_event(self, node, scope):
        event: Event = node.get_stmt()
        if event.get_event_delay():
            self.handle_bool_expr(scope, event.get_event_delay().get_expr())
        curr_triggers = dict()
        for trigger in event.get_triggers():
            if trigger.get_keyword().text in curr_triggers.keys():
                self.warning.append(ObscuredEventTrigger(curr_triggers.get(trigger.get_keyword().text).range, trigger.range, curr_triggers.get(trigger.get_keyword().text).to_string()))
            curr_triggers[trigger.get_keyword().text] = trigger
        for assignment in event.get_assignments():
            var_name = assignment.get_name()
            self._check_event_var_name(var_name, scope)
            if issubclass(type(assignment.get_value()), TrunkNode):
                for leaf in assignment.get_value().descendants():
                    if isinstance(leaf, Name):
                        name = self.table.get(QName(scope, leaf))
                        if name[0].value_node is None:
                            self.error.append(RefUndefined(leaf.range, name[0].name))
            # var = self.table.get(QName(scope, var_name))
            # if not var[0].type.derives_from(SymbolType.Parameter):
            #     self.warning.append(UninitVar(var_name.range, var_name.text))
        self.process_maybein(node, scope)
        
    def _check_event_var_name(self, var_name, scope):
        var = self.table.get(QName(scope, var_name))
        if not var[0].type.derives_from(SymbolType.Parameter):
            self.error.append(RefUndefined(var_name.range, var_name.text))
        

# def get_ancestors(node: ASTNode):
#     ancestors = list()
#     while True:
#         parent = getattr(node, 'parent')
#         if parent is None:
#             break
#         ancestors.append(parent)
#         node = parent
#     return ancestors


# def find_node(nodes: List[Tree], data: str):
#     for node in nodes:
#         if node.data == data:
#             return node
#     return None
