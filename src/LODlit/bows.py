# Functions to make bag-of-words from strings, collect background information, and  calculare cosine similarity
# To use 'calculate_cs', download 'en_core_web_lg' and 'nl_core_news_lg' from https://spacy.io/models:
# python -m spacy download en_core_web_lg AND python -m spacy download nl_core_news_lg

import json
import re
import requests
import math
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import simplemma
import spacy # numpy version 1.21

def main():
    if __name__ == "__main__":
        main()

def make_bows(text:list, lang:str, merge_bows=False) -> list:
    '''
    Makes a BoW from a list of str:
    removes non-word charachters (incl. punctuation, numbers),
    removes stop-words (nltk),
    lowercases, tokenises (split by space), lemmatises (NLTK lemmatiser for EN; simplemma for NL),
    removes tokens with fewer than 3 characters;
    text: a list of str to make BoWs from
    lang: str, language of strings, 'en' or 'nl'
    merge_bows: bool, if there are multiple texts, merge them in one BoW (True) or not (False), default False 
    Returns a BoW (list of lists)
    '''
    
    wnl = WordNetLemmatizer()

    bows = []
    
    for t in text:
        no_w_text = re.sub('(\W|\d)',' ',t)
        text_bow = no_w_text.split(' ')
        
        # checking lang
        if lang == 'en':
            text_bow_clean = [wnl.lemmatize(token.lower()) for token in text_bow if token.lower() not in stopwords.words('english') and token != '' and len(token) > 2]
        if lang == 'nl':
            # Dutch lemmatizer can output uppercase lemmas
            text_bow_clean = [simplemma.lemmatize(token.lower(),lang='nl').lower() for token in text_bow if token.lower() not in stopwords.words('dutch') and token != '' and len(token) > 2]
            
        if merge_bows == True:
            bows.extend(text_bow_clean)
        else:
            bows.append(text_bow_clean)
            
    return bows


def tf(doc:list, token:str) -> float:
    '''
    Calculates term frequency (TF)
    doc: list, all documents
    token: str, a token to get the TF score of
    Returns float
    '''
    n_found = len([t for t in doc if t == token])
    tf_score = n_found / len(doc)
    
    return tf_score


def idf(token:str, doc_freq:dict, n_docs:int) -> float:
    '''
    Calculates inverse document frequency (IDF):
        adds 1 to DF to avoid zero division
    token: str, a token to get the IDF score of
    doc_freq: dict, document frequency, in how many documents tokens appear
    n_docs: int, a number of documents
    Returns float
    '''
    idf_score = math.log(n_docs / (doc_freq[token] + 1))
        
    return idf_score


def get_top_tokens_tfidf(bow:list,doc_freq:dict,n_docs:int) -> list:
    '''
    Getting top tokens based on their TF-IDF weighting in one BoW
    Depends on the tf and idf functions
    bow: list of str, tokens in one BoW
    doc_freq: dict, document frequency, in how many documents tokens appear ({'token':int})
    n_docs: int, a number of documents
    Returns list: top 10 tokens in a bow by their TF-IDF scores
    '''
    top_tokens = []
    tf_idf_scores = {}
    
    for token in bow:
        tf_idf = tf(bow,token) * idf(token,doc_freq,n_docs)
        tf_idf_scores[token] = tf_idf
        
    tokens_scores = sorted(tf_idf_scores.items(), key=lambda x:x[1], reverse=True)
    
    if len(tokens_scores) < 10:
        top_tokens = [t[0] for t in tokens_scores]
    else:
        top_tokens = [t[0] for t in tokens_scores[0:10]]
    
    return top_tokens

def load_spacy_nlp(lang:str):
    '''
    Loads an NLP pipeline from spacy for terms vectorisation;
    lang: str, language of the strings to process, 'en' or 'nl';
    before loading, download 'en_core_web_lg' and 'nl_core_news_lg' from https://spacy.io/models
    
    '''
    # check lang
    if lang == "en":
        nlp = spacy.load("en_core_web_lg", disable=["tagger", "attribute_ruler", "lemmatizer"])

    # load nl model    
    if lang == "nl":
        nlp = spacy.load("nl_core_news_lg", disable=["tagger", "attribute_ruler", "lemmatizer"])

    return nlp

def calculate_cs(bow_1:list, bow_2:list, nlp) -> float:
    '''
    Calculates cosine similarity between two bags of words;
    based on the spacy vectors
    bow_1 and bow_2: list, two bags of words;
    nlp: spacy nlp class loaded through spacy.load; use the function 'load_spacy_nlp'
    '''

    # converting list to str, spaces as a separator

    bow_1_str = ""
    for t in bow_1:
        bow_1_str += f"{t} "
        
    bow_2_str = ""
    for t in bow_2:
        bow_2_str += f"{t} "
        
    bow_1 = nlp(bow_1_str)
    bow_2 = nlp(bow_2_str)
        
    sim = bow_1.similarity(bow_2)
    
    return sim


