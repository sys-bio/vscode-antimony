from dataclasses import dataclass
from enum import Enum, auto
import logging
from typing import Union

from lark.lexer import Token
from lark.tree import Tree


class SrcPosition:
    '''A position in text; uses 1-based index.'''
    line: int
    column: int
    __slots__ = ['line', 'column']

    def __init__(self, line: int, column: int):
        self.line = line
        self.column = column

    def __repr__(self):
        return '{}:{}'.format(self.line, self.column)

    def __str__(self):
        return 'SrcPosition({}, {})'.format(self.line, self.column)

    def __eq__(self, other):
        if not isinstance(other, SrcPosition):
            return NotImplemented
        return self.line == other.line and self.column == other.column

    def __ge__(self, other):
        if self.line > other.line:
            return True
        if self.line == other.line:
            return self.column >= other.column
        return False

    def __gt__(self, other):
        if self.line > other.line:
            return True
        if self.line == other.line:
            return self.column > other.column
        return False

    def __le__(self, other):
        if self.line < other.line:
            return True
        if self.line == other.line:
            return self.column <= other.column
        return False

    def __lt__(self, other):
        if self.line < other.line:
            return True
        if self.line == other.line:
            return self.column < other.column
        return False
        

class SrcRange:
    '''A range in text; uses 1-based index.
    
    Attributes:
        start: Start position of the range
        end: End position of the range. This is exclusive, meaning that this is one column after
             the last position in the range.
    '''
    start: SrcPosition
    end: SrcPosition
    __slots__ = ['start', 'end']

    def __init__(self, start: SrcPosition, end: SrcPosition):
        self.start = start
        self.end = end

    def __eq__(self, other):
        if not isinstance(other, SrcRange):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __str__(self):
        return 'SrcRange({}, {})'.format(self.start, self.end)

    def __repr__(self):
        return '{} - {}'.format(self.start, self.end)


@dataclass
class SrcLocation:
    '''Absolute location -- including a file path and a range.'''
    path: str  # absolute file path
    range: SrcRange


ASTNode = Union[Tree, Token]


class IssueSeverity(Enum):
    Error = auto()  # semantic error; guaranteed to fail if passed to Tellurium
    Warning = auto()
    # TODO more


class Issue:
    def __init__(self, range_: SrcRange, severity: IssueSeverity):
        self.range = range_
        self.message = ''
        self.severity = severity

    def __str__(self):
        return self.message

    def __repr__(self):
        return "{}({}, {}, '{}')".format(self.severity.name, type(self).__name__, self.range,
                                         self.message)


class SyntaxErrorIssue(Issue):
    pass


class UnexpectedTokenIssue(SyntaxErrorIssue):
    def __init__(self, leaf_range: SrcRange, leaf_name: str):
        super().__init__(leaf_range, IssueSeverity.Error)
        self.message = "Unexpected token '{name}'".format(name=leaf_name)


class UnexpectedEOFIssue(SyntaxErrorIssue):
    '''Unexpected newline or EOF when we expected another token.'''
    def __init__(self, last_leaf_range: SrcRange):
        super().__init__(last_leaf_range, IssueSeverity.Error)
        self.message = "Expected a token"


class UnexpectedNewlineIssue(SyntaxErrorIssue):
    '''Unexpected newline or EOF when we expected another token.'''
    def __init__(self, leaf_pos: SrcPosition):
        leaf_range = SrcRange(leaf_pos, SrcPosition(leaf_pos.line + 1, 1))
        super().__init__(leaf_range, IssueSeverity.Error)
        self.message = "Expected a token"


class IncompatibleType(Issue):
    def __init__(self, old_type, old_range, new_type, new_range):
        super().__init__(new_range, IssueSeverity.Error)
        self.old_type = old_type
        self.old_range = old_range
        self.new_type = new_type
        self.new_range = new_range
        self.message = ("Unable to set the type to '{new_type}' because it is already set to be the incompatible type '{old_type}' on"
                        " line {old_line}:{old_column}").format(
            new_type=new_type,
            old_type=old_type,
            old_line=old_range.start.line,
            old_column=old_range.start.column,
        )

class RefUndefined(Issue):
    def __init__(self, range, val): 
        super().__init__(range, IssueSeverity.Error)
        self.val = val
        self.message = ("Parameter '{}' missing value assignment").format(val)

class SpeciesUndefined(Issue):
    def __init__(self, range, val): 
        super().__init__(range, IssueSeverity.Warning)
        self.val = val
        self.message = ("Species '{}' has not been initialized, using default value").format(val)

class UninitMModel(Issue):
    def __init__(self, range, val): 
        super().__init__(range, IssueSeverity.Error)
        self.val = val
        self.message = ("Modular model '{}' not defined").format(val)

