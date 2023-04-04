'Tests concerning checking for errors in models from biomodels feature.'

import json
from logging import debug
from stibium import api
import os
from pygls.workspace import Document
import pytest
import io
import requests
import zipfile

f = open('biomodels_list.json')
models = json.load(f)

def get_model(model: str):
    model_download_url = ("https://www.ebi.ac.uk/biomodels/search/download?models={model}").format(
        model=model
    )
    response = requests.get(model_download_url, stream=True)
    extract = zipfile.ZipFile(io.BytesIO(response.content))
    data = io.TextIOWrapper(extract.open(extract.namelist()[0]), encoding="utf-8", newline="").read()
    extract.close()
    return extract.namelist()[0], data

# TODO add more tests as more syntax features are added
@pytest.mark.parametrize('models', [models])
def test_all_biomodels():
    for model in models:
        debug.log(model)
        filename, cur_model = get_model(model)
        # store the data in a temp file or get the extracted SBML file and convert it to Antimony
        f = os.path.join(filename + '.ant')
        doc = Document(os.path.abspath(f))
        ant_file = api.AntFile(doc.path, doc.source)
        l_issues = ant_file.get_issues()
        assert l_issues == []