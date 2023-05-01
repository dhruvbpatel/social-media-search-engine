#!/usr/bin/env python
# coding: utf-8

# In[1]:


import re
import collections
import heapq

import numpy as np
from nltk.corpus import stopwords
from nltk import PorterStemmer

import pprint
import json

# import pysolr
# from getSolrData import get_results_from_solr


# In[2]:


def tokenize_doc(doc_text, stop_words):
    # doc_text = doc_text.replace('\n', ' ')
    # doc_text = " ".join(re.findall('[a-zA-Z]+', doc_text))
    # tokens = doc_text.split(' ')
    tokens = []
    text = doc_text
    text = re.sub(r'[\n]', ' ', text)
    text = re.sub(r'[,-]', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub('[0-9]', '', text)
    text = text.lower()
    tkns = text.split(' ')
    tokens = [token for token in tkns if token not in stop_words and token != '' and not token.isnumeric()]
    return tokens


# In[3]:


def build_association(id_token_map, vocab, query):
    association_list = []
    print("query :",query)
    for i, voc in enumerate(vocab):
        for word in query.split(' '):
            c1, c2, c3 = 0, 0, 0
            for doc_id, tokens_this_doc in id_token_map.items():
                count0 = tokens_this_doc.count(voc)
                count1 = tokens_this_doc.count(word)
                c1 += count0 * count1
                c2 += count0 * count0
                c3 += count1 * count1
            c1 /= (c1 + c2 + c3)
            if c1 != 0:
                association_list.append((voc, word, c1))

    return association_list


# In[4]:


def association_main(query, solr_results):


    solr_list = []

    for result in solr_results:
        if 'content' in result:
            solr_list.append(result)

    solr_results = solr_list
    print(len(solr_list))
    print("query ass main: ",query)

    stop_words = set(stopwords.words('english'))
    
    tokens = []
    token_counts = {}
    tokens_map = {}
    # tokens_map = collections.OrderedDict()
    document_ids = []

    for result in solr_results:
        tokens_this_document = tokenize_doc(result['content'], stop_words)
        tokens_map[result['digest']] = tokens_this_document
        tokens.append(tokens_this_document)

    vocab = set([token for tokens_this_doc in tokens for token in tokens_this_doc])
    association_list = build_association(tokens_map, vocab, query)
    association_list.sort(key = lambda x: x[2],reverse=True)
    # print("association: ",association_list)
    i=1;
    while(i<5):
        query += ' '+str(association_list[i][0])
        i +=1
    return 'content: (' + query + ')'


# In[5]:
# def convert_to_solr_query(query):

#     q = query.split(" ")
#     print("q: ", q)

#     # if len(q)==1:
#     #     return query

#     query = ' OR '.join(filter(lambda x: x.isalnum(), q))
#     if query.endswith(" OR "):
#         query = query[:-4]
#     return 'content: (' + query + ')' #+ 'OR url:' + query + 

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
#     ans_list.append(association_main(query, results))


# print(ans_list)



# data = []
# with open('solr_data_500.json', 'r', encoding="utf8") as f:
#     # Load JSON data as a list of dictionaries
#     data = json.load(f)

# doc_list = data["response"]["docs"]
# documents = []
# for doc in doc_list:
#     if "content" in doc:
#         documents.append(doc)


# # In[6]:


# query="social"


# # In[7]:


# queryRes = association_main(query, documents)
# print(queryRes)


# # In[ ]:





# # In[ ]:





# %%
