"""Temporary single-file server implementation.
Author: Gary Geng, Steve Ma
"""
import os
import sys
import logging


EXTENSION_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(EXTENSION_ROOT, "..", "pythonFiles", "lib", "python"))

import antimony

sys.path.append(os.path.join(EXTENSION_ROOT, "server", "stibium"))

from stibium.api import AntCompletion, AntCompletionKind
from stibium.types import Issue, IssueSeverity
from stibium.symbols import FuncSymbol, AbstractScope, BaseScope, QName, SymbolTable
from stibium.ant_types import Name

from bioservices_server.utils import AntFile, pygls_range, sb_position, get_antfile, sb_range
from bioservices_server.webservices import NetworkError, WebServices

from dataclasses import dataclass
from pygls.features import (CODE_LENS, COMPLETION, DEFINITION, HOVER, SIGNATURE_HELP, TEXT_DOCUMENT_DID_CHANGE,
                            TEXT_DOCUMENT_DID_OPEN, TEXT_DOCUMENT_DID_SAVE, WORKSPACE_EXECUTE_COMMAND)
from pygls.server import LanguageServer
from pygls.types import (CompletionItem, CompletionItemKind, CompletionList, CompletionParams, Diagnostic, DiagnosticSeverity,
                         DidChangeTextDocumentParams,
                         DidOpenTextDocumentParams, DidSaveTextDocumentParams, Hover, InsertTextFormat, Location, MarkupContent, MarkupKind,
                         TextDocumentContentChangeEvent, TextDocumentPositionParams)
import threading
import time

# TODO remove this for production
logging.basicConfig(filename='vscode-antimony-dep.log', filemode='w', level=logging.DEBUG)
vscode_logger = logging.getLogger("vscode-antimony logger")
vscode_logger.addHandler(logging.FileHandler('vscode-antimony-ext.log', mode="w"))

server = LanguageServer()
services = WebServices()

antfile_cache = None
uri = None


#### Annotations ####
@server.command('antimony.getAnnotated')
def get_annotated(ls: LanguageServer, args):
    '''Return the list of annotated names as ranges'''
    text = args[0]
    antfile = AntFile('', text)
    qnames = antfile.analyzer.table.get_all_qnames()
    annotated = [q for q in qnames if antfile.get_annotations(q)]
    ranges = [pygls_range(a.name.range) for a in annotated]
    range_objs = [
        {
            'line': r.start.line,
            'column': r.start.character,
            'end_line': r.end.line,
            'end_column': r.end.character,
            } for r in ranges
    ]
    return range_objs

@server.thread()
@server.command('antimony.antFiletoSBMLFile')
def ant_file_to_sbml_file(ls: LanguageServer, args):
    ant = args[0].fileName
    output_dir = args[1]
    sbml_str = _get_sbml_str(ant)
    if 'error' in sbml_str:
        return sbml_str
    else:
        model_name = os.path.basename(ant)
        full_path_name = os.path.join(output_dir, os.path.splitext(model_name)[0]+'.xml')
        with open(full_path_name, 'w') as f:
            f.write(sbml_str['sbml_str'])
        return {
            'msg': 'SBML has been exported to {}'.format(output_dir),
            'file': full_path_name
        }

@server.thread()
@server.command('antimony.antFileToSBMLStr')
def ant_file_to_sbml_str(ls: LanguageServer, args):
    ant = args[0].fileName
    sbml_str = _get_sbml_str(ant)
    return sbml_str

@server.thread()
@server.command('antimony.antStrToSBMLStr')
def ant_str_to_sbml_str(ls: LanguageServer, args):
    ant_str = args[0]
    antimony.clearPreviousLoads()
    antimony.freeAll()
    sbml = antimony.loadAntimonyString(ant_str)
    if sbml < 0:
        return {
            'error': 'Antimony -  {}'.format(antimony.getLastError())
        }
    mid = antimony.getMainModuleName()
    sbml_str = antimony.getSBMLString(mid)
    return {
        'sbml_str': sbml_str
    }

@server.thread()
@server.command('antimony.sbmlFileToAntStr')
def sbml_file_to_ant_str(ls: LanguageServer, args):
    sbml = args[0].fileName
    ant_str = _get_antimony_str(sbml)
    return ant_str

@server.thread()
@server.command('antimony.sbmlStrToAntStr')
def sbml_str_to_ant_str(ls: LanguageServer, args):
    sbml = '\n'.join(args[0].split('\n')[1:])
    antimony.clearPreviousLoads()
    antimony.freeAll()
    ant = antimony.loadSBMLString(sbml)
    if ant < 0:
        return {
            'error': 'Antimony -  {}'.format(antimony.getLastError())
        }
    ant_str = antimony.getAntimonyString(None)
    return ant_str

@server.thread()
@server.command('antimony.annotationDescription')
def annotationDescription(ls: LanguageServer, args):
    description = args[0]
    name = args[1]
    SymbolTable().insert_definition(name, description)

