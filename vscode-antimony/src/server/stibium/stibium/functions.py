
BUILT_IN_FUNCS = {
    "abs": [1],
    "acos": [1],
    "arccos": [1],
    "acosh": [1],
    "arccosh": [1],
    "acot": [1],
    "arccot": [1],
    "acoth": [1],
    "arccoth": [1],
    "acsc": [1],
    "arccsc": [1],
    "acsch": [1],
    "arccsch": [1],
    "asec": [1],
    "arcsec": [1],
    "asech": [1],
    "arcsech": [1],
    "asin": [1],
    "arcsin": [1],
    "asinh": [1],
    "arcsinh": [1],
    "atan": [1],
    "arctan": [1],
    "atanh": [1],
    "arctanh": [1],
    "ceil": [1],
    "ceiling": [1],
    "cos": [1],
    "cosh": [1],
    "cot": [1],
    "coth": [1],
    "csc": [1],
    "csch": [1],
    "exp": [1],
    "factorial": [1],
    "floor": [1],
    "ln": [1],
    "not": [1],
    "sec": [1],
    "sech": [1],
    "sin": [1],
    "sinh": [1],
    "tan": [1],
    "tanh": [1],
    "divide": [2],
    "delay": [2],
    "log": [2],
    "log[1]0": [2],
    "power": [2],
    "pow": [2],
    "sqr": [2],
    "neq": [2],
}

NOT_ARG_COUNTS = {
    "equals": [0, 1], # cannot be 0 or 1
    "eq": [0, 1], # cannot be 0 or 1
    "geq": [0, 1], # cannot be 0 or 1
    "gt": [0, 1], # cannot be 0 or 1
    "leq": [0, 1], # cannot be 0 or 1
    "lt": [0, 1], # cannot be 0 or 1
    "lambda": [0], # cannot be 0
    "piecewise": [0], # cannot be 0
}

ANY_ARG_COUNTS = {
    "times": [], # can have any number of arguments
    "plus": [], # can have any number of arguments
    "and": [], # can have any number of arguments
    "or": [], # can have any number of arguments
    "xor": [], # can have any number of arguments
}

TWO_ARG_COUNTS = {
    "minus": [1, 2], # can only be 1 or 2
    "sqrt": [1, 2], # can only be 1 or 2
    "root": [1, 2], # can only be 1 or 2
}

def is_builtin_func(func_name):
    return func_name if func_name in BUILT_IN_FUNCS or NOT_ARG_COUNTS else ""

def has_correct_args(func_name, num_args):
    if func_name not in BUILT_IN_FUNCS and func_name not in NOT_ARG_COUNTS \
        and func_name not in ANY_ARG_COUNTS and func_name not in TWO_ARG_COUNTS:
        return False

    if func_name in BUILT_IN_FUNCS:
        return num_args in BUILT_IN_FUNCS[func_name]
    elif func_name in NOT_ARG_COUNTS:
        return num_args not in NOT_ARG_COUNTS[func_name]
    elif func_name in ANY_ARG_COUNTS:
        return True
    elif func_name in TWO_ARG_COUNTS:
        return num_args in TWO_ARG_COUNTS[func_name]

def get_builtin_func_arg_counts(func_name):
    if func_name not in BUILT_IN_FUNCS and func_name not in NOT_ARG_COUNTS \
        and func_name not in ANY_ARG_COUNTS and func_name not in TWO_ARG_COUNTS:
        return []
    
    if func_name in BUILT_IN_FUNCS:
        return BUILT_IN_FUNCS[func_name][0]
    
    if func_name in NOT_ARG_COUNTS:
        if len(NOT_ARG_COUNTS[func_name]) == 1:
            return "> 0"
        return "> 1"
    
    if func_name in TWO_ARG_COUNTS:
        return "{} or {}".format(TWO_ARG_COUNTS[func_name][0], TWO_ARG_COUNTS[func_name][1])
