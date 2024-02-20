# Getty AAT
# A module to parse query results (json) from The Getty Art & Archiechture Thesaurus (AAT)

import json
import gzip
import re
import csv
from SPARQLWrapper import SPARQLWrapper, JSON
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import simplemma
import pandas as pd
import requests
from . import bows

def main():
	if __name__ == "__main__":
		main()

def sparql(aat_uri:list, lang:str) -> dict:
    '''
    Querying prefLabel, altLabel, scopeNote, rdfs comments of concepts in AAT;
    Sends SPARQL queries to the AAT endpoint via SPARQLwrapper 
    aat_uri: list of AAT concepts IDs (str) ['ID']
    lang: str 'en' or 'nl'
    Returns a dict with query results: {'ID':{'lang':'en',
                                              'prefLabel':'',
                                              'altLabels':[],
                                              'scopeNote':'',
                                              'prefLabel_comment':'',
                                              'altLabel_comment':''}
    '''
    
    sparql = SPARQLWrapper("http://vocab.getty.edu/sparql")
    
    if lang == 'en':
        lang_code = '300388277'
    if lang == 'nl':
        lang_code = '300388256'
        
    result_dict = {}
        
    for uri in aat_uri:
        
        result_dict[uri] = {}
        
        query_string = '''SELECT ?prefLabel (GROUP_CONCAT(?altLabel;SEPARATOR="#") AS ?altLabels)
        ?scopeNote ?prefLabel_comment ?altLabel_comment
        WHERE {aat:''' + uri + ''' xl:prefLabel ?pL .?pL dcterms:language aat:''' + lang_code + ''';
        xl:literalForm ?prefLabel .
        OPTIONAL {?pL rdfs:comment ?prefLabel_comment . }
        OPTIONAL {aat:''' + uri + ''' xl:altLabel ?aL .
        ?aL dcterms:language aat:''' + lang_code + ''';
        xl:literalForm ?altLabel . 
        OPTIONAL { ?aL rdfs:comment ?altLabel_comment . }}
        OPTIONAL {aat:''' + uri + ''' skos:scopeNote / dcterms:language aat:'''+ lang_code + ''';
        skos:scopeNote / rdf:value ?scopeNote . }}
        GROUP BY ?prefLabel ?scopeNote ?prefLabel_comment ?altLabel_comment'''
        
        sparql.setQuery(query_string)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        
        prefLabel = None
        altLabels = []
        scopeNote = None
        prefLabel_comment = None
        altLabel_comment = None
        
        for result in results['results']['bindings']:
            
            if 'prefLabel' in result:
                prefLabel = result['prefLabel']['value']
            if 'altLabels' in result:
                altLabels = result['altLabels']['value'].split('#')
            if 'scopeNote' in result:
                scopeNote = result['scopeNote']['value']
            if 'prefLabel_comment' in result:
                prefLabel_comment = result['prefLabel_comment']['value']
            if 'altLabel_comment' in result:
                altLabel_comment = result['altLabel_comment']['value']

            result_dict[uri]['lang'] = lang
            result_dict[uri]['prefLabel'] = prefLabel
            result_dict[uri]['altLabels'] = altLabels
            result_dict[uri]['prefLabel_comment'] = prefLabel_comment
            result_dict[uri]['altLabel_comment'] = altLabel_comment
            result_dict[uri]['scopeNote'] = scopeNote
        
    return result_dict


def _get_entity_info(entity_id:str, lang:str, aat_gzip:dict) -> dict:
    '''
    This function is used for 'find_term_in_literals'
    Getting the values of prefLabel (str), altLabel (list), prefLabel_comment (str), altLabel_comment(list), and scopeNote (str)
    by entity ID in AAT
    entity_id: str, entity ID in AAT (for example, '300189559')
    lang: str, 'en' or 'nl'; language of entities info
    aat_gzip: dict, ungzipped json file with search results (ungzips in the main function)
    Returns a dict {'entity': '',
					 'scopeNote': '',
					 'prefLabel_comment': '',
					 'prefLabel': '',
					 'altLabel': [],
					 'altLabel_comment': []}
    '''

    results = {}
    results['entity'] = entity_id
    altLabel_list = []
    altLabel_comment_list = []
    results['scopeNote'] = ''
    results['prefLabel_comment'] = ''
    
    for triple in aat_gzip["results"]["bindings"]:
        if entity_id in triple['Subject']['value']:
            
            # prefLabel
            if 'prefLabel' in triple['Predicate']['value']:
                for triple_t in aat_gzip["results"]["bindings"]:
                    if triple_t['Subject']['value'] == triple['Object']['value']:
                        if 'literalForm' in triple_t['Predicate']['value']:
                            results['prefLabel'] = triple_t['Object']['value']
                        # prefLabel comment
                        if 'comment' in triple_t['Predicate']['value']:
                            results['prefLabel_comment'] = triple_t['Object']['value']
                        
            # altLabel
            if 'altLabel' in triple['Predicate']['value']:
                for triple_t in aat_gzip["results"]["bindings"]:
                    if triple_t['Subject']['value'] == triple['Object']['value']:
                        if 'literalForm' in triple_t['Predicate']['value']:
                            altLabel_list.append(triple_t['Object']['value'])
                        # altLabel comment
                        if 'comment' in triple_t['Predicate']['value']:
                            altLabel_comment_list.append(triple_t['Object']['value'])
                            
            # scopeNote
            if 'scopeNote' in triple['Predicate']['value']:
                for triple_t in aat_gzip["results"]["bindings"]:
                    if triple_t['Subject']['value'] == triple['Object']['value']:
                        results['scopeNote'] = triple_t['Object']['value']
                            
            results['altLabel'] = altLabel_list
            results['altLabel_comment'] = altLabel_comment_list
                        
    return results