@server.thread()
@server.command('antimony.sbmlFileToAntFile')
def sbml_file_to_ant_file(ls: LanguageServer, args):
    sbml = args[0].fileName
    output_dir = args[1]
    ant_str = _get_antimony_str(sbml)
    if 'error' in ant_str:
        return ant_str
    else:
        model_name = os.path.basename(sbml)
        full_path_name = os.path.join(output_dir, os.path.splitext(model_name)[0]+'.ant')
        with open(full_path_name, 'w') as f:
            f.write(ant_str["ant_str"])
        return {
            'msg': 'Antimony has been exported to {}'.format(output_dir),
            'file': full_path_name
        }

@server.thread()
@server.command('antimony.sendQuery')
def query_species(ls: LanguageServer, args):
    try:
        database = args[0]
        query = args[1]
        vscode_logger.info("Recieved search request for: " + database + " " + query)
        start = time.time()
        if database == 'chebi':
            results = services.annot_search_chebi(query)
        elif database == 'uniprot':
            results = services.annot_search_uniprot(query)
        else:
            # This is not supposed to happen
            raise SystemError("Unknown database '{}'".format(database))
        end = time.time()
        vscode_logger.debug("Search request completed")
        vscode_logger.debug("--- %s seconds ---" % (end - start))
        return {
            'query': query,
            'items': results,
        }
    except NetworkError:
        return {
            'error': 'Connection Error!'
        }

#### Hover for displaying information ####
@server.feature(HOVER)
def hover(params: TextDocumentPositionParams):
    global antfile_cache
    global uri
    if antfile_cache is None or uri is None or uri != params.textDocument.uri:
        text_doc = server.workspace.get_document(params.textDocument.uri)
        uri = params.textDocument.uri
        antfile_cache = get_antfile(text_doc)

    symbols, range_ = antfile_cache.symbols_at(sb_position(params.position))

    if not symbols:
        return None
    
    assert range_ is not None
    sym = symbols[0]
    text = sym.help_str()
    contents = MarkupContent(MarkupKind.Markdown, text)

    return Hover(
        contents=contents,
        range=pygls_range(range_),
    )

#### GOTO DEFINITION ####
@server.feature(DEFINITION)
def definition(params):
    global antfile_cache
    global uri
    if antfile_cache is None or uri is None or uri != params.textDocument.uri:
        text_doc = server.workspace.get_document(params.textDocument.uri)
        antfile_cache = get_antfile(text_doc)
        uri = params.textDocument.uri

    srclocations, range_ = antfile_cache.goto(sb_position(params.position))
    definitions = [Location(
        loc.path,
        pygls_range(loc.range)) for loc in srclocations]
    # If no definitions, return None
    return definitions or None

#### ERROR DETECTION ####
def _publish_diagnostics(cur_uri: str) -> AntFile:
    global antfile_cache
    global uri
    if antfile_cache is None or uri is None or uri != cur_uri:
        text_doc = server.workspace.get_document(cur_uri)
        antfile_cache = get_antfile(text_doc)
        uri = cur_uri

    errors = antfile_cache.get_issues()
    diagnostics = [to_diagnostic(e) for e in errors]
    server.publish_diagnostics(uri, diagnostics)
    return antfile_cache

def to_diagnostic(issue: Issue):
    '''Convert the Stibium Issue object to a pygls Diagnostic object'''
    severity = DiagnosticSeverity.Error
    if issue.severity == IssueSeverity.Warning:
        severity = DiagnosticSeverity.Warning
    return Diagnostic(
        range=pygls_range(issue.range),
        message=issue.message,
        severity=severity
    )

#### helper and util ####
@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    antfile = _publish_diagnostics(params.textDocument.uri)

lock = threading.Lock()
latest_millis = 0

@server.thread()
@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
    global latest_millis
    # re-generate parse tree
    global antfile_cache
    global uri
    text_doc = server.workspace.get_document(params.textDocument.uri)
    antfile_cache = get_antfile(text_doc)
    uri = params.textDocument.uri

    def callback(millis):
        with lock:
            if millis < latest_millis:
                return
            assert millis == latest_millis
        _publish_diagnostics(params.textDocument.uri)

    cur_millis = int(time.time() * 1000)

    with lock:
        latest_millis = max(cur_millis, latest_millis)

    t = threading.Timer(0.5, lambda: callback(cur_millis))
    t.start()


@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls, params: DidSaveTextDocumentParams):
    # re-generate parse tree
    global antfile_cache
    global uri
    text_doc = server.workspace.get_document(params.textDocument.uri)
    antfile_cache = get_antfile(text_doc)
    uri = params.textDocument.uri
    _publish_diagnostics(params.textDocument.uri)

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

def _get_sbml_str(ant):
    if ant is None:
        return {
            'error': 'Cannot open file'
        }
    antimony.clearPreviousLoads()
    antimony.freeAll()
    try:
        isfile = os.path.isfile(ant)
    except ValueError:
        return {
            'error': 'Cannot open file'
        }
    if isfile:
        sbml = antimony.loadAntimonyFile(ant)
        if sbml < 0:
            return {
                'error': 'Antimony -  {}'.format(antimony.getLastError())
            }
        mid = antimony.getMainModuleName()
        sbml_str = antimony.getSBMLString(mid)
        return {
            'sbml_str': sbml_str
        }
    else:
        return {
            'error': 'Not a valid file'
        }


if __name__ == '__main__':
    server.start_io()