class UninitFunction(Issue):
    def __init__(self, range, val): 
        super().__init__(range, IssueSeverity.Error)
        self.val = val
        self.message = ("Function '{}' not defined").format(val)

class UninitRateLaw(Issue):
    def __init__(self, range, val): 
        super().__init__(range, IssueSeverity.Warning)
        if val is None:
            val = ''
        self.val = val
        self.message = ("Reaction '{}' missing rate law").format(val)

class IncorrectParamNum(Issue):
    def __init__(self, range, val1, val2): 
        super().__init__(range, IssueSeverity.Error)
        self.message = ("Incorrect number of parameters, expected {}, given {}").format(val1, val2)

class ParamIncorrectType(Issue):
    def __init__(self, range, type1, type2):
        super().__init__(range, IssueSeverity.Error)
        self.message = ("Incorrect type being passed in, expected {}, given {}").format(type1, type2)

class UnusedParameter(Issue):
    def __init__(self, range, val): 
        super().__init__(range, IssueSeverity.Warning)
        self.val = val
        self.message = ("Parameter '{}' defined but not used").format(val)

class UninitCompt(Issue):
    def __init__(self, range, val):
        super().__init__(range, IssueSeverity.Warning)
        self.val = val
        self.message = ("Compartment '{}' has not been initialized, using default value").format(val)
        
class RateRuleNotInReaction(Issue):
     def __init__(self, range, val):
        super().__init__(range, IssueSeverity.Error)
        self.val = val
        self.message = f"Variable {val} is also a non-fixed species defined in a reaction"


class ObscuredEventTrigger(Issue):
    def __init__(self, old_range: SrcRange, new_range: SrcRange, name: str):
        super().__init__(old_range, IssueSeverity.Warning)
        self.old_range = old_range
        self.new_range = new_range
        self.name = name
        self.message = ("Event trigger '{name}' is being overridden by a declaration of the same name on "
                        "line {new_line}:{new_column}").format(
            name=name,
            new_line=new_range.start.line,
            new_column=new_range.start.column,
        )

class VarNotFound(Issue):
    def __init__(self, range, val): 
        super().__init__(range, IssueSeverity.Warning)
        self.val = val
        self.message = ("Variable '{}' not found").format(val)

class RateRuleOverRidden(Issue):
    def __init__(self, range, val, symbol): 
        super().__init__(range, IssueSeverity.Warning)
        self.val = val
        self.message = f"Previous Rate Rule {symbol.rate_rule} of {val} is overridden"


class ObscuredDeclaration(Issue):
    def __init__(self, old_range: SrcRange, new_range: SrcRange, name: str):
        super().__init__(old_range, IssueSeverity.Warning)
        self.old_range = old_range
        self.new_range = new_range
        self.name = name
        self.message = ("Declaration '{name}' is being overridden by a declaration of the same name on "
                        "line {new_line}:{new_column}").format(
            name=name,
            new_line=new_range.start.line,
            new_column=new_range.start.column,
        )

class ObscuredValue(Issue):
    def __init__(self, old_range: SrcRange, new_range: SrcRange, name: str):
        super().__init__(old_range, IssueSeverity.Warning)
        self.old_range = old_range
        self.new_range = new_range
        self.name = name
        self.message = ("Value assignment to '{name}' is being overridden by a later assignment on "
                        "line {new_line}:{new_column}").format(
            name=name,
            new_line=new_range.start.line,
            new_column=new_range.start.column,
        )

class OverridingDisplayName(Issue):
    def __init__(self, range: SrcRange, name: str):
        super().__init__(range, IssueSeverity.Warning)
        self.range = range
        self.name = name
        self.message = ("Name already assignment to '{name}'").format(
            name=name,
        )

class ObscuredValueCompartment(Issue):
    def __init__(self, old_range: SrcRange, new_range: SrcRange, name: str):
        super().__init__(old_range, IssueSeverity.Warning)
        self.old_range = old_range
        self.new_range = new_range
        self.name = name
        self.message = ("Compartment assignment to '{name}' is being overridden by a later assignment on "
                        "line {new_line}:{new_column}").format(
            name=name,
            new_line=new_range.start.line,
            new_column=new_range.start.column,
        )

class RedefinedFunction(Issue):
    def __init__(self, old_range, name, new_range):
        super().__init__(new_range, IssueSeverity.Error)
        self.old_range = old_range
        self.name = name
        self.new_range = new_range
        self.message = ("Cannot define '{name}' as a new function because it is already a defined function on"
                        "line {old_line}:{old_column}").format(
            name=name,
            old_line=old_range.start.line,
            old_column=old_range.start.column,
        )

