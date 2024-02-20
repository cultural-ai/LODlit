# Wikidata module: sending API requests and claning the search results

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import simplemma
import json
import requests
import time
import re
import pandas as pd
import gzip
import warnings
from . import bows

def main():
    if __name__ == "__main__":
        main()

def get_search_hits(search_term:str,lang:str,user_agent:str,filter_by_keywords=[],filter_by_statements=[],stemming=False) -> dict:
    """
    Getting search hits of a term in Wikidata
    search_term: str a term or a phrase to search in Wikidata
    lang: str with language code; for example, 'en' or 'nl';
    # (see language codes in Wikidata: https://www.wikidata.org/w/api.php?action=help&modules=wbgetentities)
    user_agent: str with user-agent's info; required by Wikidata (see: https://meta.wikimedia.org/wiki/User-Agent_policy)
    filter_by_keywords: list optional;  the keywords to exclude from the search results; default is []
    filter_by_statements: list optional; list of tuples with statements to exclude from the search results, specifying property and its value like [('P31','Q5'),('P31', 'Q16521')]
    # (meaning that entities with the property P31 ("instance of") with the values "Q5" ("human") and "Q16521" ("taxon") will be excluded);
    # multiple statements are possible, separate them with a whitespace; default is ''
    stemming: bool is to perform stemming of the search term (works only for English); default is False
    Returns a dict
    """

    search_hits = {}

    # 'query' with 'search' generator: constant params
    url = "https://www.wikidata.org/w/api.php"
    params = {"action":"query",
              "prop":"entityterms",
              "wbetlanguage":lang,
              "generator":"search",
              "gsrsearch":f'"{search_term}"', # term goes here (quotes for stemming off)
              "gsrlimit":"1", # 1 result is enough to get the hits info
              "gsrinfo":"totalhits",
              "format":"json"}
    headers = {"user-agent":user_agent}

    # stemming
    if stemming == True:
        params["gsrsearch"] = search_term

    # filtering by keywords
    if filter_by_keywords != []:
        keyword_str = ''
        for kw in filter_by_keywords:
            keyword_str = keyword_str + f" -{kw}"
        params["gsrsearch"] = params["gsrsearch"] + keyword_str

    # filtering by statements    
    if filter_by_statements != []:
        statements_str = ''
        for t in filter_by_statements:
            statements_str = statements_str + f" -haswbstatement:{t[0]}={t[1]}"
        params["gsrsearch"] = params["gsrsearch"] + statements_str

    r = requests.get(url,params=params,headers=headers)
    hits = r.json()['query']['searchinfo']['totalhits']
    search_hits[search_term] = hits

    return search_hits


