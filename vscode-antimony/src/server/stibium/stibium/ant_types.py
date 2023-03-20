import abc
from ast import Expression
from dataclasses import dataclass, field
import logging
from typing import List, Optional, Tuple, Union, cast
from lark.lexer import Token
from lark.tree import Tree

from stibium.types import SrcRange, SymbolType, Variability

vscode_logger = logging.getLogger("vscode logger: ")

class TreeNode(abc.ABC):
    '''Basically either a TrunkNode or a LeafNode.
    This is not a dataclass to avoid inheritance issues. The attributes are there for static
    analysis.
    '''
    range: SrcRange
    parent: Optional['TrunkNode']

    def scan_leaves(self):
        '''Return all the leaf nodes that are descendants of this node (possibly including self)'''
        for leaf in _scan_leaves(self):
            yield leaf

    def next_sibling(self):
        if self.parent is None:
            return None

        for index, node in enumerate(self.parent.children):
            if node is self:
                if index == len(self.parent.children) - 1:
                    return None
                return self.parent.children[index + 1]
        return None

    def check_rep(self):
        pass


@dataclass
class TrunkNode(TreeNode):
    range: SrcRange
    children: Tuple[Optional['TreeNode'], ...] = field(repr=False)
    parent: Optional['TrunkNode'] = field(default=None, compare=False, repr=False)

    def descendants(self):
        '''Iterate over all descendants, including self and the None nodes.'''
        yield self
        for child in self.children:
            if child is not None:
                # if isinstance(child, LeafNode):
                # faster than isinstance
                if not hasattr(child, 'children'):
                    yield child
                else:
                    child = cast(TrunkNode, child)
                    for desc in child.descendants():
                        yield desc

    def last_leaf(self):
        for child in reversed(self.children):
            if child is None:
                continue
            if isinstance(child, LeafNode):
                return child

            assert isinstance(child, TrunkNode)
            ret = child.last_leaf()
            if ret is not None:
                return ret

        return None

@dataclass
class LeafNode(TreeNode):
    range: SrcRange
    text: str
    parent: Optional['TrunkNode'] = field(default=None, compare=False, repr=False)
    prev: Optional['LeafNode'] = field(default=None, compare=False, repr=False)
    next: Optional['LeafNode'] = field(default=None, compare=False, repr=False)


def _scan_leaves(node: TreeNode):
    # using this instead of isinstance() for performance
    if isinstance(node, FuncCall):
        yield node
    elif hasattr(node, 'children'):
        node = cast(TrunkNode, node)
        for child in node.children:
            if child is not None:
                for leaf in _scan_leaves(child):
                    yield leaf
    else:
        # assert isinstance(node, LeafNode)
        yield node


# NOTE don't subclass this because we are using type(...) == ErrorNode instead of isinstance() for
# performance reasons
@dataclass
class ErrorNode(TrunkNode):
    '''ErrorNode is a tree of tokens that appear before an unexpected token (ErrorToken).

    In particular, if the tokens that appeared before the ErrorToken have not been able to form
    a statement yet, they would be collected into an ErrorNode. For example in a =?, 'a =' forms
    an error node, but in 'a = 5;?', there is no error node, since 'a = 5;' forms a complete
    statement, and we don't need to handle any dangling tokens before '?'.
    
    The error node does not have to contain only leaf nodes. It contains the best guess of the
    parser at that point, so one may see full nodes (e.g. NameMaybeIn) if there is no ambiguity
    at that point.
    '''
    pass


# NOTE don't subclass this because we are using type(...) == ErrorToken instead of isinstance() for
# performance reasons
@dataclass
class ErrorToken(LeafNode):
    pass


class ArithmeticExpr(TreeNode):
    '''Base class for arithmetic expressions.'''
    pass

@dataclass
class Sum(ArithmeticExpr, TrunkNode):
    '''Arithmetic expression with an addition/subtraction root operator.'''
    def to_string(self) -> str:
        ret = ''
        if isinstance(self, LeafNode):
            ret += self.text
        else:
            for node in self.descendants():
                if isinstance(node, LeafNode):
                    ret += node.text
        return ret
    
