# Open Dutch WordNet parser
# Download Open Dutch WordNet from "https://github.com/cultural-ai/OpenDutchWordnet"
# requires lxml: pip install lxml

import sys
import json
import csv
import re
import requests
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import simplemma
from . import bows

def main():
    if __name__ == "__main__":
        main()

def _set_odwn(path_odwn:str):
    """
    path_odwn: str path to the directory with OpenDutchWordnet (not including the module itself, for example "user/Downloads")
    Inserts the path to the OpenDutchWordnet module
    Download OpenDutchWordnet from "https://github.com/cultural-ai/OpenDutchWordnet"
    Returns an instance using Wn_grid_parser
    """

    sys.path.insert(0,path_odwn)
    from OpenDutchWordnet import Wn_grid_parser
    # creating an instance
    odwn_instance = Wn_grid_parser(Wn_grid_parser.odwn)

    return odwn_instance

def get_le_info(le_ids:list, path_odwn:str) -> dict:
    """
    Getting Lemma, sense definitions, examples, synset ID, synset definitions of ODWN Lexical Entries
    le_ids: list of Lexical Entries IDs (str), for example "appel-n-1"
    path_odwn: str path to the directory with OpenDutchWordnet (not including the module itself, for example "user/Downloads")
    Returns a dict: {"le_id": {"lemma": "",
                                "sense_def": "",
                                "examples": [],
                                "synset_ID": "",
                                "synset_def": []}
    """
    # importing ODWN
    instance = _set_odwn(path_odwn)
    
    # load all glosses
    path_to_glosses = "https://github.com/cultural-ai/LODlit/raw/main/ODWN/odwn_synset_glosses.json"
    synset_glosses = requests.get(path_to_glosses).json()
    
    results_odwn = {}

    for le_id in le_ids:
        le = instance.les_find_le(le_id)
        synset_id = le.get_synset_id()

        sense_def = le.get_definition()
        if sense_def == "":
            sense_def = None

        results_odwn[le_id] = {"lemma": le.get_lemma(),
                                "sense_def": sense_def,
                                "examples": le.get_sense_example(),
                                "synset_ID": synset_id,
                                "synset_def": synset_glosses.get(synset_id)}
    return results_odwn

def _shape_search_results(instance,query_term:str,le,all_synset_definitions:dict,found_in:str,example="") -> dict:
    
    """
    instance: class wn_grid_parser.Wn_grid_parser
    query_term: str
    le: class le.Le
    all_synset_definitions: dict, parses "https://github.com/cultural-ai/LODlit/raw/main/ODWN/odwn_synset_glosses.json" 
    found_in: str
    example: str, default is ""
    Returns a dict of search results
    This function does not perform searching,
    but puts the search results of "find_terms" in a dict
    """
    
    result_dict = {}
    result_dict["query_term"] = query_term
    result_dict["le_id"] = le.get_id()
    result_dict["le_written_form"] = le.get_lemma()
    result_dict["sense_id"] = le.get_sense_id()
    result_dict["sense_definition"] = le.get_definition()
    result_dict["sense_examples"] = le.get_sense_example()

    if le.get_synset_id() != None:
        synset_id = le.get_synset_id()
        result_dict["synset_id"] = synset_id
        result_dict["synonyms"] = [les.get_lemma() for les in instance.les_all_les_of_one_synset(synset_id)]
        if synset_id in all_synset_definitions.keys():
            result_dict["synset_definitions"] = all_synset_definitions[synset_id]
        else:
            result_dict["synset_definitions"] = []
    else:
        result_dict["synset_id"] = ""
        result_dict["synonyms"] = []
        result_dict["synset_definitions"] = []
        
    result_dict["found_in"] = found_in
    
    if found_in == "sense_examples":
        # there can be multiple examples; writing the example the term was found in
        result_dict["found_in_example"] = example
    
    return result_dict