def _collect_bg(term:str, lang:str, bg_info:dict, bg_bow:str) -> list:
    '''
    Collects bacgkround info for a term
    term: str, a term to get backgrounf info for
    lang: str, lang of the term, "en" or "nl"
    bg_info: dcit with background info (loads in "get_cs" functions)
    bg_bow: str, indicates which background info to collect;
        options for bg_bow: (1) "rm" -- related matches from all resources, not including Words Matter texts, (2) "wm" -- only Words Matter text, (3) "joint" -- related matches + Words Matter
    Returns a list of unique tokens from the background info of a term
    '''

    if term in bg_info[lang].keys():
        bg = []

        if bg_bow == "rm":

            if bg_info[lang][term].get("aat"):
                bg.extend(bg_info[lang][term]["aat"])
            
            if bg_info[lang][term].get("wikidata"):
                bg.extend(bg_info[lang][term]["wikidata"])

            if lang == "en":
                if bg_info[lang][term].get("pwn"):
                    bg.extend(bg_info[lang][term]["pwn"])
            if lang == "nl":
                if bg_info[lang][term].get("odwn"):
                    bg.extend(bg_info[lang][term]["odwn"])

        if bg_bow == "wm":

            if bg_info[lang][term].get("wm"):
                bg.extend(bg_info[lang][term]["wm"])

        if bg_bow == "joint":

            if bg_info[lang][term].get("aat"):
                bg.extend(bg_info[lang][term]["aat"])
            
            if bg_info[lang][term].get("wikidata"):
                bg.extend(bg_info[lang][term]["wikidata"])

            if lang == "en":
                if bg_info[lang][term].get("pwn"):
                    bg.extend(bg_info[lang][term]["pwn"])
            if lang == "nl":
                if bg_info[lang][term].get("odwn"):
                    bg.extend(bg_info[lang][term]["odwn"])

            if bg_info[lang][term].get("wm"):
                bg.extend(bg_info[lang][term]["wm"])
            
        bg_set = list(set(bg))

    else:
        bg_set = []

    return bg_set

def _vectorize_bows(bow_1:list, bow_2:list) -> int:
    '''
    Vectorizing two BoWs
    based on common token overlap in two sets of tokens
    Calculating cosine similarity between them
    bow_1 and bow_2: list, bag of words
    Returns int, rounded cosine similarity value
    '''
    # creating sets
    set_1 = {t for t in bow_1}
    set_2 = {t for t in bow_2}
    union_set = set_1.union(set_2)
    
    # vectorizing
    v1 = []
    v2 = []
    for t in union_set:
        if t in set_1:
            v1.append(1)
        else:
            v1.append(0)
        if t in set_2:
            v2.append(1)
        else:
            v2.append(0)
    
    # calculating cs 
    c = 0
    for i in range(len(union_set)):
        c += v1[i] * v2[i]

    cos_sim = c / float((sum(v1) * sum(v2)) ** 0.5)
    
    return cos_sim


def get_top_10(cs_table_path:str, metric:str, lang:str, groupby='lemma'):
    '''
    Getting top-10 results (max 10) (entities) for every query term based on a metric
    cs_table_path: str, path to the csv table with cosine similarity scores, see the files '[dataset]_[lang]_cs.csv'; for example, 'aat_en_cs.csv'; wikidata en cs is zipped;
    metric: str, which metric to take to get top-10
        options for metric: (1) "cs_rm" -- only related matches, (2) "cs_wm" -- only WM text, and (3) "cs_rm_wm" -- extended bows with related matches and WM text
    lang: str, 'en' or 'nl'; language of the dataset in teh csv table 
    groupby: str, 'lemma' or 'term'; how to group entities to generate Top-10; 'lemma' is default  
    Returns a pandas data frame (a subset of cs_table) with ranked results per term or per lemma
    '''

    top_10 = pd.DataFrame()
    cs_table = pd.read_csv(cs_table_path)

    if groupby == 'term':
        # dropping duplicates (taking only unique entities for top-10)
        cs_table.drop_duplicates(subset=["term","hit_id"], inplace=True)

        for group in cs_table.groupby("term"):
            top_10 = top_10.append(group[1].sort_values(by=metric, ascending=False)[0:10])

    if groupby == 'lemma':

        # loading query terms
        path_query_terms = "https://github.com/cultural-ai/ContentiousTermsLOD/raw/main/query_terms.json"
        query_terms = requests.get(path_query_terms).json()

        # insert the lemmas column
        lemmas = []
        for row in cs_table.iterrows():
            for lemma, wordforms in query_terms[lang].items():
                if row[1]['term'] in wordforms:
                    lemmas.append(lemma)

        cs_table.insert(0,"lemma",lemmas)

        # drop duplicates
        cs_table.drop_duplicates(subset=["lemma","hit_id"], inplace=True)

        for group in cs_table.groupby("lemma"):
            top_10 = top_10.append(group[1].sort_values(by=metric, ascending=False)[0:10])

    return top_10

