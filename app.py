
import flask
from flask_cors import CORS
import pysolr
import re
import os
from flask import request, jsonify
import json
from query_expansion.AssociationClustering import association_main
from query_expansion.MetricCluster import metric_cluster_main
from query_expansion.ScalarClustering import scalar_main
from spellchecker import SpellChecker

spell = SpellChecker()
solr = pysolr.Solr('http://localhost:8983/solr/nutch', always_commit=True, timeout=10)

app = flask.Flask(__name__)
CORS(app)
app.config["DEBUG"] = True


@app.route('/api/v1/indexer', methods=['GET'])
def get_query():
    expanded_query=""
    print("args: ", request.args)
    if 'query' in request.args and 'type' in request.args:
        query = str(request.args['query'])
        type =  str(request.args['type'])
        total_results = 20
        
        
        if type == "association_qe" or type == "metric_qe" or type == "scalar_qe":
            total_results = 20
        print('query: ',query)

        solr_query = convert_to_solr_query(query)
        solr_results = get_results_from_solr(solr_query, total_results)


        print("solr query: ",solr_query)

        print("solr_results: ",solr_results)
        api_resp = parse_solr_results(solr_results)

        if type == "page_rank":
            result = api_resp
        elif "clustering" in type:
            result = get_clustering_results(api_resp, type)
        elif type == "hits":
            result = get_hits_results(api_resp)
        elif type == "association_qe":
            
            # query = solr_query
            # query = spell.correction(query)
            expanded_query = association_main(query, solr_results)
            solr_res_after_qe = get_results_from_solr(expanded_query, 20)
            api_resp = parse_solr_results(solr_res_after_qe)
            result = api_resp
        elif type == "metric_qe":
            # query = spell.correction(query)
            expanded_query = metric_cluster_main(query, solr_results)
            solr_res_after_qe = get_results_from_solr(expanded_query, 20)
            api_resp = parse_solr_results(solr_res_after_qe)
            result = api_resp
        elif type == "scalar_qe":
            query = solr_query
            # query = spell.correction(query)
            print("query indexer: ",query)
            expanded_query = scalar_main(query, solr_results)

            

            solr_res_after_qe = get_results_from_solr(expanded_query, 20)
            
            api_resp = parse_solr_results(solr_res_after_qe)
            result = api_resp

        

        if expanded_query is None:
            expanded_query=" "
        
        print(expanded_query)

        res = {
            "result":result,
            "expanded_query":expanded_query
        }

        
        return jsonify(res)
    

    else:
        return "Error: No query or type provided"

def convert_to_solr_query(query):

    q = query.split(" ")
    print("q: ", q)

    query = ' OR '.join(filter(lambda x: x.isalnum(), q))
    if query.endswith(" OR "):
        query = query[:-4]
    return 'content: (' + query + ')' 


def get_results_from_solr(query, no_of_results):
    results = solr.search(query, search_handler="/select", **{
        "wt": "json",
        "rows": no_of_results
    })
    return results


def parse_solr_results(solr_results):
    if solr_results.hits == 0:
        return jsonify("query out of scope")
    else:
        api_resp = list()
        rank = 0
        for result in solr_results:
            rank += 1
            title = ""
            url = ""
            content = ""
            if 'title' in result:
                title = result['title']
            if 'url' in result:
                url = result['url']
            if 'content' in result:
                content = result['content']
                meta_info = content[:200]
                meta_info = meta_info.replace("\n", " ")
                meta_info = " ".join(re.findall("[a-zA-Z]+", meta_info))
            link_json = {
                "title": title,
                "url": url,
                "meta_info": meta_info,
                "rank": rank
            }
            api_resp.append(link_json)
    return api_resp


def get_clustering_results(clust_inp, param_type):
    if param_type == "flat_clustering":
        f = open('clustering\precomputed_clusters\clustering_kmeans.txt')
        lines = f.readlines()
        f.close()
    elif param_type == "single_hierarchical_clustering":
        f = open('clustering\precomputed_clusters\single_clustering.txt')
        lines = f.readlines()
        f.close()
    elif param_type == "avg_hierarchical_clustering":
            f = open('clustering\precomputed_clusters\\average_clustering.txt')
            lines = f.readlines()
            f.close()
    

    cluster_map = {}
    for line in lines:
        line_split = line.split(",")
        if line_split[1] == "":
            line_split[1] = "99"
        cluster_map.update({line_split[0]: line_split[1]})

    for curr_resp in clust_inp:
        curr_url = curr_resp["url"]
        curr_cluster = cluster_map.get(curr_url, "99")
        curr_resp.update({"cluster": curr_cluster})
        curr_resp.update({"done": "False"})

    clust_resp = []
    curr_rank = 1
    for curr_resp in clust_inp:
        if curr_resp["done"] == "False":
            curr_cluster = curr_resp["cluster"]
            curr_resp.update({"done": "True"})
            curr_resp.update({"rank": str(curr_rank)})
            curr_rank += 1
            clust_resp.append({"title": curr_resp["title"], "url": curr_resp["url"],
                               "meta_info": curr_resp["meta_info"], "rank": curr_resp["rank"]})
            for remaining_resp in clust_inp:
                if remaining_resp["done"] == "False":
                    if remaining_resp["cluster"] == curr_cluster:
                        remaining_resp.update({"done": "True"})
                        remaining_resp.update({"rank": str(curr_rank)})
                        curr_rank += 1
                        clust_resp.append({"title": remaining_resp["title"], "url": remaining_resp["url"],
                                           "meta_info": remaining_resp["meta_info"], "rank": remaining_resp["rank"]})

    return clust_resp


def get_hits_results(clust_inp):
    authority_score_file = open("HITS/precomputed_scores/authority_score_1", 'r').read()
    authority_score_dict = json.loads(authority_score_file)

    clust_inp = sorted(clust_inp, key=lambda x: authority_score_dict.get(x['url'], 0.0), reverse=True)
    return clust_inp


app.run(port='5000')

