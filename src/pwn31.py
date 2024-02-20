# Module to parse Princeton WordNet 3.1

# Important! After installing NLTK, download wordnet31 ('https://github.com/nltk/nltk_data/blob/gh-pages/packages/corpora/wordnet31.zip');
# put the content of 'wordnet31' to 'wordnet' in 'nltk_data/corpora' (it is not possible to import wordnet31 from nltk.corpus; See explanations on the WordNet website (retrieved on 10.02.2023): https://wordnet.princeton.edu/download/current-version; "WordNet 3.1 DATABASE FILES ONLY. You can download the WordNet 3.1 database files. Note that this is not a full package as those above, nor does it contain any code for running WordNet. However, you can replace the files in the database directory of your 3.0 local installation with these files and the WordNet interface will run, returning entries from the 3.1 database. This is simply a compressed tar file of the WordNet 3.1 database files.";
# Use check_version() to ensure that WordNet 3.1 is imported

import json
import re
import requests
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import warnings
import pandas as pd
from . import bows

def main():

    print("Install NLTK and download wordnet. Download wordnet31 from 'https://github.com/nltk/nltk_data/blob/gh-pages/packages/corpora/wordnet31.zip' and put the content of 'wordnet31' to 'wordnet' in 'nltk_data/corpora'")

    if __name__ == "__main__":
        main()

def check_version() -> str:
    return f"You have WordNet version {wn.get_version()}"

def find_term(query_term:str) -> list:
    '''
    Searching for a query term in synset lemmas, synset difinitions, and synset examples
    query_term: str, a term to search in synsets, phrases are also allowed
    Returns a list of dicts with the synset info if the query term was found:
    [{'query_term':query_term,
        'synset_id':'',
        'lemmata':[],
        'definition':'',
        'examples':[],
        'found_in':''}]
    '''

    if wn.get_version() != '3.1':
        warnings.warn("This module is created to parse WordNet 3.1. Your version is different. Download version 3.1 from 'https://github.com/nltk/nltk_data/blob/gh-pages/packages/corpora/wordnet31.zip' and put the content of 'wordnet31' to 'wordnet' in 'nltk_data/corpora'. Import wordnet again and check your version with .get_version()")

    search_results = []
    # searching in lemmata
    # getting synset_id, lemmata (synonyms), definition, examples
    for synset in wn.synsets(query_term):
        for le in synset.lemmas():
            # exact match between query term and lemma name
            if query_term == le.name().lower(): # lemmas can be capitalized
                result_dict = {}
                result_dict['query_term'] = query_term
                result_dict['synset_id'] = synset.name()
                result_dict['lemmata'] = [l.name() for l in synset.lemmas()]
                result_dict['definition'] = synset.definition()
                result_dict['examples'] = synset.examples()
                result_dict['found_in'] = 'lemmata'
                search_results.append(result_dict)

    # searching in all synsets
    for synset in list(wn.all_synsets()):

        # searching in definitions
        if len(re.findall(f'\\b{query_term}\\b',synset.definition(),re.IGNORECASE)) > 0:
            result_dict = {}
            result_dict['query_term'] = query_term
            result_dict['synset_id'] = synset.name()
            result_dict['lemmata'] = [l.name() for l in synset.lemmas()]
            result_dict['definition'] = synset.definition()
            result_dict['examples'] = synset.examples()
            result_dict['found_in'] = 'definition'
            search_results.append(result_dict)

        # searching in examples
        for example in synset.examples():
            if len(re.findall(f'\\b{query_term}\\b',example,re.IGNORECASE)) > 0:
                result_dict = {}
                result_dict['query_term'] = query_term
                result_dict['synset_id'] = synset.name()
                result_dict['lemmata'] = [l.name() for l in synset.lemmas()]
                result_dict['definition'] = synset.definition()
                result_dict['examples'] = synset.examples()
                result_dict['found_in'] = 'examples'
                search_results.append(result_dict)

    return search_results

def get_synsets_info(synsets:list) -> dict:
    '''
    Getting lemmata, definition, and examples of synsets
    synsets: a list of synsets IDs (str), for example ['cookie.n.01','cookie.n.02','cookie.n.03']
    Return a dict: {'synset_id': {'lemmata': [],
                                   'definition': '',
                                   'examples': []}
    '''
    
    synsets_info = {}
    
    for s in synsets:
        synset = wn.synset(s)
        lemmata = [l.name() for l in synset.lemmas()]
        definition = synset.definition()
        examples = synset.examples()
        
        # writing results 
        synsets_info[s] = {'lemmata': lemmata,
                         'definition': definition,
                         'examples': examples}
        
    return synsets_info

