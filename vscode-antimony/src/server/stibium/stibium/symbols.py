'''Classes for working with and storing symbols.
'''
import requests
import logging
from bioservices import ChEBI, UniProt, Rhea
from stibium.ant_types import Annotation, Name, Sboterm, TreeNode
from .types import Issue, ObscuredValueCompartment, RedefinedFunction, OverrodeValue, ObscuredDeclaration, ObscuredValue, SrcRange, SymbolType, IncompatibleType
from .ant_types import LeafNode, VarName, Declaration, VariableIn, Function, DeclItem, Assignment, ModularModel, Number, ModularModelCall, Event

import abc
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from typing import DefaultDict, Dict, List, Optional, Set, Tuple, Union
from lark.lexer import Token

from lark.tree import Tree

vscode_logger = logging.getLogger("vscode logger: ")

'''Classes that represent scopes. TODO rename all these to Scope, b/c Scope is not the same thing as scope'''
class AbstractScope(abc.ABC):
    '''Should never be instantiated.'''
    pass


class BaseScope(AbstractScope):
    '''The highest-level scope within a file, outside of any declared models.'''
    def __init__(self):
        pass

    def __eq__(self, other):
        if not isinstance(other, BaseScope):
            return NotImplemented
        
        return True

    def __hash__(self):
        return hash(('_base', ''))


class ModelScope(AbstractScope):
    '''The scope for statements in declared models.'''
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, ModelScope):
            return NotImplemented
        
        return self.name == other.name

    def __hash__(self):
        return hash(('model', self.name))

class ModularModelScope(AbstractScope):
    '''The scope for statements in declared models.'''
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, ModularModelScope):
            return NotImplemented
        
        return self.name == other.name

    def __hash__(self):
        return hash(('modular_model', self.name))


class FunctionScope(AbstractScope):
    '''The scope for statements in functions.'''
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, FunctionScope):
            return NotImplemented

        return self.name == other.name

    def __hash__(self):
        return hash(('function', self.name))


@dataclass
class QName:
    '''Represents a qualified name; i.e. a scope and a name string.'''
    scope: AbstractScope
    name: Name

    def __eq__(self, other):
        if not isinstance(other, FunctionScope):
            return NotImplemented

        return self.scope == other.scope and self.name.text == other.name.text

    def __hash__(self):
        return hash((self.scope, self.name.text))

