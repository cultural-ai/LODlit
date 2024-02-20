# How Contentious Terms About People and Cultures are Used in Linked Open Data
## The repository of the research paper

[Online Appendix](https://cultural-ai.github.io/ContentiousTermsLOD)

### Data

* We reuse the previously developed [knowledge graph of contentious terminology](https://doi.org/10.1007/978-3-031-33455-9_30);
* From the knowledge graph, we extract culturally sensitive terms to inspect them in LOD-datasets; the process is in the notebook [getting_query_terms.ipynb](getting_query_terms.ipynb), the resulting file is [query_terms.json](query_terms.json); there are 75 EN and 82 NL canonical forms of terms, which are linked to their inflected forms (for example, "aboriginal" and "aboriginals"); with both canonical and inflected forms, there are 154 EN and 242 NL terms;
* We query terms in four LOD datasets:
  * Wikidata (EN and NL);
  * The Getty Art & Architechture Thesaurus (AAT) (EN and NL);
  * Princeton WordNet (version 3.1) (only EN);
  * Open Dutch WordNet (version 1.3) (only NL);
  
* For details on querying each dataset, refer to Jupyter notebooks in the corresponding directories:
  * [Wikidata](Wikidata)
  * [AAT](AAT)
  * [PWN](PWN)
  * [ODWN](ODWN)

### Sets constructed for analysis

  #### Set 1: literlas of resources from the Words Matter Knowledge Graph (or related matches)
  * see [get_literals_set_2.ipynb](get_literals_set_2.ipynb); for the analysis of related matches, refer to [rm](rm)
  #### Set 2: all retrieved literals
  * all retrieved literals by datasets are in the corresponding directories with the suffix '_query_results_{lang}.json'; for [Wikidata](Wikidata), there are multiple compressed json files: (1) initial search results 'gzip_search_results_{lang}.json', (2) claims (for example, P31 or P279) of the retrieved entities 'gzip_results_with_claims_{lang}.json', (3) filtered results used for analysis 'gzip_results_clean_{lang}.json'
  #### Set 3: disambiguated literals
  * [samples](samples) contains (1) samples for annotations by dataset and language, (2) background information for each term presented to annotators, (3) annotated samples with the prefix "ann_" and IDs of annotators (1 and 3); the notebook [samples.ipynb](samples.ipynb) generates 6 csv files with samples and calculates inter-annotator agreement for each annotated sample; the mean of these agreement scores (0.8) is reported in the section 4.3; 


### Markers of contentiousness

The directory [markers](markers) contains results for RQ2, whether contentious terms in literals have any markers of their contentiousness and if so, what these markers are and how they are given. We define two groups of markers: (1) [implicit](markers/implicit) markers given in text of literals next to contentious terms and (2) [explicit](markers/explicit) markers, which are specific properties with URIs.

### Other directories and files

* [n_hits](n_hits) contains 36 csv files with number of terms' hits in the three sets by property values; the code to generate these files is in the notebook [n_hits.ipynb](n_hits.ipynb);

### LODlit module

The LODlit Python module allows querying terms in Wikidata, AAT, PWN, and ODWN.
LODlit can be used to both reproduce our research results and retrieve literals from the LOD datasets for other purposes.
Read more in the [LODlit repository](https://github.com/cultural-ai/LODlit).
  
### Paper footnotes

* \[13]: The list of exluded categories in Wikidata is in the file [statements_filter.json](Wikidata/statements_filter.json);
* \[13]: The number of search results from Wikidata before and after filtering is in the file [n_entities_by_term.csv](Wikidata/n_entities_by_term.csv), the number of retrieved entities (<= 10K) is in [n_entities_retrieved_by_term.csv](Wikidata/n_entities_retrieved_by_term.csv); the number of **entities** after filtering proper names out (Set 1) is in [n_entities_clean_by_term.csv](Wikidata/n_entities_clean_by_term.csv) and the number of **hits** by canonical forms is in [n_hits_by_lemma.csv](Wikidata/n_hits_by_lemma.csv);
* \[16]: See the functions we added to parse ODWN in [OpenDutchWordnet](https://github.com/cultural-ai/OpenDutchWordnet) (the modules 'le' and 'lemma')
* \[17]: The Jupyter notebook (experimenting_with_wsd.ipynb)(cs/experimenting_with_wsd.ipynb) demonstrates our attempts to use common token overlap scores and cosine similarity scores with different background information to disambiguate literals.

### Citation

Andrei Nesterov, Laura Hollink, and Jacco van Ossenbruggen. 2024. How Contentious Terms About People and Cultures are Used in Linked Open Data. In Proceedings of the ACM Web Conference 2024 (WWW ’24), May 13–17, 2024, Singapore, Singapore. ACM, New York, NY, USA, 11 pages. https://doi.org/10.1145/3589334.3648140

[Download BibTeX](ContentiousTermsLOD.bib)