def get_bows(path_to_results:str) -> dict:
    '''
    Getting bag of words (BoW) from the Princeton WordNet 3.1 search results for every search term
    path_to_results: str, a path to the search results (in json format)
    Returns a dict with BoWs per hit per term: {term:[{synset_id:['token1','token2','token3']}]}
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

            literals.extend(hit["lemmata"])
    
            if hit["definition"] != "":
                literals.append(hit["definition"])
        
            literals.extend(hit["examples"])

            bow = bows.make_bows(literals,"en",merge_bows=True)

            q_bag[hit["synset_id"]] = bow

            list_by_term.append(q_bag)

        all_bows[query_term] = list_by_term

    return all_bows


def get_lit_related_matches_bow() -> dict:
    '''
    Generates dict with BoWs by query terms and their related matches in PWN
    reads the file with PWN BoWs: pwn31_bows.json
    the info about which PWN synset is a related match to the query term is taken from https://github.com/cultural-ai/wordsmatter/blob/main/related_matches/rm.csv
    Returns a dict with BoWs by term: {term:['token1','token2','token3']}
    This dict doesn't store info about synsets IDs bc one term can have one or more related match synsets;
    in these cases, BoWs of each synsets are merged
    '''
    
    results = {}
    
    # loading related matches
    path_rm = "https://github.com/cultural-ai/wordsmatter/raw/main/related_matches/rm.json"
    rm = requests.get(path_rm).json()

    # load pwn bows
    path_to_bows = f"https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/PWN/pwn31_bows.json"
    pwn_bows = requests.get(path_to_bows).json()

    # getting a list of all PWN synsets of related matches
    pwn_synsets = []
    for values in rm.values():
        if values["lang"] == "en" and values["related_matches"]["pwn"][0] != 'None':
            pwn_synsets.extend(values["related_matches"]["pwn"])

    related_matches_pwn = list(set(pwn_synsets))

    # getting BoWs for each synset 
    related_matches_pwn_synsets_bows = {}
    for s_rm in related_matches_pwn:
        for hits in pwn_bows.values():
            for hit in hits:
                for s, bow in hit.items():
                    if s == s_rm:
                        related_matches_pwn_synsets_bows[s_rm] = bow

    # shaping resulting dict: BoWs per term
    for values in rm.values():
        if values["lang"] == "en":
            rm_synsets = values["related_matches"]["pwn"]
            if rm_synsets[0] != "None":
                for term in values["query_terms"]:
                    synsets_bow = []
                    for s in rm_synsets:
                        if s in related_matches_pwn_synsets_bows.keys():
                            synsets_bow.extend(related_matches_pwn_synsets_bows[s])
                            results[term] = synsets_bow

    return results

def get_cs():
    '''
    Calculating three cosine similarity scores between PWN search results and background info;
    the similarity scores are based on (1) only related matches, (2) only WM text, and (3) extended bows with related matches and WM text
    Returns a pandas data frame with columns:
    query_term, hit_id, bow, cs_rm, cs_wm, cs_rm_wm
    '''

    nlp = bows.load_spacy_nlp("en")

    # load bckground info
    path_bg = "https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/bg/background_info_bows.json"
    bg_info = requests.get(path_bg).json()

    # load all pwn bows
    path_pwn_bows = f"https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/PWN/pwn31_bows.json"
    pwn_bows = requests.get(path_pwn_bows).json()

    pwn_df = pd.DataFrame(columns=['term','hit_id','bow','cs_rm','cs_wm','cs_rm_wm'])

    for term, hits in pwn_bows.items():

        bg_rm = bows._collect_bg(term,"en",bg_info,bg_bow="rm")
        bg_wm = bows._collect_bg(term,"en",bg_info,bg_bow="wm")
        bg_rm_wm = bows._collect_bg(term,"en",bg_info,bg_bow="joint")

        # if there are search results
        if len(hits) > 0:
            for hit in hits:
                for i, bow in hit.items():
                    # making a set
                    pwn_bow = list(set(bow))

                    if len(pwn_bow) > 0:
                        # calculate cs
                        cs_rm = bows.calculate_cs(bg_rm,pwn_bow,nlp)
                        cs_wm = bows.calculate_cs(bg_wm,pwn_bow,nlp)
                        cs_rm_wm = bows.calculate_cs(bg_rm_wm,pwn_bow,nlp)
                        
                        pwn_df.loc[len(pwn_df)] = [term,i,pwn_bow,cs_rm,cs_wm,cs_rm_wm]
                    
                    # if there are no tokens, all cs = None
                    else:
                        pwn_df.loc[len(pwn_df)] = [term,i,pwn_bow,None,None,None]

        # if there are no search results in PWN, cs = None
        else:
            pwn_df.loc[len(pwn_df)] = [term,None,None,None,None,None]

    return pwn_df