@dataclass
class Expressions(Sum, TrunkNode):
    '''Base class for equalities and inequalities.'''
    pass

class BooleanExpr(Expressions, TreeNode):
    '''Base class for boolean expressions.'''
    pass


@dataclass
class Product(ArithmeticExpr, TrunkNode):
    '''Arithmetic expression with a multiplication/division root operator.'''
    def to_string(self) -> str:
        ret = ''
        if isinstance(self, LeafNode):
            ret += self.text
        else:
            for node in self.descendants():
                if isinstance(node, LeafNode):
                    ret += node.text
        return ret


@dataclass
class Power(ArithmeticExpr, TrunkNode):
    '''Arithmetic expression with a power root operator.'''
    pass


# @dataclass
# class Negation(ArithmeticExpr, TrunkNode):
#     '''Arithmetic expression that represents a negation'''
#     children: Tuple['Operator', 'Atom'] = field(repr=False)


@dataclass
class Atom(TrunkNode, ArithmeticExpr):
    '''Atomic arithmetic expression.'''
    children: Tuple['Operator', Union[ArithmeticExpr, 'Number', 'VarName'], 'Operator'] = field(repr=False)
    # TODO also possible that children be '-' 'number' or '+' 'name', etc. Possibly create a new
    # rule called Factor that handles that?


# NOTE don't subclass this because we are using type(...) == Name instead of isinstance() for
# performance reasons
class Name(LeafNode):
    def check_rep(self):
        assert bool(self.text)

    def __eq__(self, other):
        return self.text == other.text
    
    def __hash__(self):
        return hash(self.text)

class EscapedString(LeafNode):
    pass

class Number(LeafNode, ArithmeticExpr):
    def get_value(self):
        return float(self.text)
    
    def check_rep(self):
        self.get_value()


@dataclass
class Operator(LeafNode):
    pass


@dataclass
class Boolean(TrunkNode):
    children: Tuple[Operator] = field(repr=False)
    def get_bool(self):
        return self.children[0].text


@dataclass
class CompareSign(TrunkNode):
    children: Tuple[Operator] = field(repr=False)
    def get_sign(self):
        return self.children[0].text


@dataclass
class Parenthesis(TrunkNode):
    children: Tuple[Operator] = field(repr=False)
    def get_paren(self):
        return self.children[0].text


@dataclass
class Logical(TrunkNode):
    children: Tuple[Operator] = field(repr=False)
    def get_logic_symbol(self):
        return self.children[0].text


@dataclass
class Keyword(LeafNode):
    def get_str(self):
        return self.text[1:-1]


@dataclass
class StringLiteral(LeafNode):
    def get_str(self):
        '''Get the string within the quotes.'''
        return self.text[1:-1]
    
@dataclass
class Sbo(LeafNode):
    pass


# NOTE for now, the EOF is constructed as a Newline with text being an empty string. In the future,
# we may want to add a special EOF class
@dataclass
class Newline(LeafNode):
    pass


@dataclass
class VarName(TrunkNode):
    children: Tuple[Optional[Operator], Name] = field(repr=False)

    def is_const(self):
        return self.children[0] is not None

    def get_name(self):
        return self.children[1]

    def get_name_text(self):
        return self.children[1].text


# NOTE don't subclass this because we are using type(...) == InComp instead of isinstance() for
# performance reasons
@dataclass
class InComp(TrunkNode):
    children: Tuple[Keyword, VarName] = field(repr=False)

    def get_comp(self) -> VarName:
        return self.children[1]


@dataclass
class NameMaybeIn(TrunkNode):
    children: Tuple[VarName, Optional[InComp]] = field(repr=False)

    def get_var_name(self):
        return self.children[0]
    
    def is_in_comp(self):
        return self.children[1] is not None

    def get_comp(self):
        if self.is_in_comp():
            return self.children[1].get_comp()
        else:
            return None


# # TODO move this to another class, e.g. logical/model types
# # TODO create new classes Name and Node to replace Token and Tree
# @dataclass
# class Species:
#     stoich: float
#     name: Token