def find_terms(query_terms:list, path_odwn:str) -> dict:
    '''
    Searching for a query term in lemmas (written form of Lexical Entry (LE)), sense definitions, sense examples, and synset definitions (glosses) of ODWN
    query_term: list of terms to search in ODWN (str), phrases are also allowed
    path_odwn: str path to the directory with OpenDutchWordnet (not including the module itself, for example "user/Downloads")
    Returns a dict with the LE or synset info by query term if the query term was found
    if found in LE or its children tags:
        {query_term:[{"query_term": "",
                    "le_id": "",
                   "le_written_form": "",
                   "sense_id": "",
                   "sense_definition": "",
                   "sense_examples": [],
                   "synset_id": "",
                   "synonyms": [],
                   "synset_definitions": [],
                   "found_in": ""}]};
    if found in a synset definition, but that synset is not attached to any LEs:
        {query_term:[{"query_term": "",
                   "synset_id": "",
                   "synonyms": [],
                   "synset_definitions": [],
                   "found_in": "synset_definitions",
                   "found_in_synset_definition": ""}]}
    '''

    # importing ODWN
    instance = _set_odwn(path_odwn)
    
    # load all glosses
    path_to_glosses = "https://github.com/cultural-ai/LODlit/raw/main/ODWN/odwn_synset_glosses.json"
    synset_glosses = requests.get(path_to_glosses).json()

    results = {}

    for query_term in query_terms:

        results_per_term = []

        # searching in lemmas
        for le in instance.lemma_get_generator(query_term,ignore_case=True):
            results_per_term.append(_shape_search_results(instance,query_term,le,synset_glosses,"le"))

        # Iterating over all Lexical Entries
        
        # searching in sense definitions
        for le in instance.les_get_generator():
            if len(re.findall(f"\\b{query_term}\\b",le.get_definition(),re.IGNORECASE)) > 0:
                results_per_term.append(_shape_search_results(instance,query_term,le,synset_glosses,"sense_definition"))

            # searching in sense examples
            for example in le.get_sense_example():
                if len(re.findall(f"\\b{query_term}\\b",example,re.IGNORECASE)) > 0:
                    results_per_term.append(_shape_search_results(instance,query_term,le,synset_glosses,"sense_examples",example))

        # searching in synset definitions
        for synset_id, definitions in synset_glosses.items():
            for d in definitions:
                if len(re.findall(f"\\b{query_term}\\b",d,re.IGNORECASE)) > 0:
                        # results_per_term for synsets are different, so we don"t use "_shape_search_results()"
                        result_dict = {}
                        result_dict["query_term"] = query_term
                        result_dict["synset_id"] = synset_id
                        result_dict["synonyms"] = [les.get_lemma() for les in instance.les_all_les_of_one_synset(synset_id)]
                        result_dict["synset_definitions"] = synset_glosses[synset_id]
                        result_dict["found_in"] = "synset_definitions"
                        # there can be multiple definitions; writing the definition the term was found in
                        result_dict["found_in_synset_definition"] = d
                        results_per_term.append(result_dict)

        results[query_term] = results_per_term

    return results

def get_bows(path_to_results:str) -> dict:
    '''
    Getting bag of words (BoW) from the Open Dutch Wordnet search results for every search term
    path_to_results: str, a path to the search results (in json format)
    Returns a dict with BoWs per hit per term: {term:[{synset_id/le_id:['token1','token2','token3']}]}
    '''
    wnl = WordNetLemmatizer()

    all_bows = {}
   
    with open(path_to_results,'r') as jf:
        search_results = json.load(jf)

    for query_term, results in search_results.items():

        list_by_term = []

        for hit in results:

            q_bag = {}
            literals = []

            if hit["found_in"] == "synset_definitions":
                literals.extend(hit["synonyms"])
                literals.extend(hit["synset_definitions"])
            else:
                literals.append(hit["le_written_form"])
                literals.extend(hit["sense_examples"])
                literals.extend(hit["synonyms"])
                literals.extend(hit["synset_definitions"])
                if hit["sense_definition"] != "":
                    literals.append(hit["sense_definition"])

            bow = bows.make_bows(literals,"nl",merge_bows=True)

            # if there's no synset ID, using LE ID as key
            if hit["synset_id"] != "":
                q_bag[hit["synset_id"]] = bow
            else:
                q_bag[hit["le_id"]] = bow

            list_by_term.append(q_bag)

        all_bows[query_term] = list_by_term

    return all_bows


def get_lit_related_matches_bow() -> dict:
    '''
    Generates dict with BoWs by query terms and their related matches in ODWN
    reads two json files: (1) odwn_bows.json (ODWN BoWs), (2) related_matches_odwn.json (related matches for every term in ODWN)
    Returns a dict with BoWs by term: {term:['token1','token2','token3']}
    This dict doesn't store info about synsets IDs or LE IDs bc one term can have one or more related matches;
    in these cases, BoWs of each synsets and LEs are merged
    '''
    
    results = {}
    
    # loading related matches
    path_rm = "https://github.com/cultural-ai/wordsmatter/raw/main/related_matches/rm.json"
    rm = requests.get(path_rm).json()

    # load odwn bows
    path_to_bows = f"https://github.com/cultural-ai/LODlit/raw/main/ODWN/odwn_bows.json"
    odwn_bows = requests.get(path_to_bows).json()
    
    # getting a list of all ODWN LE IDs and synset IDs of related matches
    odwn_les_synsets = []
    for values in rm.values():
        if values["odwn_le"][0] != 'None':
            odwn_les_synsets.extend(values["odwn_le"])
        if values["odwn_synsets"] != '':
            odwn_les_synsets.extend(values["odwn_synsets"])

    related_matches_odwn = list(set(odwn_les_synsets))
            
    # getting BoWs for each LE or synset
    related_matches_odwn_bows = {}
    for odwn_id in related_matches_odwn:
        for hits in odwn_bows.values():
            for hit in hits:
                for le, bow in hit.items():
                    if le == odwn_id:
                        related_matches_odwn_bows[le] = bow
                        
    # shaping resulting dict: terms with related matches and BoWs
    for values in rm.values():
        rm_ids = []
        rm_ids.extend(values["odwn_le"])
        rm_ids.extend(values["odwn_synsets"])
        if rm_ids != []:
            for term in values["query_terms"]:
                bow = []
                for i in rm_ids:
                    if i in related_matches_odwn_bows.keys():
                        bow.extend(related_matches_odwn_bows[i])
                        results[term] = bow
    
    return results