def get_lit_by_term(search_term:str,lang:str,user_agent:str,filter_by_keywords=[],filter_by_statements=[],stemming=False) -> dict:
    """
    Getting Qids, their labels, aliases, descriptions by a query term; to support stemming, set stemming=True
    search_term: str a term or a phrase to search in Wikidata
    lang: str with language code; for example, 'en' or 'nl';
    # (see language codes in Wikidata: https://www.wikidata.org/w/api.php?action=help&modules=wbgetentities)
    user_agent: str with user-agent's info; required by Wikidata (see: https://meta.wikimedia.org/wiki/User-Agent_policy)
    filter_by_keywords: list optional;  the keywords to exclude from the search results; default is []
    filter_by_statements: list optional; list of tuples with statements to exclude from the search results, specifying property and its value like [('P31','Q5'),('P31', 'Q16521')]
    # (meaning that entities with the property P31 ("instance of") with the values "Q5" ("human") and "Q16521" ("taxon") will be excluded);
    stemming: bool is to perform stemming of the search term (works only for English); default is False
    Returns a dict
    """

    # 'query' with 'search' generator: constant params
    url = "https://www.wikidata.org/w/api.php"
    params = {"action":"query",
              "prop":"entityterms",
              "wbetlanguage":lang,
              "generator":"search",
              "gsrsearch":f'"{search_term}"', # quotes for stemming off
              "gsrlimit":"max", # getting all results
              "gsroffset":"0", # offset
              "gsrinfo":"totalhits",
              "gsrsort":"incoming_links_desc", # sorting results by incoming links
              "format":"json",} 
    headers = {"user-agent":user_agent}

    results = {} # dict to store the results

    # stemming
    if stemming == True:
        params["gsrsearch"] = search_term # stemming on
    
    # filtering by keywords
    if filter_by_keywords != []:
        keyword_str = ''
        for kw in filter_by_keywords:
            keyword_str = keyword_str + f" -{kw}"
        params["gsrsearch"] = params["gsrsearch"] + keyword_str

    # filtering by statements    
    if filter_by_statements != []:
        statements_str = ''
        for t in filter_by_statements:
            statements_str = statements_str + f" -haswbstatement:{t[0]}={t[1]}"
        params["gsrsearch"] = params["gsrsearch"] + statements_str    
    
    # counter for offset
    gsroffset = 0

    # sending requests
    w = requests.get(url,params=params,headers=headers)
    wikidata_json = w.json()
    time.sleep(2) # to prevent 502
        
    # checking the number of hits
    hits = wikidata_json['query']['searchinfo']['totalhits']
        
    # if there are no results
    if hits == 0:
        results[search_term] = wikidata_json['query']
        loops = 0
            
    # saving results from the first loop
    else:
        results[search_term] = wikidata_json['query']['pages']

    # - CONDITIONS FOR LOOPS- #

    # if there are less than 500 hits for a term, no loops are needed
    if hits < 500:
        loops = 0

    # 10K is max; and if hits > 500, offset is needed
    if 10000 > hits > 500 and hits % 500 > 0:
        loops = hits // 500
        
    # minus one loop if there's no remainder
    if 10000 > hits > 500 and hits % 500 == 0:
        loops = hits // 500 - 1
        
    # as the first loop is already done, max = 19
    if hits > 10000:
        loops = 19

    # - REQUEST LOOPS - #   

    for i in range(0,loops):
        gsroffset = gsroffset + 500
        # setting the offset and sending a new request
        params["gsroffset"] = f"{gsroffset}"
        w_i = requests.get(url,params=params,headers=headers)
        wikidata_json_i = w_i.json()
        
        # saving the results
        results[search_term].update(wikidata_json_i['query']['pages'])
        time.sleep(2)

    return results


def get_lit_by_q(qids:list,lang:str,user_agent:str) -> list:
    
    """
    Getting labels, aliases, descriptions of Wikidata entities by their Qids
    qids: list of entity IDs (str) (requests 50 entities at a time slicing the list)
    lang: str with language code; for example, 'en' or 'nl';
    (see language codes in Wikidata: https://www.wikidata.org/w/api.php?action=help&modules=wbgetentities)
    user_agent: str with user-agent's info; required by Wikidata (see: https://meta.wikimedia.org/wiki/User-Agent_policy)
    Returns a list of dicts: [{'QID': {'type': '',
                     'id': 'QID',
                     'labels': {'lang': {'language': 'lang', 'value': ''}},
                     'descriptions': {'lang': {'language': 'lang','value': ''}},
                     'aliases': {'lang': [{'language': 'lang', 'value': ''}]
    """
    
    wd_results = []

    # 'wbgetentities' constant params
    url = "https://www.wikidata.org/w/api.php"
    params = {"action":"wbgetentities",
              "ids":"", # string of entities (max=50)
              "props":"labels|aliases|descriptions",
              "languages":lang,
              "format":"json"}
    headers = {"user-agent":user_agent}

    # - N LOOPS - #

    # if there's a remainder
    if len(qids) % 50 > 0:
        loops = len(qids) // 50 + 1 # add another loop for requests
    else:
        loops = len(qids) // 50

    # - REQUEST LOOPS - #   

    # counters to slice qids

    start_quid_str = 0
    end_quid_str = 0

    for i in range(0,loops):
        ids_string = "" # putting Qs in one string
        end_quid_str = end_quid_str + 50 # max 50 entities per request

        for q in qids[start_quid_str:end_quid_str]:
            ids_string = ids_string + f"{q}|"

        start_quid_str = start_quid_str + 50

        # updating params

        params["ids"] = ids_string.rstrip("|")

        # sending a request
        d = requests.get(url,params=params,headers=headers)
        literals = d.json()

        for qid, value in literals['entities'].items():
            wd_results.append({qid:value})

    return wd_results