@dataclass
class Species(TrunkNode):
    children: Tuple[Optional[Number], Optional[Operator], Name] = field(repr=False)
    
    def get_stoich(self):
        if self.children[0] is None:
            return 1

        return self.children[0].get_value()

    def is_const(self):
        return bool(self.children[1])

    def get_name(self):
        return self.children[2]

    def get_name_text(self):
        return self.get_name().text


@dataclass
class ReactionName(TrunkNode):
    '''Represents the 'J0:' at the start of the reaction.'''
    children: Tuple[NameMaybeIn, Operator] = field(repr=False)

    def get_maybein(self):
        return self.children[0]

    def get_name(self):
        return self.get_maybein().get_var_name().get_name()

    def get_name_text(self):
        return self.get_maybein().get_var_name().get_name_text()


@dataclass
class SpeciesList(TrunkNode):
    def get_all_species(self) -> List[Species]:
        return cast(List[Species], self.children[::2])

    def check_rep(self):
        assert len(self.children) == 0 or len(self.children) % 2 == 1
        for child in self.children[::2]:
            assert isinstance(child, Species)
        for child in self.children[1::2]:
            assert isinstance(child, LeafNode) and child.text == '+'


@dataclass
class Reaction(TrunkNode):
    children: Tuple[Optional[ReactionName], SpeciesList, Operator, SpeciesList, Operator,
                    Optional[ArithmeticExpr], Optional[InComp]] = field(repr=False)

    def get_maybein(self):
        if self.children[0] is None:
            return None
        return self.children[0].get_maybein()

    def get_name(self):
        if self.children[0] is None:
            return None
        return self.children[0].get_name()

    def get_name_text(self):
        if self.children[0] is None:
            return None
        return self.children[0].get_name_text()

    def get_reactant_list(self) -> Optional[SpeciesList]:
        return self.children[1]

    def get_product_list(self) -> Optional[SpeciesList]:
        return self.children[3]
    
    def get_reactant_product_num(self) -> str:
        '''
        get the number of reactant and product in a reaction, return in string form:
        for example, a reaction with one reactant and two products will return '12'
        '''
        return '' + str(len(self.get_reactants())) + str(len(self.get_products()))

    def get_reactants(self) -> List[Species]:
        slist = self.get_reactant_list()
        if slist:
            return slist.get_all_species()
        return list()

    def get_products(self) -> List[Species]:
        slist = self.get_product_list()
        if slist:
            return slist.get_all_species()
        return list()

    def get_rate_law(self):
        if self.children[5] is not None:
            return self.children[5]
        return None

    def is_reversible(self):
        assert self.children[2].text in ('->', '=>')
        return self.children[2].text == '->'
    
    def get_comp(self):
        if self.children[6] is not None:
            return self.children[6]
        return None
    
@dataclass
class InteractionName(TrunkNode):
    children: Tuple[NameMaybeIn, Operator] = field(repr=False)

    def get_maybein(self):
        return self.children[0]

    def get_name(self):
        return self.get_maybein().get_var_name().get_name()

    def get_name_text(self):
        return self.get_maybein().get_var_name().get_name_text()

@dataclass 
class Interaction(TrunkNode):
    children: Tuple[InteractionName, Species, Operator, NameMaybeIn] = field(repr=False)

    def get_name(self):
        return self.children[0]

    def get_opr(self):
        return self.children[2]

    def get_species(self):
        return self.children[1]

    def get_reaction_namemaybein(self) -> NameMaybeIn:
        return self.children[3]

@dataclass
class ParenthesisList(TrunkNode):
    def get_all_parens(self) -> List[Parenthesis]:
        return cast(List[Parenthesis], self.children)
    
    def to_string(self):
        ret = ''
        for paren in self.get_all_parens():
            ret += paren.get_paren()
        return ret

    def check_rep(self):
        for child in self.children:
            assert isinstance(child, Parenthesis)
            assert child.text == '(' or child.text == ')'
            
@dataclass
class EventDelay(TrunkNode):
    children: Tuple[Union[BooleanExpr, VarName], Keyword] = field(repr=False)
    
    def get_expr(self):
        return self.children[0]
    
    def get_sum_text(self):
        ret = ''
        delay = self.get_sum()
        if isinstance(delay, LeafNode):
            ret += delay.text
        else:
            ret += delay.to_string()
        ret += ' after'
        return ret
    
