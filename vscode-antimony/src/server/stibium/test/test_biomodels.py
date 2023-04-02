'Tests concerning checking for errors in models from biomodels feature.'

import json
from logging import debug
from stibium import api
from main import get_model
import os
from pygls.workspace import Document


# TODO add more tests as more syntax features are added
def test_all_biomodels():
    f = open('biomodels_list.json')
    models = json.load(f)
    for model in enumerate(models['models']):
        debug.log(model)
        get_model(model)
        f = os.path.join(model + '.ant')
        doc = Document(os.path.abspath(f))
        ant_file = api.AntFile(doc.path, doc.source)
        l_issues = ant_file.get_issues()
        if l_issues.__len__ > 0:
            assert(False)
        else:
            assert(True)