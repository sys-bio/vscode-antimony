'Tests concerning checking for errors in models from biomodels feature.'
import pytest
from stibium import api
import os
from pygls.workspace import Document
import antimony
import tempfile

directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'biomodels')
model_list = os.listdir(directory)

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

@pytest.mark.parametrize('models', model_list)
def test_all_biomodels(models):
    # store the data in a temp file or get the extracted SBML file and convert it to Antimony
    f = os.path.join(directory + "/" + models)
    ant_str = _get_antimony_str(os.path.abspath(f))
    temp_ant_file = tempfile.TemporaryFile(mode='w+t', delete=True, encoding='utf-8')
    assert ant_str.get("ant_str") is not None, "There was an error converting the SBML file to Antimony"
    temp_ant_file.write(ant_str.get('ant_str'))
    doc = Document(temp_ant_file.name, temp_ant_file.read())
    ant_file = api.AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    temp_ant_file.close()
    assert error_count == 0, "There were errors in the Antimony file"