@dataclass
class EventTrigger(TrunkNode):
    children: Tuple[Keyword, Operator, Union[Boolean, Sum, Number]] = field(repr=False)
    def get_keyword(self):
        return self.children[0]
    
    def get_trigger(self):
        return self.children[2]
    
    def get_trigger_str(self):
        if isinstance(self.get_trigger(), Boolean):
            return self.get_trigger().get_bool()
        elif isinstance(self.get_trigger(), Sum):
            return self.get_trigger().to_string()
        elif isinstance(self.get_trigger(), LeafNode):
            return self.get_trigger().text
    
    def to_string(self):
        return self.children[0].text + ' = ' + self.get_trigger_str()
        
    
@dataclass
class EventTriggerList(TrunkNode):
    def get_all_triggers(self) -> List[EventTrigger]:
        return cast(List[EventTrigger], self.children[1::2])
    
    def get_triggers(self):
        ret = dict()
        for trigger in self.get_all_triggers():
            ret[trigger.get_keyword().text] = trigger.get_trigger_str()
        return ret
        
    
@dataclass
class EventAssignment(TrunkNode):
    children: Tuple[VarName, Operator, Sum] = field(repr=False)
    def get_var_name(self):
        return self.children[0]
    
    def get_name(self):
        return self.get_var_name().get_name()
        
    def get_name_text(self):
        return self.get_var_name().get_name_text()
    
    def get_value(self):
        return self.children[2]

    def get_type(self):
        return self.unit
    
@dataclass
class EventAssignmentList(TrunkNode):
    def get_all_event_assignments(self) -> List[EventAssignment]:
        return cast(List[EventAssignment], self.children[::2])

@dataclass
class Event(TrunkNode):
    children: Tuple[Optional[ReactionName], Keyword, Optional[EventDelay],
                    BooleanExpr, Optional[EventTriggerList],
                    Operator, EventAssignmentList] = field(repr=False)
    unnamed_label : int = -1
    def get_maybein(self):
        if self.children[0] is None:
            return None
        return self.children[0].get_maybein()

    def get_name(self):
        if self.children[0] is None:
            return None
        return self.children[0].get_name()

    def get_name_text(self):
        if self.children[0] is None:
            return None
        return self.children[0].get_name_text()
    
    def get_event_delay(self):
        return self.children[2]
    
    def get_event_delay_text(self) -> str:
        if self.get_event_delay() is not None:
            return self.get_event_delay().get_sum_text()
        return None
        
    def get_condition(self) -> BooleanExpr:
        return self.children[3]

    def get_trigger_list(self) -> Optional[EventTriggerList]:
        return self.children[4]

    def get_triggers(self) -> List[EventTrigger]:
        slist = self.get_trigger_list()
        if slist:
            return slist.get_all_triggers()
        return list()
    
    def get_assignment_list(self):
        return self.children[6]
    
    def get_assignments(self) -> List[EventAssignment]:
        slist = self.get_assignment_list()
        return slist.get_all_event_assignments()

@dataclass
class Assignment(TrunkNode):
    unit: Sum = None
    children: Tuple[NameMaybeIn, Operator, ArithmeticExpr] = field(repr=False)

    def get_maybein(self):
        return self.children[0]

    def get_name(self):
        return self.get_maybein().get_var_name().get_name()

    def get_name_text(self):
        return self.get_maybein().get_var_name().get_name_text()

    def get_value(self):
        return self.children[2]

    def get_type(self):
        return self.unit

@dataclass
class RateRules(TrunkNode):
    children: Tuple[Name, Operator, Operator, ArithmeticExpr] = field(repr=False)

    def get_name(self):
        return self.children[0]
    
    def get_value(self):
        return self.children[3]


@dataclass
class VarModifier(Keyword):
    # text: Union[Literal['const'], Literal['var']]
    pass


@dataclass
class TypeModifier(Keyword):
    # text: Union[Literal['species'], Literal['compartment'], Literal['formula']]
    pass