def get_labels_by_q(qids:list,lang:list,user_agent:str) -> dict:

    """
    Getting labels of entities by QIDs
    qids: list of entities' QIDs (str) to work on;
    lang: list of str with language code; for example, ['en','nl'];
    (see language codes in Wikidata: https://www.wikidata.org/w/api.php?action=help&modules=wbgetentities)
    user_agent: str with user-agent's info; required by Wikidata (see: https://meta.wikimedia.org/wiki/User-Agent_policy)
    Returns a dict: {"labels":dict with labels by lang,"failed":list of QIDs that were failed}
    """

    # 'wbgetentities' constant params
    url = "https://www.wikidata.org/w/api.php"
    params = {"action":"wbgetentities",
              "ids":"", # string of entities (max=50)
              "props":"labels", # only labels
              "format":"json"}
    headers = {"user-agent":user_agent}

    request = {}
    failed_entities = []

    # languages
    if len(lang) > 1:
        languages = ''
        for l in lang:
            languages = languages + f"{l}|"
        # updating params
        params["languages"] = languages.rstrip("|")
    else:
        params["languages"] = lang[0]

    # - N LOOPS - #

    # if there's a remainder
    if len(qids) % 50 > 0:
        loops = len(qids) // 50 + 1 # add another loop for requests
    else:
        loops = len(qids) // 50

    # - REQUEST LOOPS - #   

    # counters to slice qids

    start_quid_str = 0
    end_quid_str = 0

    for i in range(0,loops):
        ids_string = "" # putting Qs in one string
        end_quid_str = end_quid_str + 50 # max 50 entities per request

        for q in qids[start_quid_str:end_quid_str]:
            ids_string = ids_string + f"{q}|"

        start_quid_str = start_quid_str + 50

        # updating params

        params["ids"] = ids_string.rstrip("|")

        # sending a request
        d = requests.get(url,params=params,headers=headers)
        labels = d.json()

        if 'entities' in labels:
            for entity,lbl in labels['entities'].items():
                per_lang = {}
                for l in lang:
                    if 'labels' in lbl:
                        if l in lbl['labels']:
                            per_lang[l] = lbl['labels'][l]['value']

                request[entity] = per_lang

            # to prevent server errors    
            time.sleep(2)

        else:
            failed_entities.extend(qids[start_quid_str:end_quid_str])

    results = {"labels":request,"failed":failed_entities}

    return results

def _claims_parse_properties(query_results:dict, QID:str, propepties:list) -> dict:
    """
    Parses the values of the properties of entities from Wikidata response,
    for example: get the values of the property P31 for the entity Q104534511;
    query_results: dict, Wikidata response in json format;
    QID: str, only 1 QID;
    properties: list of str; for example ['P31','P279'];
    Return a dict {'QID': {'property_ID':{'property_value': ''}}};
    The empty value of the property_value is intended for its label, which is queried using another function
    """
    dict_per_qid = {}
    dict_per_qid[QID] = {}
    
    for p in propepties:

        dict_per_qid[QID][p] = {}
        if 'missing' not in query_results['entities'][QID].keys():
            claims_per_qid = query_results['entities'][QID]['claims']
            # getting property values
            if p in claims_per_qid:
                for i in claims_per_qid[p]:
                    if 'datavalue' in i['mainsnak']:
                        dict_per_qid[QID][p][i['mainsnak']['datavalue']['value'].get('id')] = ""
                    
    return dict_per_qid

def get_claims(qids:list, propepties:list, user_agent:str, path='') -> str:

    """
    Getting claims by QIDs and properties
    qids: list of entities (str) to work on, if len > 50, results will be saved in batches (separate files)
    properties: list of str; for example ['P31','P279']; getting claims only with the properties specified in this list
    user_agent: str with user-agent's info; required by Wikidata (see: https://meta.wikimedia.org/wiki/User-Agent_policy)
    path: optional; str path where to save json files (including '/');
    Saves the request results in json files due to large size;
    Returns str when files are saved and whether there are failed entities;
    Saves failed entities (due to request errors) in a separate txt file;
    Uses another function (_claims_parse_properties) to parse the indicated properties from the request results
    """

    # 'wbgetentities' constant params
    url = "https://www.wikidata.org/w/api.php"
    params = {"action":"wbgetentities",
              "ids":"", # string of entities (max=50)
              "props":"claims",
              "format":"json"}
    headers = {"user-agent":user_agent}

    failed_entities = []

    # - N LOOPS - #

    # if there's a remainder
    if len(qids) % 50 > 0:
        loops = len(qids) // 50 + 1 # add another loop for requests
    else:
        loops = len(qids) // 50

    # - REQUEST LOOPS - #   

    # counters to slice qids

    start_quid_str = 0
    end_quid_str = 0

    for i in range(0,loops):
        
        results = {}

        ids_string = "" # putting Qs in one string
        end_quid_str = end_quid_str + 50 # max 50 entities per request

        for q in qids[start_quid_str:end_quid_str]:
            ids_string = ids_string + f"{q}|"

        start_quid_str = start_quid_str + 50

        # updating params
        params["ids"] = ids_string.rstrip("|")

        # sending a request
        d = requests.get(url,params=params,headers=headers)
        claims = d.json() # claims per request

        if 'entities' in claims:
            for entity in claims['entities']:
                results.update(_claims_parse_properties(claims,entity,propepties))

            # - SAVING RESULTS IN BATCHES - #
    
            with open(f'{path}claims_{start_quid_str}.json', 'w') as json_file:
                json.dump(results, json_file)
            # to prevent server errors
            time.sleep(2)

        else:
            failed_entities.extend(qids[start_quid_str:end_quid_str])

    if len(failed_entities) > 0:
        with open(f'{path}failed_entities.txt','w') as txt_file:
            for q in failed_entities:
                txt_file.writelines(f"{q}\n")
        output_str = f"Requests are saved in {path}. There are {len(failed_entities)} failed entities, see the .txt file"
    else:
        output_str = f"Requests are saved in {path}"

    return output_str

