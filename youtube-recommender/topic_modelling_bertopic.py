"""
inspired by:
	https://www.holisticseo.digital/python-seo/topic-modeling/
"""

import pandas as pd
from bertopic import BERTopic

data = pd.read_feather("data/captions.feather")
topic_model = BERTopic()