def get_cs():
    '''
    Calculating three cosine similarity scores between ODWN search results and background info;
    the similarity scores are based on (1) only related matches, (2) only WM text, and (3) extended bows with related matches and WM text
    Returns a pandas data frame with columns:
    query_term, hit_id, bow, cs_rm, cs_wm, cs_rm_wm
    '''

    nlp = bows._load_spacy_nlp("nl")

    # load bckground info
    path_bg = "https://github.com/cultural-ai/LODlit/raw/main/bg/background_info_bows.json"
    bg_info = requests.get(path_bg).json()

    # load all pwn bows
    path_odwn_bows = f"https://github.com/cultural-ai/LODlit/raw/main/ODWN/odwn_bows.json"
    odwn_bows = requests.get(path_pwn_bows).json()

    odwn_df = pd.DataFrame(columns=['term','hit_id','bow','cs_rm','cs_wm','cs_rm_wm'])

    for term, hits in odwn_bows.items():

        bg_rm = bows._collect_bg(term,"nl",bg_info,bg_bow="rm")
        bg_wm = bows._collect_bg(term,"nl",bg_info,bg_bow="wm")
        bg_rm_wm = bows._collect_bg(term,"nl",bg_info,bg_bow="joint")

        # if there are search results
        if len(hits) > 0:
            for hit in hits:
                for i, bow in hit.items():
                    # making a set
                    bow_set = list(set(bow))

                    if len(bow_set) > 0:
                        # calculate cs
                        cs_rm = bows.calculate_cs(bg_rm,bow_set,nlp)
                        cs_wm = bows.calculate_cs(bg_wm,bow_set,nlp)
                        cs_rm_wm = bows.calculate_cs(bg_rm_wm,bow_set,nlp)
                        
                        odwn_df.loc[len(odwn_df)] = [term,i,bow_set,cs_rm,cs_wm,cs_rm_wm]
                    
                    # if there are no tokens, all cs = None
                    else:
                        odwn_df.loc[len(odwn_df)] = [term,i,bow_set,None,None,None]

        # if there are no search results in PWN, cs = None
        else:
            odwn_df.loc[len(odwn_df)] = [term,None,None,None,None,None]

    return odwn_df

def get_pragmatics(ids:list, path_odwn:str, by="synset_id") -> dict:
    '''
    Get pragmatic values of lemmas by synset IDs or sense IDs
    ids: list, synset ids or sense_ids, for example ["temperatuur-n-4", "temperatuur-n-3"]
    path_odwn: str, path to the directory with OpenDutchWordnet (not including the module itself, for example "user/Downloads")
    by: str, how to get pragmatics: by "synset_id" or "sense_id", default is "synset_id"
    Returns dict: {'id': [{'le_id': 'lemma_id',
                       'pragmatics': {'register': None,
                        'geography': None,
                        'chronology': None,
                        'connotation': None,
                        'domain': None}}]}
    '''
    # importing ODWN
    instance = _set_odwn(path_odwn)

    pragmatics = {}

    for i in ids:

        pragmatics_per_le = []

        if by == "synset_id":

            for le in instance.les_all_les_of_one_synset(i):
                dict_per_le = {}
                dict_per_le["le_id"] = le.get_id()
                dict_per_le["pragmatics"] = le.get_pragmatics()
                pragmatics_per_le.append(dict_per_le)

        if by == "sense_id":

            for le in instance.les_get_generator():
                if le.get_sense_id() == i:
                    dict_per_le = {}
                    dict_per_le["le_id"] = le.get_id()
                    dict_per_le["pragmatics"] = le.get_pragmatics()
                    pragmatics_per_le.append(dict_per_le)

        pragmatics[i] = pragmatics_per_le

    return pragmatics