def find_where_query_term_appears(query_results_path:str, lang:str) -> dict:
    """
    Finding where a target term appears in the search results: label, description, or aliases
    query_results_path: str, the path to the search results  (the output of 'get_lit_by_term'), including '/'
    lang – str language string ("en" or "nl") corresponding to the results language of 'get_lit_by_term'
    Returns dict with info about every hit and where a term was found
    """
    
    # importing query results
    with open(query_results_path,'r') as jf:
        query_results = json.load(jf)

    target_terms_dict_wikidata = {}

    for query_term, hits in query_results.items():
        
        results_per_query_term = []

        for page_id, values in hits.items():
            if 'entityterms' in values:
                
                # checking labels
                if 'label' in values['entityterms']:
                    if len(re.findall(f'\\b{query_term}\\b',values['entityterms']['label'][0],re.IGNORECASE)) > 0:
                        dict_per_hit = {}
                        dict_per_hit['query_term'] = query_term
                        dict_per_hit['lang'] = lang
                        dict_per_hit['QID'] = values['title']
                        dict_per_hit['prefLabel'] = values['entityterms']['label'][0]
                        dict_per_hit['aliases'] = values['entityterms'].get('alias')
                        dict_per_hit['description'] = values['entityterms'].get('description')
                        dict_per_hit['index'] = values['index']
                        dict_per_hit['found_in'] = 'prefLabel'
                        results_per_query_term.append(dict_per_hit)
                        
                # checking aliases        
                if 'alias' in values['entityterms']:
                    for a in values['entityterms']['alias']:
                        if len(re.findall(f'\\b{query_term}\\b',a,re.IGNORECASE)) > 0:
                            dict_per_hit = {}
                            dict_per_hit['query_term'] = query_term
                            dict_per_hit['lang'] = lang
                            dict_per_hit['QID'] = values['title']
                            if values['entityterms'].get('label') != None:
                                dict_per_hit['prefLabel'] = values['entityterms']['label'][0]
                            else:
                                dict_per_hit['prefLabel'] = None
                            dict_per_hit['aliases'] = values['entityterms']['alias']
                            dict_per_hit['description'] = values['entityterms'].get('description')
                            dict_per_hit['index'] = values['index']
                            dict_per_hit['found_in'] = 'aliases'
                            results_per_query_term.append(dict_per_hit)
                            
                # checking descriptions            
                if 'description' in values['entityterms']:
                    if len(re.findall(f'\\b{query_term}\\b',values['entityterms']['description'][0],re.IGNORECASE)) > 0:
                        dict_per_hit = {}
                        dict_per_hit['query_term'] = query_term
                        dict_per_hit['lang'] = lang
                        dict_per_hit['QID'] = values['title']
                        if values['entityterms'].get('label') != None:
                            dict_per_hit['prefLabel'] = values['entityterms']['label'][0]
                        else:
                            dict_per_hit['prefLabel'] = None
                        dict_per_hit['aliases'] = values['entityterms'].get('alias')
                        dict_per_hit['description'] = values['entityterms']['description'][0]
                        dict_per_hit['index'] = values['index']
                        dict_per_hit['found_in'] = 'description'
                        results_per_query_term.append(dict_per_hit)
                        
        target_terms_dict_wikidata[query_term] = results_per_query_term

    return target_terms_dict_wikidata