class Symbol:
    '''A generic Symbol.

    TODO document what the tokens are
    Attributes:
        name:           The name of the symbol.
        typ:            The type of the symbol.
        type_name:      The exact analysis token of the symbol.
        dcl_node:       The analysis Node that represents the declaration statement of the symbol. May
                        be None if the symbol was not explicitly declared.
        display_name:   The display name of the symbol
    '''

    name: str
    type: SymbolType
    type_name: Name
    decl_name: Optional[Name]
    decl_node: Optional[TreeNode]
    value_node: Optional[TreeNode]
    annotations: List[Annotation]
    sboterms: List[Sboterm]
    display_name: str
    comp: str
    is_const: bool
    is_sub: bool
    imp: str
    interaction: str
    rate_rule: str
    in_reaction: bool
    events: List[Event]

    def __init__(self, name: str, typ: SymbolType, type_name: Name,
            decl_name: Name = None,
            decl_node: TreeNode = None,
            value_node: TreeNode = None,
            display_name: str = None,
            comp: str = None,
            is_const: bool = False,
            is_sub: bool = False,
            imp: str = None,
            interaction = None,
            rate_rule: str = None,
            ):
        self.name = name
        self.type = typ
        self.type_name = type_name
        self.decl_name = decl_name
        self.decl_node = decl_node
        self.value_node = value_node
        self.annotations = list()
        self.sboterms = list()
        self.display_name = display_name
        self.comp = comp
        self.is_const = is_const
        self.is_sub = is_sub
        self.imp = imp
        self.interaction = interaction
        self.rate_rule = rate_rule
        self.in_reaction = False
        self.queried_annotations = dict()
        self.events = list()

    def def_name(self):
        '''Return the Name that should be considered as the definition'''
        # return self.decl_name or self.value_node or self.type_name
        return self.value_node or self.decl_name or self.type_name

    def help_str(self):
        ret = "```"
        # add formula later
        if self.type == SymbolType.Parameter or \
            self.type == SymbolType.Species or \
                self.type == SymbolType.Compartment:
            if self.is_const:
                ret += '\n{}'.format("const")
            else:
                ret += '\n{}'.format("var")

        if self.display_name != None:
            ret += '\n{}'.format(self.display_name)
        if self.rate_rule is not None:
            ret += '\n{}'.format("Rate Rule: " + self.rate_rule)
        
        if self.interaction != None:
            ret += '\n{}'.format(self.interaction)

        if self.is_sub:
            ret += '\n{}'.format("Substance-only species")

        if isinstance(self, MModelSymbol):
            name = self.name
            ret += '\n{}'.format(name) + "("
            for index, param in enumerate(self.parameters):
                if not param:
                    ret += ")\n"
                    ret += "```"
                    return ret
                type = param[0].type
                ret += str(type) + ": " + param[0].name
                if index != len(self.parameters) - 1:
                    ret += ", "
            ret += ")\n"
        elif isinstance(self, FuncSymbol):
            name = self.name
            ret += '\n{}'.format(name) + "("
            for index, param in enumerate(self.parameters):
                ret += param[0].name
                if index != len(self.parameters) - 1:
                    ret += ", "
            ret += ")\n"
        elif self.value_node is not None and self.value_node.get_value() is not None: 
            init_val = ""
            if isinstance(self.value_node.get_value(), Number):
                init_val = " " + self.value_node.get_value().text
            else:
                init_val = _get_init_val(self.value_node.get_value())
            if isinstance(self.value_node, Assignment) and self.value_node.get_type() is not None:
                ret += '\n({}) {}\n{}\n'.format(
                    self.type, self.name, 
                    "Initialized Value:" + init_val  + 
                    _get_init_val(self.value_node.get_type()))
            elif isinstance(self.value_node, DeclItem) and self.value_node.get_decl_assignment().get_type() is not None:
                ret += '\n({}) {}\n{}\n'.format(
                    self.type, self.name, 
                    "Initialized Value:" + init_val  + 
                    _get_init_val(self.value_node.get_decl_assignment().get_type()))
            else:
                ret += '\n({}) {}\n{}\n'.format(
                    self.type, self.name, 
                    "Initialized Value:" + init_val)
        else:
            ret += '\n({}) {}\n'.format(self.type, self.name)
        if self.events:
            for event in self.events:
                event_name = event.get_name_text()
                if event_name is not None:
                    ret += 'event {}\n'.format(event_name)
                else:
                    ret += 'unnamed event {}\n'.format(event.unnamed_label)

        if self.comp:
            ret += 'In compartment: {}\n'.format(self.comp)

        if self.imp:
            ret += 'The imported data: \n{}\n'.format(self.imp)

        ret += '```'

        if self.annotations:
            # add the first annotation
            for annotation in self.annotations:
                uri = annotation.get_uri()
                ret += '\n***\n{}\n'.format(uri)
                if uri[0:4] != 'http':
                    continue
                if uri in self.queried_annotations.keys():
                    ret += self.queried_annotations[uri]
                    continue
                uri_split = uri.split('/')
                website = uri_split[2]
                chebi_id = uri_split[4]
                if website == 'identifiers.org':
                    if uri_split[3] == 'chebi':
                        chebi = ChEBI()
                        res = chebi.getCompleteEntity(chebiId=chebi_id)
                        name = res.chebiAsciiName
                        definition = res.definition
                        queried = '\n{}\n\n{}\n'.format(name, definition)
                        ret += queried
                        self.queried_annotations[uri] = queried
                    else:
                        continue
                        # uniport = UniProt()
                elif website == 'www.rhea-db.org':
                    rhea = Rhea()
                    df_res = rhea.query(uri_split[4], columns="equation", limit=10)
                    equation = df_res['Equation']
                    queried = '\n{}\n'.format(equation[0])
                    df_res += queried
                    self.queried_annotations[uri] = queried
                else:
                    ontology_name = uri_split[-1].split('_')[0].lower()
                    iri = uri_split[-1]
                    response = requests.get('http://www.ebi.ac.uk/ols/api/ontologies/' + ontology_name + '/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F' + iri).json()
                    if ontology_name == 'pr' or ontology_name == 'ma' or ontology_name == 'obi' or ontology_name == 'fma':
                        definition = response['description']
                    else:
                        response_annot = response['annotation']
                        definition = response_annot['definition']
                    name = response['label']
                    queried =  '\n{}\n'.format(name)
                    if definition:
                        queried += '\n{}\n'.format(definition[0])
                    ret += queried
                    self.queried_annotations[uri] = queried
        if self.sboterms:
            # add all sboterms
            for sboterm in self.sboterms:
                if sboterm.get_val()[:4] == 'SBO:':
                    ret += '\n***\nSBOterm: {}\n'.format(sboterm.get_val()[4:])
                else:
                    ret += '\n***\nSBOterm: {}\n'.format(sboterm.get_val())
        return ret


