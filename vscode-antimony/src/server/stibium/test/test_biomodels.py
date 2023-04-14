'Tests concerning checking for errors in models from biomodels feature.'

import json
from logging import debug

import pytest
from stibium import api
import os
from pygls.workspace import Document
from os import listdir
import antimony
import tempfile

# Change path later
path="/Users/evaliu02/Documents/vscode-antimony/vscode-antimony/src/server/stibium/test/biomodels"
bio_list = os.listdir(path)

def _get_antimony_str(sbml):
    if sbml is None:
        return {
            'error': 'Cannot open file'
        }
    antimony.clearPreviousLoads()
    antimony.freeAll()
    try:
        isfile = os.path.isfile(sbml)
    except ValueError:
        return {
            'error': 'Cannot open file'
        }
    if isfile:
        ant = antimony.loadSBMLFile(sbml)
        if ant < 0:
            return {
                'error': 'Antimony -  {}'.format(antimony.getLastError())
            }
        ant_str = antimony.getAntimonyString(None)
        return {
            'ant_str': ant_str
        }
    else:
        return {
            'error': 'Not a valid file'
        }

# TODO add more tests as more syntax features are added
@pytest.mark.parametrize('models', bio_list)
def test_all_biomodels(models):
    # store the data in a temp file or get the extracted SBML file and convert it to Antimony
    f = os.path.join(path + "/" + models)
    ant_str = _get_antimony_str(os.path.abspath(f))
    temp_ant_file = tempfile.TemporaryFile(mode='w+t', delete=True)
    temp_ant_file.write(ant_str.get('ant_str'))
    # xml_file = api.AntFile(doc.path, doc.source)
    l_issues = temp_ant_file.get_issues()
    temp_ant_file.close()
    assert l_issues == []