class SubError(Issue):
    def __init__(self, range):
        super().__init__(range, IssueSeverity.Error)
        self.message = ("The substanceOnly keyword only works with species")


class OverrodeValue(Issue):
    def __init__(self, old_range: SrcRange, new_range: SrcRange, name: str):
        super().__init__(old_range, IssueSeverity.Warning)
        self.old_range = old_range
        self.new_range = new_range
        self.name = name
        self.message = ("Value assignment to '{name}' is overriding previous assignment on "
                        "line {new_line}:{new_column}").format(
            name=name,
            new_line=new_range.start.line,
            new_column=new_range.start.column,
        )

class NoImportFile(Issue):
    def __init__(self, range):
        super().__init__(range, IssueSeverity.Error)
        self.message = "File not found"

class GrammarHasIssues(Issue):
    def __init__(self, range, issues: list()):
        super().__init__(range, IssueSeverity.Error)
        issue_list = "The grammar contains issues, please fix before importing\n"
        for issue in issues:
            issue_list += "{}\n".format(issue)
        self.message = issue_list

class FileAlreadyImported(Issue):
    def __init__(self, range, file: str):
        super().__init__(range, IssueSeverity.Error)
        self.message = ("'{file}' has already been imported, please remove any extra "
                        "import statements for '{file}'").format(file=file)

class ModelAlreadyExists(Issue):
    def __init__(self, range, model: str):
        super().__init__(range, IssueSeverity.Error)
        self.message = ("Model '{}' is already defined, or there is a circular import").format(model)

class DuplicateImportedMModelCall(Issue):
    def __init__(self, range, mmodelcall: str):
        super().__init__(range, IssueSeverity.Error)
        self.message = ("The modular model call '{}' has been duplicated, please make sure "
                        "there is only one modular model call of this name").format(mmodelcall)

class CircularImportFound(Issue):
    def __init__(self, range):
        super().__init__(range, IssueSeverity.Error)
        self.message = "Circular import found"

class FunctionAlreadyExists(Issue):
    def __init__(self, range, function: str):
        super().__init__(range, IssueSeverity.Error)
        self.message = ("Function '{}' is already defined").format(function)

class ReservedName(Issue):
    def __init__(self, range, name: str):
        super().__init__(range, IssueSeverity.Error)
        self.message = ("Cannot use reserved name '{}'").format(name)

class AntimonySyntaxError(Exception):
    # TODO this is far from complete. To include: filename, possible token choices,
    # and possibly even parser state?
    def __init__(self, text: str, pos: SrcPosition, end_pos: SrcPosition=None):
        message = f"unexpected token '{text}' at {pos}"
        super().__init__(message)
        self.text = text
        self.pos = pos
        self.end_pos = end_pos


class SymbolType(Enum):
    Unknown = 'unknown'

    # Subtypes of UNKNOWN
    Variable = 'variable'
    Submodel = 'submodel'
    Model = 'model'
    Function = 'function'
    Unit = 'unit'
    ModularModel = 'mmodel'
    Import = 'import'

    # Subtype of VARIABLE. Also known as "formula"
    Parameter = 'parameter'

    # Subtypes of PARAMETER
    Species = 'species'
    Compartment = 'compartment'
    Reaction = 'reaction'
    Interaction = 'interaction'
    Event = 'event'
    Constraint = 'constraint'

    def __str__(self):
        return self.value

    def derives_from(self, other):
        if self == other:
            return True

        if other == SymbolType.Unknown:
            return True

        derives_from_param = self in (SymbolType.Species, SymbolType.Compartment,
                                      SymbolType.Reaction,
                                      SymbolType.Constraint)

        if other == SymbolType.Variable:
            return derives_from_param or self == SymbolType.Parameter

        if other == SymbolType.Parameter:
            return derives_from_param

        if self in (SymbolType.Species, SymbolType.Compartment,
                                      SymbolType.Reaction,
                                      SymbolType.Constraint,
                                      SymbolType.Parameter) and other not in (SymbolType.Species, 
                                      SymbolType.Compartment,
                                      SymbolType.Reaction,
                                      SymbolType.Constraint,
                                      SymbolType.Parameter):
            return False
        
        if other in (SymbolType.Species, SymbolType.Compartment,
                                      SymbolType.Reaction,
                                      SymbolType.Constraint,
                                      SymbolType.Parameter) and self not in (SymbolType.Species, 
                                      SymbolType.Compartment,
                                      SymbolType.Reaction,
                                      SymbolType.Constraint,
                                      SymbolType.Parameter):
            return False

        return False


class Variability(Enum):
    UNKNOWN = auto()
    CONSTANT = auto()
    VARIABLE = auto()