def filter_proper_names(dataset_path:str, lang:str, path:'') -> str:
    """
    Filtering out proper names in the search results
    dataset_path: str, the path to the search results with claims ('results_w_claims_[lang].json')
    lang: str, the lang of the search results ('en' or 'nl')
    path: optional; str path where to save json files (including '/');
    Saves a json file with search results without proper names (results_clean_[lang].json)
    Returns a status str with N of filtered out entities
    """

    # importing results w claims
    with open(dataset_path,'r') as jf:
        dataset = json.load(jf)

    results_clean = {}
    n_filtered = 0

    if lang == 'en':
        Q5_value = 'human'
    if lang == 'nl':
        Q5_value = 'mens'

    for query_term,results in dataset.items():
        results_clean[query_term] = []
        for hit in results:
            count_Q5 = 0
            for p in hit['instance_of']:
                    if p == Q5_value:
                        count_Q5 += 1

            if hit['prefLabel'] != None and len(re.findall(f"\\b{hit['query_term'].capitalize()}\\b",hit['prefLabel'])) > 0 and count_Q5 > 0:
                n_filtered += 1

            else:
                results_clean[query_term].append(hit)

    with open(f"{path}results_clean_{lang}.json","w") as jf:
        json.dump(results_clean, jf)
                
    return f"File is saved. {n_filtered} entities are filtered out."


