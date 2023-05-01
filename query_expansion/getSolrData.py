import pysolr
import re
from flask import request, jsonify

solr = pysolr.Solr('http://localhost:8983/solr/nutch/', always_commit=True, timeout=10)

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

# solr_results = get_results_from_solr("text:(+mountain)", 10)
# #
# result = parse_solr_results(solr_results)
#
# print(type(result))
# for r in result:
#     # print(r["content"], "\n\n")
#     print(r, "\n\n")