def _get_init_val(node):
    if node == None or not hasattr(node, "children"):
        return ""
    elif (isinstance(node, VarName)):
        return " " + node.get_name_text()
    elif hasattr(node, "text"):
        return " " + node.text
    init_val = ""
    for child in node.children:
        if isinstance(child, VarName):
            init_val += " " + child.get_name_text()
        elif hasattr(child, "text"):
            init_val += " " + child.text
        else:
            init_val += _get_init_val(child)
    return init_val


class VarSymbol(Symbol):
    '''Represents a variable, rather than a function or model.
    
    TODO account for variability
    '''

class FuncSymbol(Symbol):
    '''
    Symbol for func
    '''
    parameters: List[VarSymbol]

    def __init__(self, name: str, typ: SymbolType, type_name: Name,
            parameters):
        Symbol.__init__(self, name, typ, type_name)
        self.parameters = parameters
        self.type = SymbolType.Function

class MModelSymbol(Symbol):
    '''
    Symbol for modular model
    '''
    parameters: List[VarSymbol]

    def __init__(self, name: str, typ: SymbolType, type_name: Name,
            parameters):
        Symbol.__init__(self, name, typ, type_name)
        self.parameters = parameters
        self.type = SymbolType.ModularModel

# TODO allow the same scope and name to map to multiple symbols, since antimony allows
# models and variables to have the same name
class SymbolTable:
    # In the future, maybe use a tree-like data structure? Probably not necessary though - Gary.
    _table: DefaultDict[AbstractScope, Dict[str, Symbol]]
    _qnames: List[QName]

    def __init__(self):
        self._table = defaultdict(dict)
        self._error = list()
        self._warning = list()
        self._qnames = list()

    def _leaf_table(self, scope: AbstractScope):
        return self._table[scope]

    @property
    def error(self):
        return self._error

    @property
    def warning(self):
        return self._warning

    def get_all_names(self):
        '''Get all the unique names in the table as a set (outside of scope) '''
        names = set()
        for leaf_table in self._table.values():
            names |= leaf_table.keys()
        return names

    def get_all_qnames(self):
        '''Get all the unique names in the table as a set (outside of scope) '''
        return self._qnames

    def get_unique_name(self, prefix: str, scope: AbstractScope = None) -> str:
        '''Obtain a unique name under the scope by trying successively larger number suffixes.
        
        If scope is None, then find a name unique in every scope.
        '''
        if scope is None:
            all_names = self.get_all_names()

            i = 0
            while True:
                name = '{}{}'.format(prefix, i)
                if name not in all_names:
                    break
                i += 1
        else:
            leaf_table = self._leaf_table(scope)
            i = 0
            while True:
                name = '{}{}'.format(prefix, i)
                if name not in leaf_table:
                    break
                i += 1
        return name

    def get(self, qname: QName) -> List[Symbol]:
        leaf_table = self._leaf_table(qname.scope)
        if isinstance(qname.name, VarName):
            name = qname.name.get_name().text
        else:
            name = qname.name.text
        if isinstance(name, str) and name in leaf_table:
            return [leaf_table[name]]
        else:
            return []
    
    def remove(self, qname: QName):
        leaf_table = self._leaf_table(qname.scope)
        leaf_table.pop(qname.name.text)
    
    def insert_warning(self, issue: Issue):
        self.warning.append(issue)
    
    def insert_function_holder(self, function, scope):
        leaf_table = self._leaf_table(scope)
        sym = FuncSymbol(function.name, function.type, function.type_name, parameters=function.parameters)
        leaf_table[function.name] = sym
    
    def insert_mmodel_holder(self, mmodel, scope):
        leaf_table = self._leaf_table(scope)
        sym = MModelSymbol(mmodel.name, mmodel.type, mmodel.type_name, parameters=mmodel.parameters)
        leaf_table[mmodel.name] = sym

    def insert_function(self, qname: QName, typ: SymbolType, parameters, decl_node: TreeNode = None,
               value_node: TreeNode = None):
        assert qname.name is not None
        self._qnames.append(qname)
        leaf_table = self._leaf_table(qname.scope)
        name = qname.name.get_name().text
        if name not in leaf_table:
            sym = FuncSymbol(name, typ, qname.name.get_name(), parameters=parameters)
            leaf_table[name] = sym
        else:
            # variable already exists
            sym = leaf_table[name]
            old_type = sym.type
            if typ.derives_from(old_type):
                old_range = sym.type_name.range
                # new type is valid and narrower
                sym.type = typ
                sym.type_name = qname.name
                # error
                new_range = qname.name.get_name().range
                self._error.append(RedefinedFunction(new_range, name, old_range))
                self._error.append(RedefinedFunction(old_range, name, new_range))
            else:
                old_range = sym.type_name.range
                new_range = qname.name.get_name().range
                self._error.append(IncompatibleType(old_type, old_range, typ, new_range))
                self._error.append(IncompatibleType(old_type, new_range, typ, old_range))
        

    def insert_mmodel(self, qname: QName, typ: SymbolType, parameters, decl_node: TreeNode = None,
               value_node: TreeNode = None):
        assert qname.name is not None
        self._qnames.append(qname)
        name = qname.name.get_name().text
        sym = MModelSymbol(name, type, qname.name.get_name(), parameters=parameters)
        leaf_table = self._leaf_table(qname.scope)
        leaf_table[name] = sym

    def insert(self, qname: QName, typ: SymbolType, decl_node: TreeNode = None,
               value_node: TreeNode = None, is_const : bool = False, comp : str = None, 
               is_sub : bool = False, imp : str = None):
        '''Insert a variable symbol into the symbol table.'''
        # TODO create more functions like insert_var(), insert_reaction(), insert_model() and
        # create more specific symbols. Need to store things like value for types like var.
        # Have an inner method that returns (added, [errors]). Update the value, etc. only if
        # successfully added.
        assert qname.name is not None
        self._qnames.append(qname)
        leaf_table = self._leaf_table(qname.scope)
        name = qname.name.text
        if name not in leaf_table:
            # first time parsing, insert directly in the table
            sym = VarSymbol(name, typ, qname.name, is_const=is_const, comp=comp, is_sub=is_sub, imp=imp)
            leaf_table[name] = sym
        else:
            # variable already exists
            sym = leaf_table[name]
            old_type = sym.type
            if typ.derives_from(old_type):
                # new type is valid and narrower
                sym.type = typ
                sym.type_name = qname.name
                if is_const:
                    sym.is_const = is_const
                if not sym.comp:
                    sym.comp = comp
                if is_sub:
                    sym.is_sub = is_sub
                if not sym.imp:
                    sym.imp = imp
            elif old_type.derives_from(typ):
                # legal, but useless information
                if is_const:
                    sym.is_const = is_const
                if not sym.comp:
                    sym.comp = comp
                if is_sub:
                    sym.is_sub = is_sub
                if not sym.imp:
                    sym.imp = imp
            else:
                old_range = sym.type_name.range
                new_range = qname.name.range
                if value_node is not None:
                    self._error.append(IncompatibleType(old_type, old_range, typ, value_node.range))
                    self._error.append(IncompatibleType(old_type, value_node.range, typ, old_range))
                else:
                    self._error.append(IncompatibleType(old_type, old_range, typ, new_range))
                    self._error.append(IncompatibleType(old_type, new_range, typ, old_range))
                return

        # warning: overriding previous assignment
        if value_node is not None:
            value_name = qname.name
            if sym.value_node is not None:
                old_range = sym.value_node.range
                new_range = value_node.range
                # Overriding previous declaration
                self._warning.append(ObscuredValue(old_range, new_range, value_name.text))
                self._warning.append(OverrodeValue(new_range, old_range, value_name.text))
            sym.value_node = value_node
        elif decl_node is not None:
            decl_name = qname.name
            if sym.decl_node is not None and (type(decl_node) != Declaration or decl_node.get_modifiers is None):
                old_range = sym.decl_node.range
                new_range = decl_node.range
                # Overriding previous declaration
                if isinstance(decl_node, VariableIn):
                    self._warning.append(ObscuredValueCompartment(old_range, new_range, decl_name.text))
                    self._warning.append(ObscuredValueCompartment(new_range, old_range, decl_name.text))
                else:
                    self._warning.append(ObscuredValue(old_range, new_range, decl_name.text))
                    self._warning.append(OverrodeValue(new_range, old_range, decl_name.text))
            sym.decl_node = decl_node
            sym.decl_name = decl_name


    def insert_annotation(self, qname: QName, node: Annotation):
        leaf_table = self._leaf_table(qname.scope)
        name = qname.name.text
        if name not in leaf_table:
            sym = VarSymbol(name, SymbolType.Unknown, qname.name)
            leaf_table[name] = sym
        else:
            sym = leaf_table[name]
        sym.annotations.append(node)

    def insert_event(self, qname: QName, node: Event):
        leaf_table = self._leaf_table(qname.scope)
        name = qname.name.text
        if name not in leaf_table:
            sym = VarSymbol(name, SymbolType.Unknown, qname.name)
            leaf_table[name] = sym
        else:
            sym = leaf_table[name]
        sym.events.append(node)

    def insert_sboterm(self, qname: QName, node: Sboterm):
        leaf_table = self._leaf_table(qname.scope)
        name = qname.name.text
        if name not in leaf_table:
            sym = VarSymbol(name, SymbolType.Unknown, qname.name)
            leaf_table[name] = sym
        else:
            sym = leaf_table[name]
        sym.sboterms.append(node)