@dataclass
class SubModifier(Keyword):
    pass


@dataclass
class DeclModifiers(TrunkNode):
    '''Represents the prefix modifiers to a declaration.
    
    Note that this is special in that the Lark parse tree, this node may have one or two children.
    But here it always has two: [DeclVarModifier, DeclTypeModifier]. At most one of those may be
    None.
    '''
    children: Tuple[Optional[VarModifier], Optional[SubModifier], Optional[TypeModifier]] = field(repr=False)

    def get_var_modifier(self):
        return self.children[0]

    def get_sub_modifier(self):
        return self.children[1]

    def get_type_modifier(self):
        return self.children[2]

    def get_variab(self):
        var_mod = self.get_var_modifier()
        if var_mod is None:
            return Variability.UNKNOWN
        return Variability.CONSTANT if var_mod.text == 'const' else Variability.VARIABLE

    def get_type(self):
        type_mod = self.get_type_modifier()
        if type_mod is None:
            return SymbolType.Unknown

        return {
            'species': SymbolType.Species,
            'compartment': SymbolType.Compartment,
            'formula': SymbolType.Parameter,
        }[type_mod.text]

    def check_rep(self):
        assert bool(self.children[0]) or bool(self.children[1])


@dataclass
class DeclAssignment(TrunkNode):
    unit: Sum = None
    children: Tuple[Operator, ArithmeticExpr] = field(repr=False)

    def get_value(self):
        return self.children[1]

    def get_type(self):
        return self.unit


@dataclass
class DeclItem(TrunkNode):
    children: Tuple[NameMaybeIn, DeclAssignment] = field(repr=False)

    def get_maybein(self):
        return self.children[0]

    def get_decl_assignment(self):
        return self.children[1]

    def get_name(self):
        return self.get_maybein().get_var_name().get_name()

    def get_name_text(self):
        return self.get_maybein().get_var_name().get_name_text()

    def get_value(self):
        node = self.get_decl_assignment()
        if node is None:
            return None
        return node.get_value()


@dataclass
class Declaration(TrunkNode):
    def get_modifiers(self):
        return cast(DeclModifiers, self.children[0])

    def get_items(self):
        items = self.children[1::2]
        return cast(List[DeclItem], items)

    def check_rep(self):
        assert len(self.children) >= 3
        assert isinstance(self.children[0], DeclModifiers)
        assert isinstance(self.children[1], DeclItem)
        assert isinstance(self.children[2], Operator)



# TODO All below
@dataclass
class NewAnnotation(TrunkNode):
    children: Tuple[Operator, Newline, StringLiteral] = field(repr=False)

    def get_uri(self):
        return self.children[2]

@dataclass
class Annotation(TrunkNode):
    children: Tuple[VarName, Keyword, StringLiteral, Optional[List[NewAnnotation]]]

    def get_var_name(self):
        return self.children[0]

    def get_name_text(self):
        return self.get_var_name().get_name_text()

    def get_keyword(self):
        return self.children[1].text

    def get_uri(self):
        alist = self.children[3]
        if alist:
            #for annot in alist:
            vscode_logger.info(alist.get_uri())
        vscode_logger.info("this is: ")
        vscode_logger.info(alist)
        return self.children[2].get_str()


    
@dataclass
class Sboterm(TrunkNode):
    children: Tuple[VarName, Keyword, Operator, Number]
    
    def get_var_name(self):
        return self.children[0]

    def get_name_text(self):
        return self.get_var_name().get_name_text()

    def get_keyword(self):
        return self.children[1].text[1:]

    def get_val(self):
        return self.children[3].text

@dataclass
class UnitDeclaration(TrunkNode):
    children: Tuple[Keyword, VarName, Operator, Sum] = field(repr=False)

    def get_var_name(self):
        return self.children[1]
    
    def get_sum(self):
        return self.children[3]

@dataclass
class UnitAssignment(TrunkNode):
    children: Tuple[VarName, Keyword, Sum] = field(repr=False)

    def get_var_name(self):
        return self.children[0]
    
    def get_sum(self):
        return self.children[2]