def find_term_in_literals(query_term:str, lang:str) -> list:
    '''
    Finding query terms in the literal values of properties:
    prefLabel, altLabel, rdfs comment (for prefLabel and altLabel), and scopeNote
    query_term: str, for example 'term'
    ang: str, 'en' or 'nl'; language of the literals in which the query term is searched
    Returns a list of dicts with an AAT entity URI and the property name in the literal value of which the term was found
    '''

    # reading the gzip json file with aat search results
    # path to raw gzip on GitHub
    gzip_path = f"https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/AAT/gzip_aat_subgraph_{lang}.json"
    
    # decompressing
    aat_gzip = json.loads(gzip.decompress(requests.get(gzip_path).content))
    
    list_of_results = []
    
    for triple in aat_gzip["results"]["bindings"]:
        
        if triple['Object']['type'] == 'literal' \
        and len(re.findall(f'\\b{query_term}\\b',triple['Object']['value'],re.IGNORECASE)) > 0:
            
            results_per_hit = {}
            results_per_hit['query_term'] = query_term
            results_per_hit['aat_uri'] = ''
            
            # if a term found in scopeNote
                    
            if 'rdf-syntax' in triple['Predicate']['value']:
                results_per_hit['found_in'] = 'scopeNote'
                for triple_t in aat_gzip["results"]["bindings"]:
                    if triple_t['Object']['value'] == triple['Subject']['value']:
                        # getting entity URI
                        entity = triple_t['Subject']['value'].split('/')[-1]
                        
            # if a term found in pref or alt labels
            
            if 'literalForm' in triple['Predicate']['value']:
                for triple_t in aat_gzip["results"]["bindings"]:
                    if triple_t['Object']['value'] == triple['Subject']['value']:
                        # getting entity URI
                        entity = triple_t['Subject']['value'].split('/')[-1]
                        # altLabel or prefLabel 
                        if 'altLabel' in triple_t['Predicate']['value']:
                            results_per_hit['found_in'] = 'altLabel'
                        if 'prefLabel' in triple_t['Predicate']['value']:
                            results_per_hit['found_in'] = 'prefLabel'
                        
            # if a term found in rdfs comment
            
            if 'comment' in triple['Predicate']['value']:
                for triple_t in aat_gzip["results"]["bindings"]:
                    if triple_t['Object']['value'] == triple['Subject']['value']:
                        # getting entity URI
                        entity = triple_t['Subject']['value'].split('/')[-1]
                        # comment to altLabel or prefLabel
                        if 'altLabel' in triple_t['Predicate']['value']:
                            results_per_hit['found_in'] = 'altLabel_comment'
                        if 'prefLabel' in triple_t['Predicate']['value']:
                            results_per_hit['found_in'] = 'prefLabel_comment'
            
            results_per_hit['aat_uri'] = entity
            
            entity_info = _get_entity_info(entity, lang, aat_gzip)
            
            results_per_hit['prefLabel'] = entity_info['prefLabel']
            results_per_hit['prefLabel_comment'] = entity_info['prefLabel_comment']
            results_per_hit['altLabel'] = entity_info['altLabel']
            results_per_hit['altLabel_comment'] = entity_info['altLabel_comment']
            results_per_hit['scopeNote'] = entity_info['scopeNote']
            
            list_of_results.append(results_per_hit)
            
    return list_of_results

