

import re
import numpy as np
from nltk.corpus import stopwords
from nltk import PorterStemmer
from tqdm import tqdm
# from getSolrData import get_results_from_solr, parse_solr_results
# import pysolr
# from getSolrData import get_results_from_solr


porter_stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))

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

def get_scalar_cluster(doc_tokens, token_2_stem, stem_2_tokens, query):
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

    # frequency of stems in each document
    f = np.zeros((len(doc_tokens), len(stems)), dtype=np.int32)
    for doc_id, tokens in enumerate(doc_tokens):
        for token in tokens:
            if token in token_2_stem:
                stem = token_2_stem[token]
                stem_idx = stem_2_idx[stem]
                f[doc_id, stem_idx] += 1

    # correlation matrix
    c = np.dot(f.T, f) # (#_of_stems, #_of_stems)
    c_diag = np.expand_dims(np.diag(c), axis=0) # extract all c_{u,u} shape: (1, #_of_stems)

    # normalize correlation matrix
    s = c / (c + c_diag + c_diag.T) # (#_of_stems, #_of_stems)
    s_norm = np.linalg.norm(s, axis=1) # (#_of_stems,)

    # expand query
    query_expands_id = []
    for token in query:
        stem = token_2_stem[token]
        stem_id = stem_2_idx[stem]

        # calculate cosine simialrity for the token with all other stems
        stem_vec = np.expand_dims(s[stem_id, :], axis=0)
        stem_norm = np.linalg.norm(stem_vec)
        s_stem = np.dot(stem_vec, s.T).squeeze() # (#_of_stems,)
        s_stem = (s_stem / stem_norm) / s_norm # cosine similarity

        # pick the top 3 stems for each query token
        idx_sort = np.argsort(s_stem)[::-1] # sort decreasing by score
        idx_sort = idx_sort[:2]
        query_expands_id.extend(idx_sort.tolist())

    # convert stem ids to stem
    query_expands = []
    for stem_idx in query_expands_id:
        query_expands.append(stems[stem_idx])

    return query_expands

def scalar_main(query, solr_results):
    """
    Args:
        query(str): a text string of query
        solr_results(list): result for the query from function 'get_results_from_solr'
    Return:
        query(str): a text string of expanded query
    """
    # query = 'Michael Phelps'
    # solr = pysolr.Solr('http://localhost:8983/solr/nutch/', always_commit=True, timeout=10)
    # results = get_results_from_solr(query, solr)
    vocab = set()
    doc_tokens = []

    # tokenize query and query results, then build vocabulary
    if 'content:' == query[:8]:
        query = query[8:]
    query_text = query # keep original query text
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
    query_expands_stem = get_scalar_cluster(doc_tokens, token_2_stem, stem_2_tokens, query)
    # convert from stem to tokens
    query_expands = set()
    for stem in query_expands_stem:
        query_expands.update(list(stem_2_tokens[stem]))
    # generate new query
    for token in query:
        query_expands.discard(token)
    query.extend(list(query_expands))
    query = ' '.join(query)

    #print('Expanded query:', query)
    query = 'content: (' + query + ')' #is for end

    return query

def get_documents(solr_results):
    documents = []
    for doc in solr_results:
        if "content" in doc:
            documents.append(doc)
    return documents

# #Function start
# query = "green moutains united states of america"
# solr_query_format = "content:({})".format(query)
# solr_results = get_results_from_solr(solr_query_format, 500)
# solr_results = parse_solr_results(solr_results)
# documents = get_documents(solr_results)
# expanded_query = scalar_main(query, documents)
# print(expanded_query)


# def convert_to_solr_query(query):

#     q = query.split(" ")
#     print("q: ", q)

#     # if len(q)==1:
#     #     return query

#     query = ' OR '.join(filter(lambda x: x.isalnum(), q))
#     if query.endswith(" OR "):
#         query = query[:-4]
#     return 'content: (' + query + ')' #+ 'OR url:' + query + 


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
#     ans_list.append(scalar_main(query, results))


# print(ans_list)