@dataclass
class VariableIn(TrunkNode):
    children: Tuple[VarName, InComp] = field(repr=False)

    def get_name(self):
        return self.children[0]
    
    def get_incomp(self):
        return self.children[1]

@dataclass
class IsAssignment(TrunkNode):
    children: Tuple[VarName, Keyword, EscapedString] = field(repr=False)

    def get_var_name(self):
        return self.children[0]
    
    def get_display_name(self):
        return self.children[2]

@dataclass
class Import(TrunkNode):
    children: Tuple[Keyword, StringLiteral] = field(repr=False)
    
    def get_file_name(self):
        return self.children[1]
    
    def get_file(self):
        from stibium.utils import get_file_info
        file_str = get_file_info(self.get_file_name().get_str())
        return file_str

@dataclass
class SimpleStmt(TrunkNode):
    children: Tuple[Union[IsAssignment, Reaction, Assignment, Declaration, Annotation, Sboterm, UnitDeclaration, UnitAssignment, VariableIn, Import, RateRules, Event], Union[Operator, Newline]] = field(repr=False)

    def get_stmt(self):
        return self.children[0]


@dataclass
class SimpleStmtList(TrunkNode):
    children: Tuple[SimpleStmt, ...] = field(repr=False)

@dataclass
class Model(TrunkNode):
    children: Tuple[Keyword, VarName, SimpleStmtList, Keyword] = field(repr=False)

    def get_name(self):
        return self.children[1]
    
    def get_stmt_list(self):
        return self.children[2]

@dataclass
class Parameters(TrunkNode):

    def get_items(self):
        items = self.children[0::2]
        return cast(List[Name], items)

@dataclass
class ModularModel(TrunkNode):
    children: Tuple[Keyword, Optional[Operator], VarName, Operator, Optional[Parameters], Operator, 
                    SimpleStmtList, Keyword] = field(repr=False)

    def get_name(self):
        return self.children[2]

    def get_name_str(self):
        return self.children[2].text

    def get_params(self):
        return self.children[4]
    
    def get_stmt_list(self):
        return self.children[6]

@dataclass
class ModularModelCall(TrunkNode):
    children: Tuple[Optional[ReactionName], VarName, Operator, 
                Optional[Parameters], Operator] = field(repr=False)
    
    def get_maybein(self):
        if self.children[0] is None:
            return None
        return self.children[0].get_maybein()

    def get_name(self):
        if self.children[0] is None:
            return None
        return self.children[0].get_name()
    
    def get_mmodel_name(self):
        return self.children[1]
    
    def get_mmodel_name_str(self):
        return self.children[1].text

    def get_params(self):
        return self.children[3]
    
    def get_value(self):
        return None

@dataclass
class Function(TrunkNode):
    children: Tuple[Keyword, VarName, Operator, Optional[Parameters], Operator, Newline, 
                    ArithmeticExpr, Optional[Operator], Keyword] = field(repr=False)

    def get_name(self):
        return self.children[1]
    
    def get_name_str(self):
        return self.children[1].text
    
    def get_params(self):
        return self.children[3]
    
    def get_expr(self):
        return self.children[6]

@dataclass
class FunctionCall(TrunkNode):
    children: Tuple[NameMaybeIn, Operator, VarName, Operator, 
                Optional[Parameters], Operator] = field(repr=False)
    
    def get_maybein(self):
        return self.children[0]

    def get_name(self):
        return self.get_maybein().get_var_name().get_name()
    
    def get_function_name(self):
        return self.children[2]
    
    def get_function_name_str(self):
        return self.children[2].text

    def get_params(self):
        return self.children[4]
    
    def get_value(self):
        return None
    
@dataclass
class FuncCall(TrunkNode):
    children: Tuple[VarName, Operator, Optional[Parameters], Operator] = field(repr=False)

    def get_function_name(self):
        return self.children[0]
    
    def get_params(self):
        return self.children[2]

# Unit
@dataclass
class BuiltinUnit(TrunkNode):
    pass

@dataclass
class End(LeafNode):
    pass

@dataclass
class FileNode(TrunkNode):
    children: Tuple[SimpleStmt, ...] = field(repr=False)
