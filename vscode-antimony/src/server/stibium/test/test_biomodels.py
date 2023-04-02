'Tests concerning checking for errors in models from biomodels feature.'

import json
from logging import debug
from stibium import api
from main import get_model
import os
from pygls.workspace import Document
import pytest

f = open('biomodels_list.json')
models = json.load(f)


# TODO add more tests as more syntax features are added
@pytest.mark.parametrize('models', [models])
def test_all_biomodels():
    for model in models:
        debug.log(model)
        get_model(model)
        f = os.path.join(model + '.ant')
        doc = Document(os.path.abspath(f))
        ant_file = api.AntFile(doc.path, doc.source)
        l_issues = ant_file.get_issues()
        assert l_issues == []