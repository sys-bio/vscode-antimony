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
    # Use an in-memory document (avoid TemporaryFile which may expose numeric .name)
    ant_text = ant_str.get("ant_str")
    assert ant_text is not None, "There was an error converting the SBML file to Antimony"
    # Ensure ant_text is a str (antimony bindings may return bytes)
    if isinstance(ant_text, bytes):
        ant_text = ant_text.decode('utf-8', errors='replace')
    # Give the document a stable path-like name (pygls expects a string URI/path)
    doc = Document(os.path.abspath(f) + ".ant", ant_text)
    ant_file = api.AntFile(doc.path, doc.source)
    l_issues = ant_file.get_issues()
    error_count = 0
    for issue in l_issues:
        if str(issue.severity.__str__()) == 'IssueSeverity.Error':
            error_count += 1
    temp_ant_file.close()
    assert error_count == 0, "There were errors in the Antimony file"