from getSolrData import get_results_from_solr
import numpy as np
from collections import Counter
from nltk.tokenize import wordpunct_tokenize
from nltk.corpus import stopwords
from string import punctuation
import nltk
nltk.download('stopwords')

class Rocchio:
    '''
    1. Written by Arpit Singh for Moutains Search Engine on April 29th, 2023.
    2. The following class implements the famous rocchio algorithm.
    3. The inputs for the class is the initial query that needs to be expanded.
    4. REQUIRED - Solr running on local host is required to fetch results for the initial query
    5. The output for the class is the expanded query with max 5 terms in it.
    '''

    def __init__(self, query) -> None:
        """
        1.  The constructor for the class takes the initial query as a single parameter.
        2.  Then it sets the value for alpha, beta & gamma which are experimentally derived.
        3.  Gets results from the Solr for the initial query using a method present in getSolrData.py
        """
        self.alpha = 1
        self.beta = 0.5
        self.gamma = 0.1
        self.query = query


        self.query_response = get_results_from_solr("text:({})".format(query), 50)
        solr_list = []

        for result in self.query_response:
            if 'content' in result:
                solr_list.append(result)

        self.query_response = solr_list
        # solr_results = solr_list
        # print(len(solr_list))
        # print("query rochio main: ",self.query_response)

        self.relevant_results_threshold = 10
        self.english_stopwords = stopwords.words("english")

    def get_tokens(self, text) -> list:
        """
        1.  The get_tokens function returns a list of tokens that are not punctuations & stopwords.
        2.  Input to the function is String.
        """
        words =  wordpunct_tokenize(text.lower())
        wordsFiltered = []
        for w in words:
            if w not in punctuation and w not in self.english_stopwords:
                wordsFiltered.append(w)
        return wordsFiltered

    def get_document_data(self):
        '''
        1.  For every document fetched from solr it tokenizes the content present in the document.
        2.  Creates a dictionary of documents & tokens inside the documents.
        3.  Creates a vocab list that contains all the tokens in the collection of documents.
        4.  Returns the document dictionary as document_dict, and the vocab list as total_doc_terms
        '''
        document_dict = {}
        total_doc_terms = []

        for docId, doc in enumerate(self.query_response):
            doc_content = self.get_tokens(doc['content'])
            total_doc_terms.extend(doc_content)
            document_dict[docId] = doc_content
        total_doc_terms = list(set(total_doc_terms))

        url_list = []

        for i in range(10):
            response = self.query_response[i]['url']
            url_list.append(response)
        
        print(url_list)




        return document_dict, total_doc_terms
    
    def get_relevant_irrelevant_documents(self, document_dict):
        '''
        1.  Out of the max 50 documents fetched from Solr, it splits the 50 results into two parts.
        2.  It sets the top 10 documents fetched to relevant_results.
        3.  Sets the rest of documents fetched to irrelevant_results.
        '''
        relevant_results = []
        irrelevant_results = []

        rel_urls = []
        irrel_urls = []

        for docId in document_dict:
            if docId <= self.relevant_results_threshold:
                relevant_results.append(document_dict[docId])
            else:
                irrelevant_results.append(document_dict[docId])

        return relevant_results, irrelevant_results
    
    def get_document_vector(self, total_doc_terms, document_list):
        '''
        1.  To create a document vector it takes input the total vocab of collection & the list of relevant/irrelevant results.
        2.  Starts iterating over each documents present inside the document list.
        3.  Creates a numpy array of zeroes of size = total vocab of collection.
        4.  The it iterates over term in the document, and counts how many times it was present.
        5.  At the index of that term in the list it stores the count of that term.
        6.  Returns the document vector which is 2D Array.
        '''
        document_vector = []

        for docs in document_list:
            vec = np.zeros(len(total_doc_terms))
            for term in docs:
                count = docs.count(term) 
                vec[total_doc_terms.index(term)] = count
            document_vector.append(vec)

        return document_vector
    
    def get_query_vector(self, total_doc_terms):
        '''
        1.  Tokenize the query using get_tokens function
        2.  Creates a query vector using same method used in get_document_vector
        3.  Returns the query vector which is 1D Array.
        '''
        query_list = self.get_tokens(self.query)
        count_total_doc_terms = Counter(total_doc_terms)
        vec = np.zeros(len(total_doc_terms))

        for term in query_list:
            vec[total_doc_terms.index(term)] = count_total_doc_terms[term]
        vector_query = vec

        return vector_query
    
    def get_rocchio_expanded_query(self):
        '''
        1.  Calls all the above functions and gets the respective data.
        2.  Calculate the exapnded query using the optimized query formula.
        3.  The expanded query returns a list of float values.
        4.  Sort expanded query list in descending order & gets the top 5 values.
        5.  Returns the list as a string.
        '''

        document_dict, total_doc_terms = self.get_document_data()
        relevant_documents, irrelevant_documents = self.get_relevant_irrelevant_documents(document_dict)
        relevant_document_vector = self.get_document_vector(total_doc_terms, relevant_documents)
        irrelevant_document_vector = self.get_document_vector(total_doc_terms, irrelevant_documents)
        query_vector = self.get_query_vector(total_doc_terms)

        # print("rel: ",relevant_documents['url'])
        # print("irrel: ",irrelevant_documents)

        expanded_query = (self.alpha * query_vector) + (self.beta * sum(relevant_document_vector) / len(relevant_document_vector)) - (self.gamma * sum(irrelevant_document_vector) / len(irrelevant_document_vector))
        
        top_n_terms = 5
        max_terms_indices = expanded_query.argsort()[-top_n_terms:][::-1]
        
        Query_terms_Added = []
        for i in max_terms_indices:
            Query_terms_Added.append(total_doc_terms[i])

        return " ".join(Query_terms_Added)
        

rocchio = Rocchio("instagram")

user_query = [
    "instagram",
    'hashtags',
    "reddit",
    "twitter",
    "snapchat",
    "pinterest",
    "trending",
    "viral video",
    "tiktok",
    "clickbait",
    "reels",
    "social media marketing",
    "social bookmarking",
    "live streaming",
    "influencer",
    "pay per click",
    "sponsored post",
    "engagement",
    "social networking",
    "community",
    "linkedin",
    "networking community",
    "microblogging",
    "online forum"
]




q_list = []

for i in range(len(user_query)):
    q = user_query[i]
    
    print("current query: ",q)
    rocchio = Rocchio(q)
    rocchio.get_rocchio_expanded_query()
    q_list.append(rocchio.get_rocchio_expanded_query())

print(q_list)
print("Expanded Query By Rocchio --> ", rocchio.get_rocchio_expanded_query())