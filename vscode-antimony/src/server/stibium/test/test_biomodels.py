'Tests concerning checking for errors in models from biomodels feature.'

import json
from logging import debug

import pytest
from stibium import api
import os
from pygls.workspace import Document
from os import listdir

path="/Users/evaliu/Documents/vscode-antimony/vscode-antimony/src/server/stibium/test/biomodels"
bio_list = os.listdir(path)

# TODO add more tests as more syntax features are added
@pytest.mark.parametrize('models', bio_list)
def test_all_biomodels(models):
    # store the data in a temp file or get the extracted SBML file and convert it to Antimony
    f = os.path.join(path + "/" + models)
    doc = Document(os.path.abspath(f))
    ant_file = api.AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    assert l_issues == []