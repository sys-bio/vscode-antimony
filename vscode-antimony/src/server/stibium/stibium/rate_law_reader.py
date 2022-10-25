import os
import orjson
from stibium.ant_types import SimpleStmt, Reaction
from stibium.parse import AntimonyParser


class RateLawReader:
    def __init__(self, text: str):
        '''
        :param text: The reaction string
        self.reactant_product_num = '_error' the text given is not a reaction
        '''
        self.relevant_rate_laws = list()
        parser = AntimonyParser()
        tree = parser.parse(text, recoverable=True)
        self.reactant_product_num = '_error'
        self.reaction = None
        for child in tree.children:
            if isinstance(child, SimpleStmt):
                stmt = child.get_stmt()
                if stmt is None:
                    continue
                if stmt.__class__.__name__ == 'Reaction':
                    self.reactant_product_num = stmt.get_reactant_product_num()
                    self.reaction = stmt
                    break
        if self.reaction is not None:
            f = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.json"), "r")
            data = f.read()
            rate_laws = orjson.loads(data)
            reversibility = 'Irreversible'
            if self.reaction.is_reversible():
                reversibility = 'Reversible'
            for rate_law in rate_laws['rateml']['listOfRateLaws']['law']:
                substrate_product_num = ''
                substrate_product_num += rate_law['_numSubstrates'] + rate_law['_numProducts']
                if substrate_product_num == self.reactant_product_num and reversibility in rate_law['_property']:
                    constants = list()
                    for constant_item in rate_law['listOfParameters']['parameter']:
                        constants.append({'name': constant_item['_name'], 'description': constant_item['_description']})
                    expression = substitute_rate_law_participants(rate_law['_infixExpression'], self.reaction)
                    expression = create_snippet(expression, constants)
                    self.relevant_rate_laws.append({
                        'name': rate_law['_displayName'].strip(),
                        'orig_expr': rate_law['_infixExpression'],
                        'expression': expression,
                        'latex': rate_law['_display'],
                        'constants': constants,
                    })

    def no_rate_law_check(self):
        '''
        check if there is no rate law exist
        '''
        assert isinstance(self.reaction, Reaction)
        if self.reaction.get_rate_law():
            return '_error'
        return 'correct'
    
def substitute_rate_law_participants(rate_law_str: str, reaction: Reaction):
    '''
    substitute a raw rate law string with a reaction
    '''
    indicator = 1
    for substrate in reaction.get_reactants():
        rate_law_str = rate_law_str.replace('___S' + str(indicator) + '___', substrate.get_name_text())
        indicator += 1
    indicator = 1
    for product in reaction.get_products():
        rate_law_str = rate_law_str.replace('___P' + str(indicator) + '___', product.get_name_text())
        indicator += 1
    return rate_law_str

def create_snippet(rate_law_str: str, constants: list):
    '''
    create the snippet string for a rate law
    '''
    indicator = 1
    for constant in constants:
        rate_law_str = rate_law_str.replace(constant['name'], '${' + str(indicator) + ':' + constant['name'] + '}')
        indicator += 1
    return rate_law_str