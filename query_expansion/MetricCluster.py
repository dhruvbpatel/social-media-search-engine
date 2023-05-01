#!/usr/bin/env python
# coding: utf-8

# In[1]:


import re
from collections import Counter

import numpy as np
from nltk.corpus import stopwords
from nltk import PorterStemmer


import json
from tqdm import tqdm

# import pysolr
# from getSolrData import get_results_from_solr


# In[2]:


porter_stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))


# In[3]:


def tokenize_text(text):
    """
    Args:
        text(str): a string of text

    Return:
        tokens(list): a list of cleaned tokens
    """
    tokens = []
    text = re.sub(r'[\n]', ' ', text) # remove enters
    text = re.sub(r'[,-]', ' ', text) # remove comma and dash
    text = re.sub('[0-9]', '', text) # remove all numbers
    text = re.sub(r'[^\W\w\s]', '', text) # only keep A-Za-z_ and space
    text = text.lower()
    tkns = text.split()
    # double check, remove empty tokens, stop words, and full numeric tokens
    tokens = [token for token in tkns if token not in stop_words and token != '' and not token.isnumeric()]
    return tokens


# In[4]:


def make_stem_map(vocab):
    """
    Args:
        vocab(list): a list of vocabulary

    Returns:
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
    """
    token_2_stem = {} # 1 to 1
    stem_2_tokens = {} # 1 to n

    for token in vocab:
        stem = porter_stemmer.stem(token)
        if stem not in stem_2_tokens:
            stem_2_tokens[stem] = set()
        stem_2_tokens[stem].add(token)
        token_2_stem[token] = stem

    return token_2_stem, stem_2_tokens


# In[5]:


def get_metric_clusters(doc_tokens, token_2_stem, stem_2_tokens, query):
    """
    Args:
        doc_tokens(2-D list): tokens in each documents having structure:
                              [[token_1, token_2, ...], [...], ...]
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
        query(list): a list of tokens from query
        
    Return:
        query_expands(list): list of expand stem tokens ids for each token in the query
    """
    # build map from stem to index
    stems = stem_2_tokens.keys()
    stems = list(sorted(stems))
    stem_2_idx = {s:i for i, s in enumerate(stems)}

    # print('Vocab:', token_2_stem.keys())
    # print('Stems:', stem_2_idx.keys())

    # count the number of variants for each stem
    stem_len = [len(stem_2_tokens[s]) for s in stems]
    stem_len = np.array(stem_len)

    # build correlation matrix
    # c = np.zeros((len(stem_2_idx), len(stem_2_idx)), dtype=np.int)
    c = np.zeros((len(stem_2_idx), len(stem_2_idx)))
    for doc_id, tokens in enumerate(doc_tokens):
        tokens_count = Counter(tokens)
        # for each documents, count the difference between each pair of tokens
        # and add them to their corresponding stems
        for token_1, count_1 in tokens_count.items():
            stem_1 = token_2_stem[token_1]
            stem_1_id = stem_2_idx[stem_1]
            for token_2, count_2 in tokens_count.items():
                stem_2 = token_2_stem[token_2]
                stem_2_id = stem_2_idx[stem_2]
                if stem_1 == stem_2:
                    continue
                if count_1 != count_2:
                    c[stem_1_id, stem_2_id] += 1. / abs(count_1 - count_2)

    # normalize correlation matrix and pick the top 3 expansion tokens
    query_expands_id = []
    for token in query:
        stem = token_2_stem[token]
        stem_id = stem_2_idx[stem]

        # normalize correlation matrix
        s_stem = c[stem_id, :] / (stem_len[stem_id] * stem_len)

        # pick the top 3 stems for each query token
        s_stem = np.argsort(s_stem)[::-1] # sort decreasing by score
        s_stem = s_stem[:2]
        query_expands_id.extend(s_stem.tolist())

    # convert stem ids to stem
    query_expands = []
    for stem_idx in query_expands_id:
        query_expands.append(stems[stem_idx])

    return query_expands


# In[6]:


def metric_cluster_main(query, solr_results):
    """
    Args:
        query(str): a text string of query
        solr_results(list): result for the query from function 'get_results_from_solr'

    Return:
        query(str): a text string of expanded query
    """
    # query = 'olympic medal'
    # solr = pysolr.Solr('http://localhost:8983/solr/nutch/', always_commit=True, timeout=10)
    # results = get_results_from_solr(query, solr)

    solr_list = []

    for result in solr_results:
        if 'content' in result:
            solr_list.append(result)

    solr_results = solr_list
    print(len(solr_list))
    print("query ass main: ",query)

    vocab = set()
    doc_tokens = []

    # tokenize query and query results, then build stem
    if 'content:' == query[:8]:
        query = query[8:]
    query_text = query
    query = tokenize_text(query)
    vocab.update(query)
    for result in tqdm(solr_results, desc='Preprocessing results'):
        if 'content' not in result:
            tokens = []
        else:
            tokens = tokenize_text(result['content'])
        doc_tokens.append(tokens)
        vocab.update(tokens)

    vocab = list(sorted(vocab))
    token_2_stem, stem_2_tokens = make_stem_map(vocab)

    # expand query
    query_expands_stem = get_metric_clusters(doc_tokens, token_2_stem, stem_2_tokens, query)
    # convert from stem to tokens
    query_expands = set()
    for stem in query_expands_stem:
        query_expands.update(list(stem_2_tokens[stem]))
    # generate new query
    for token in query:
        query_expands.discard(token)
    query.extend(list(query_expands))
    query = ' '.join(query)

    print('Expanded query:', query)
    query = 'content: (' + query + ')'


    return query


# In[7]:

# def convert_to_solr_query(query):

#     q = query.split(" ")
#     print("q: ", q)

#     # if len(q)==1:
#     #     return query

#     query = ' OR '.join(filter(lambda x: x.isalnum(), q))
#     if query.endswith(" OR "):
#         query = query[:-4]
#     return 'content: (' + query + ')'  


# query = 'olympic medal'
# solr = pysolr.Solr('http://localhost:8983/solr/nutch/', always_commit=True, timeout=10)

# user_query = ['meta', 'facebook', 'instagram', 'hashtags', 'reddit', 'twitter', 'snapchat', 'pinterest',
#       'trending', 'viral video', 'tiktok', 'clickbait', 'reels',"work life balance", 'social media marketing',
#         'social bookmarking', 'live streaming', 'influencer', 'pay per click', 'sponsored post', 'engagement', 'social networking',
#           'community', 'linkedin', 'networking community', 'microblogging', 'online forum', 'Social media algorithms']


# ans_list = []

# for i in range(len(user_query)):
#     query = user_query[i]
#     # print(query)
#     solr_query = convert_to_solr_query(query)
#     # solr_query = query
#     # print(solr_query)
#     results = get_results_from_solr(solr_query, 20)
#     ans_list.append(metric_cluster_main(query, results))


# print(ans_list)




# data = []
# with open('solr_data_5000.json', 'r', encoding="utf8") as f:
#     # Load JSON data as a list of dictionaries
#     data = json.load(f)

# doc_list = data["response"]["docs"]
# documents = []
# for doc in doc_list:
#     if "content" in doc:
#         documents.append(doc)


# # In[8]:


# query="social"


# # In[9]:


# queryRes = metric_cluster_main(query, documents)
# print(queryRes)

