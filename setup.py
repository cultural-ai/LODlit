from setuptools import setup

setup(
    name='LODlit',
    version='0.5.0',    
    description = "Retrieving literal values from LOD",
    author = "Andrei Nesterov",
    author_email = "nesterov@cwi.nl",
    license = "CC BY 4.0",
    keywords = ["LOD", "literals", "linked open data", "strings", "NLP"],
    url='https://github.com/cultural-ai/LODlit/tree/main/LODlit_package',
    install_requires=[
        'nltk==3.8.1',
	    'pandas==2.0.3',
	    'numpy==1.21.0',
	    'requests==2.31.0',
	    'simplemma==0.9.1',
	    'spacy==3.6.1',
	    'SPARQLWrapper==2.0.0',
	    'lxml==4.9.3'])