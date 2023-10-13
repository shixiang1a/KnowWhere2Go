from elasticsearch import Elasticsearch 
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from tqdm import tqdm
from gensim.summarization import bm25
import os
import json

class Retriever:
    def __init__(self, index_name):
        self.es = Elasticsearch(hosts=[{'host': 'localhost', 'port': 9200}])
        self.index_name = index_name
        if not self.es.indices.exists(index_name):
            self.es.indices.create(index=index_name)
            self.es.indices.put_mapping(
                index=index_name,
                body={
                    "properties": {
                        "document": {
                            "type": "text"
                        },
                        "url": {
                            "type": "keyword"
                        }
                    }
                },
            )
        self.count = len(self.es.search(index=index_name, body={"query": {"match_all": {}}})['hits']['hits'])
    
    def insert(self, doc):
        self.es.index(index=self.index_name, id=self.count + 1, body=doc)
        self.count += 1
    
    def insert_many(self, docs):
        for doc in docs:
            self.insert(doc)
    
    def delete(self, id):
        self.es.delete(index=self.index_name, id=id)
    
    def delete_all(self):
        self.es.delete_by_query(index=self.index_name, body={"query": {"match_all": {}}})
    
    def index(self, id):
        self.es.indices.refresh(index=self.index_name)
        return self.es.get(index=self.index_name, id=id)
    
    def search(self, query, size=10):
        if "site:" not in query:
            body = {
                "query": {
                    "match": {
                        "document": query
                    }
                },
                "size": size
            }
        else:
            text_query = query.split("site:")[0].strip()
            url_query = query.split("site:")[1].strip()
            body = {
                "query": {
                    "bool": {
                    "must": [
                        {"match":{"document": text_query}},
                        {"wildcard":{"url": {"value": url_query + "*"}}
                    }
                    ]
                    },
                },
                "size": size
            }
        res = self.es.search(index=self.index_name, body=body)
        return res['hits']['hits']


class Bm25_retriever:
    def __init__(self, size):
        self.size = size
    
    def retrieve(self, query, docs):
        scores = self.bm25Model.get_scores(nltk.word_tokenize(query))
        best_n_doc_idx = np.argsort(scores)[-self.size:][::-1]
        doc = [docs[int(idx)] for idx in best_n_doc_idx]
        return doc

class Tfidf_retriever:
    def __init__(self, size):
        self.size = size
        self.tf_idf = TfidfVectorizer()
    
    def retrieve(self, query, docs):
        tfidf_docs = self.tf_idf.fit_transform([doc for doc in docs])
        tfidf_query = self.tf_idf.transform([query])[0]
        similarities = [cosine_similarity(tfidf_doc, tfidf_query) for tfidf_doc in tfidf_docs]
        best_n_doc_idx = np.argsort(similarities)[-self.size:][::-1]
        doc = [docs[int(idx)] for idx in best_n_doc_idx]
        score = [similarities[int(idx)] for idx in best_n_doc_idx]
        return doc, score


class local_retriever:
    def __init__(self, retriever_name, size):
        if retriever_name == "bm25":
            self.retriever =  Bm25_retriever(size)
        elif retriever_name == "tfidf":
            self.retriever = Tfidf_retriever(size)
        else:
            raise NotImplementedError
    
    def retrieve(self, query, docs):
        return self.retriever.retrieve(query, docs)
    
    


if __name__ == "__main__":
    retriever = Retriever("web_search")
    print(retriever.es.search(index="web_search", body={"query": {"match":{"document": "{What is the \"natural\" sleeping position for humans}"}}}))
    # body = {
    #     "query": {
    #         "bool": {
    #         "must": [
    #             {"match":{"document": "a"}},
    #             {"wildcard":{"url": {"value": "https://docs.devexpress.com/*"}}
    #         }
    #         ]
    #     },
    #     },
    #     "size":1
    # }
    # print(retriever.es.search(index="web_search", body=body))

    # 数据存储
    # dir_list = os.listdir("/data_share/data/RedPajama-Data-1T/c4")
    # for dir in tqdm(dir_list[12:24]):
    #     file = open("/data_share/data/RedPajama-Data-1T/c4/" + dir, "r", encoding="utf-8")
    #     for line in tqdm(file.readlines()):
    #         line = json.loads(line)
    #         doc = {"document": line["text"], "url": line["meta"]["url"]}
    #         retriever.insert(doc)




