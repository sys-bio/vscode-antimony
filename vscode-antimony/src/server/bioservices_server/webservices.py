'''Aggregation of webservices required by the extension.

Author: Gary Geng
'''

# local
from asyncio.log import logger
# from .bioservices.chebi import ChEBI
# from .bioservices.uniprot import UniProt

from bioservices import ChEBI
from bioservices import UniProt
from bioservices import Rhea

from ols_client import OlsClient

import pandas as pd
import logging

from io import StringIO
from urllib.error import URLError

from typing import Text
import csv


class NetworkError(Exception):
    pass


class WebServices:
    '''Wrapper class that allows querying a couple of Bio webservices for annotation'''
    def __init__(self):
        self.chebi = None
        self.uniprot = None
        self.rhea = None
        self.ontology = None

    def init_chebi(self):
        if self.chebi is None:
            try:
                self.chebi = ChEBI()
            except Exception:
                raise NetworkError

    def init_uniprot(self):
        if self.uniprot is None:
            try:
                self.uniprot = UniProt()
            except Exception:
                raise NetworkError
            
    def init_rhea(self):
        if self.rhea is None:
            try:
                self.rhea = Rhea()
            except Exception:
                raise NetworkError
            
    def init_ontology(self):
        if self.ontology is None:
            try:
                self.ontology = OlsClient()
            except Exception:
                raise NetworkError

    def annot_search_chebi(self, query: str):
        self.init_chebi()
        # TODO do we want to change searchCategory and maybe THREE STARS?
        if query.strip() == '':
            return list()
        try:
            results = self.chebi.getLiteEntity(query, maximumResults=100)
        except URLError:
            raise NetworkError

        # no result
        if isinstance(results, str):
            return list()
        # sort by length as well. TODO should I do this?
        results.sort(key=lambda e: e.searchScore * -10000 + len(e.chebiAsciiName))
        results = results[:20]
        return [{
            'id': res.chebiId,
            'name': res.chebiAsciiName,
            'prefix': 'chebi'
        } for res in results]

    def annot_search_uniprot(self, query: str):
        self.init_uniprot()

        if query.strip() == '':
            return list()

        try:
            result_str = self.uniprot.search(query, limit=20, columns='id,entry name,protein names,genes')
        except URLError:
            raise NetworkError

        assert isinstance(result_str, str)
        result_f = StringIO(result_str)
        reader = csv.reader(result_f, delimiter='\t')
        objects = list()
        # Skip header
        next(reader, None)
        for row in reader:
            id_, entry_name, protein_names, genes = row
            objects.append({
                'id': id_,
                'name': protein_names,
                'entry_name': entry_name,
                'protein_names': protein_names,
                'genes': genes,
                'prefix': 'uniprot',
            })
        return objects
    
    def annot_search_rhea(self, query: str):
        rhea_logger = logging.getLogger("rhea logger")
        self.init_rhea()
        
        if query.strip() == '':
            return list()

        try:
            result_df = self.rhea.search(query, columns='rhea-id,equation')
            rhea_logger.info("result_df: " + result_df[0:20])
        except URLError:
            raise NetworkError

        result_df = result_df[0:20]
        result_l = result_df.values.tolist()
        rhea_logger.info(result_l)
        objects = list()
        for row in result_l:
            id_ = row[0]
            equation = row[1]
            id_ = id_[5:]
            objects.append({
                'id': id_,
                'name': equation,
                'detail': id_,
                'prefix': 'rhea',
            })
        return objects
    
    def annot_search_ontology(self, query: str, ontology_id: str):
        ontology_logger = logging.getLogger("ontology logger")
        self.init_ontology()
        
        if query.strip() == '':
            return list()
        ontology_logger.info('here')
        try:
            result_dict = self.ontology.search(query)
            result_dicts = result_dict['response']['docs']
            ontology_logger.info(result_dict)
        except URLError:
            raise NetworkError
        
        objects = list()
        
        for d in result_dicts:
            iri = d['iri']
            name = d['label']
            prefix = d['ontology_prefix']
            if (prefix == ontology_id):
                objects.append({
                    'name': name,
                    'iri': iri,
                    'prefix': 'ontology'
                })
        return objects