def get_bows(path_to_results:str, lang:str) -> dict:
    '''
    Getting bag of words (BoW) from the Wikidata search results for every search term
    path_to_results: str, a path to the search results (in json format)
    lang: str, 'en' or 'nl'
    Returns a dict with BoWs per hit per term: {term:[{QID:['token1','token2','token3']}]}
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
            
            if hit["prefLabel"] != None:
                literals.append(hit["prefLabel"]) # adding prefLabel

            if hit["found_in"] == "prefLabel" or hit["found_in"] == "aliases":
                literals.extend(hit["instance_of"])
                literals.extend(hit["subclass_of"])

            if hit["aliases"] != None:
                literals.extend(hit["aliases"]) # adding aliases

            # adding descriptions
            # descriptions can be str or list
            # None doesn't add
            if type(hit["description"]) == str:
                literals.append(hit["description"])
                
            if type(hit["description"]) == list:
                literals.extend(hit["description"])
            #print(literals)    
            bow = bows.make_bows(literals,lang,merge_bows=True)
                
            q_bag[hit["QID"]] = bow

            list_by_term.append(q_bag)

        all_bows[query_term] = list_by_term
        
    return all_bows


def get_lit_related_matches_bow(lang:str) -> dict:
    '''
    Generates dict with BoWs by query terms and their related matches in Wikidata
    reads files with Wikidata BoWs: gzip_wd_bows_en.json (EN), gzip_wd_bows_nl.json (NL)
    the info about which QID is a related match to the query term is taken from https://github.com/cultural-ai/wordsmatter/blob/main/related_matches/rm.csv
    lang: str, 'en' or 'nl'
    Returns a dict with BoWs by term: {term:{QID:['token1','token2','token3']}}
    '''
    
    results = {}
    
    # loading related matches
    path_rm = "https://github.com/cultural-ai/wordsmatter/raw/main/related_matches/rm.json"
    rm = requests.get(path_rm).json()
    
    # load wd bows
    path_to_bows = f"https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/Wikidata/gzip_wd_bows_{lang}.json"
    wd_bow = requests.get(path_to_bows).json()

    # getting a list of all QIDs of related matches in Wikidata
    related_matches_wd_qid = list(set([values["related_matches"]["wikidata"][0] for values in rm.values() \
                     if values["lang"] == lang and values["related_matches"]["wikidata"][0] != 'None']))    
    # getting BoWs for QIDs
    related_matches_wd_qid_bows = {}
    for q_id_rm in related_matches_wd_qid:
        for hits in wd_bow.values():
            for hit in hits:
                for q_id, bow in hit.items():
                    if q_id == q_id_rm:
                        related_matches_wd_qid_bows[q_id] = bow
                        
    # shaping resulting dict: terms with related matches and BoWs
    for values in rm.values():
        if values["lang"] == lang:
            rm_wd = values["related_matches"]["wikidata"][0]
            if rm_wd != "None":
                for term in values["query_terms"]:
                    if rm_wd in related_matches_wd_qid_bows.keys():
                        results[term] = {"QID":rm_wd,"bow":related_matches_wd_qid_bows[rm_wd]}
            
    return results

def get_cs(lang:str):
    '''
    Calculating three cosine similarity scores between Wikidata search results and background info;
    the similarity scores are based on (1) only related matches, (2) only WM text, and (3) extended bows with related matches and WM text
    lang:str, language of bows, "en" or "nl"
    Returns a pandas data frame with columns:
    query_term, QID, bow, cs_rm, cs_wm, cs_rm_wm
    '''

    nlp = bows.load_spacy_nlp(lang)

    # load bckground info
    path_bg = "https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/bg/background_info_bows.json"
    bg_info = requests.get(path_bg).json()

    wikidata_df = pd.DataFrame(columns=['term','hit_id','bow','cs_rm','cs_wm','cs_rm_wm'])

    # load wd bows
    path_wd_bows = f"https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/Wikidata/gzip_wd_bows_{lang}.json"
    wikidata_bows = requests.get(path_wd_bows).json()

    for term, hits in wikidata_bows.items():

        bg_rm = bows._collect_bg(term,lang,bg_info,bg_bow="rm")
        bg_wm = bows._collect_bg(term,lang,bg_info,bg_bow="wm")
        bg_rm_wm = bows._collect_bg(term,lang,bg_info,bg_bow="joint")
          
        # if there are search results
        if len(hits) > 0:
            for hit in hits:
                for i, bow in hit.items():
                    # making a set
                    wd_bow = list(set(bow))
                    
                    if len(wd_bow) > 0:
                        # calculate cs
                        cs_rm = bows.calculate_cs(bg_rm,wd_bow,nlp)
                        cs_wm = bows.calculate_cs(bg_wm,wd_bow,nlp)
                        cs_rm_wm = bows.calculate_cs(bg_rm_wm,wd_bow,nlp)
                        
                        wikidata_df.loc[len(wikidata_df)] = [term,i,wd_bow,cs_rm,cs_wm,cs_rm_wm]
                    
                    # if there are no tokens, all cs = None
                    else:
                        wikidata_df.loc[len(wikidata_df)] = [term,i,wd_bow,None,None,None]

        # if there are no search results in Wikidata, cs = None
        else:
            wikidata_df.loc[len(wikidata_df)] = [term,None,None,None,None,None]

    return wikidata_df


def get_n_hits_by_properties(path_to_results:str, lang:str, group_by_lemma=False):
    '''
    Getting N of hits of query terms by properties in Wikidata
    with optional grouping by lemmas
    path_to_results: str, path to a json file with results (query results or annotated entities)
    lang: str, language of results, "en" or "nl"
    group_by_lemma: bool, if group N hits by lemma, default False (count by query term)
    Requires the file with query terms "query_terms.json"
    Returns a pandas dataframe
    '''
    # importing query terms with lemmas
    # loading query terms
    path_query_terms = "https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/query_terms.json"
    query_terms = requests.get(path_query_terms).json()
    
    with open(path_to_results,'r') as jf:
        wd_results = json.load(jf)
        
    n_occurences_by_query_term = pd.DataFrame(columns=["lemma","query_term","lang","wd_prefLabel","wd_aliases","wd_descr","wd_qt_total"])

    for term, hits in wd_results.items():
        # property counters
        pref = 0
        alias = 0
        descr = 0
        
        for hit in hits:
            if hit["found_in"] == "prefLabel":
                pref += 1
            if hit["found_in"] == "aliases":
                alias += 1
            if hit["found_in"] == "description":
                descr += 1
        
        total_count_by_qt = pref + alias + descr
                
        # getting lemma of a query term
        for l, wordforms in query_terms[lang].items():
                if term in wordforms:
                    lemma = l
        
        data = [lemma,term,lang,pref,alias,descr,total_count_by_qt]
        n_occurences_by_query_term.loc[len(n_occurences_by_query_term)] = data
        
        results_to_return = n_occurences_by_query_term
                
    if group_by_lemma == True:
        
        n_occurences_by_lemma = pd.DataFrame(columns=["lemma","lang","wd_prefLabel","wd_aliases","wd_descr","wd_lemma_total"])
        
        for group in n_occurences_by_query_term.groupby('lemma'):
            row = [group[0],lang,sum(group[1]['wd_prefLabel']),sum(group[1]['wd_aliases']),\
              sum(group[1]['wd_descr']),sum(group[1]['wd_qt_total'])]
            n_occurences_by_lemma.loc[len(n_occurences_by_lemma)] = row
            
        results_to_return = n_occurences_by_lemma
        
    return results_to_return