def get_bows(lang:str) -> dict:
    '''
    Getting bag of words (BoW) from the AAT search results for every search term
    lang: str, 'en' or 'nl'
    Returns a dict with BoWs per hit per term: {term:[{aat_URI:['token1','token2','token3']}]}
    '''

    path_to_results = f"https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/AAT/aat_query_results_{lang}.json"
    search_results = requests.get(path_to_results).json()

    wnl = WordNetLemmatizer()
    all_bows = {}

    for query_term, results in search_results.items():

        list_by_term = []

        for hit in results:
            q_bag = {}
            literals = []
            
            literals.append(hit["prefLabel"])
            literals.append(hit["prefLabel_comment"])
            literals.append(hit["scopeNote"])
            literals.extend(hit["altLabel"])
            literals.extend(hit["altLabel_comment"])

            bow = bows.make_bows(literals,lang,merge_bows=True)

            q_bag[hit["aat_uri"]] = bow

            list_by_term.append(q_bag)

        all_bows[query_term] = list_by_term

    return all_bows


def get_lit_related_matches_bow(lang:str) -> dict:
    '''
    Generates dict with BoWs by query terms and their related matches in AAT
    reads files with AAT BoWs: aat_bows_en.json (EN), aat_bows_nl.json (NL)
    the info about which AAT concept is a related match to the query term is taken from https://github.com/cultural-ai/wordsmatter/blob/main/related_matches/rm.csv
    lang: str, 'en' or 'nl'
    Returns a dict with BoWs by term: {term:{concept_uri:['token1','token2','token3']}}
    '''
    
    results = {}
    
    # loading related matches from GitHub
    path_rm = "https://github.com/cultural-ai/wordsmatter/raw/main/related_matches/rm.json"
    rm = requests.get(path_rm).json()
    
    # load aat bows
    path_to_bows = f"https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/AAT/aat_bows_{lang}.json"
    aat_bows = requests.get(path_to_bows).json()

    # getting a list of all AAT URIs of related matches
    # terms with no related matches won't be included in the file
    related_matches_aat = list(set([values["related_matches"]["aat"][0] for values in rm.values() \
                            if values["lang"] == lang and values["related_matches"]["aat"][0] != 'None']))    
    
    # getting BoWs for AAT concept URIs 
    related_matches_aat_uri_bows = {}
    for uri_rm in related_matches_aat:
        for hits in aat_bows.values():
            for hit in hits:
                for uri, bow in hit.items():
                    if uri == uri_rm:
                        related_matches_aat_uri_bows[uri_rm] = bow
                        
    # shaping resulting dict: terms with related matches and BoWs
    for values in rm.values():
        if values["lang"] == lang:
            rm_aat = values["related_matches"]["aat"][0]
            if rm_aat != "None":
                for term in values["query_terms"]:
                    if rm_aat in related_matches_aat_uri_bows.keys():
                        results[term] = {"aat_uri":rm_aat,"bow":related_matches_aat_uri_bows[rm_aat]}
            
    return results


def get_cs(lang:str):
    '''
    Calculating three cosine similarity scores between AAT search results and background info;
    the similarity scores are based on (1) only related matches, (2) only WM text, and (3) extended bows with related matches and WM text
    lang:str, language of bows, "en" or "nl"
    Returns a pandas data frame with columns:
    query_term, aat_URI, bow, cs_rm, cs_wm, cs_rm_wm
    '''

    nlp = bows.load_spacy_nlp(lang)

    # load bckground info
    path_bg = "https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/bg/background_info_bows.json"
    bg_info = requests.get(path_bg).json()

    # load aat bows

    path_aat_bows = f"https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/AAT/aat_bows_{lang}.json"
    aat_bows = requests.get(path_aat_bows).json()

    aat_df = pd.DataFrame(columns=['term','hit_id','bow','cs_rm','cs_wm','cs_rm_wm'])

    for term, hits in aat_bows.items():

        bg_rm = bows._collect_bg(term,lang,bg_info,bg_bow="rm")
        bg_wm = bows._collect_bg(term,lang,bg_info,bg_bow="wm")
        bg_rm_wm = bows._collect_bg(term,lang,bg_info,bg_bow="joint")
          
        # if there are search results
        if len(hits) > 0:
            for hit in hits:
                for i, bow in hit.items():
                    # making a set
                    aat_bow = list(set(bow))
                    
                    if len(aat_bow) > 0:
                        # calculate cs
                        cs_rm = bows.calculate_cs(bg_rm,aat_bow,nlp)
                        cs_wm = bows.calculate_cs(bg_wm,aat_bow,nlp)
                        cs_rm_wm = bows.calculate_cs(bg_rm_wm,aat_bow,nlp)
                        
                        aat_df.loc[len(aat_df)] = [term,i,aat_bow,cs_rm,cs_wm,cs_rm_wm]
                    
                    # if there are no tokens, all cs = None
                    else:
                        aat_df.loc[len(aat_df)] = [term,i,aat_bow,None,None,None]

        # if there are no search results in AAT, cs = None
        else:
            aat_df.loc[len(aat_df)] = [term,None,None,None,None,None]

    return aat_df