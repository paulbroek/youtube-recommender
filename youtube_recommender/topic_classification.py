"""
	topic_classification.py

	where topic_modelling_*.py files use `topic modelling` to determine topics through unsupervised learning,
	this file determines topics through supervised learning, that is, given topics

	explains the difference between Modeling and Classification very well:
		https://datascience.stackexchange.com/questions/962/what-is-difference-between-text-classification-and-topic-models

	more help:
		https://wandb.ai/authors/Kaggle-NLP/reports/Kaggle-s-NLP-Text-Classification--VmlldzoxOTcwNTc
		https://www.dataquest.io/blog/tutorial-text-classification-in-python-using-spacy/
		https://medium.com/analytics-vidhya/nlp-tutorial-for-text-classification-in-python-8f19cd17b49e
		https://realpython.com/python-keras-text-classification/
	
	todo:
		- select a topic collection model
		- predict topics for every caption, with probabilities per topic
"""

from functools import partial
import pandas as pd

import spacy

from utils.nlp import clean_up
from settings import SPACY_MODEL, CAPTIONS_PATH

# load spacy model and dataset
nlp = spacy.load(SPACY_MODEL)
data = pd.read_feather(CAPTIONS_PATH)

clean_up = partial(clean_up, nlp=nlp)
datalist = data.text.map(clean_up)

raise NotImplementedError
