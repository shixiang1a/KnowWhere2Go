import sys
sys.path.append("./")
import re
import logging
from utils.search import Operator
from utils.utils import cut_page, url_to_domain
import json
from retriever.retriever import Tfidf_retriever

####################### Resource Optimizer #######################
# This class is responsible for optimizing the sources
# Three source optimization methods: (1) call the self critical method of the model, (2) call the online search engine, (3) call the record of the local source pool


class SourceOptimizer:
    def __init__(self, config, model=None, source_pool=None, evidence_model=None, validator=None):
        self.config = config
        # if method is not in the above three methods, an exception is thrown
        if  self.config.optimizer not in ['self_critical', 'online', 'history']:
            raise Exception('No such method')
        self.model = model
        # self.model.load_multiple_adapters([self.config.correct_lora_weights], ["correct"])
        self.op = Operator()
        # initialize log
        logging.basicConfig(filename=self.config.log_dir + "KW2G.log", level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # evidence finder
        self.evidence_model = evidence_model
        # source pool
        self.source_pool = source_pool
        
        self.validator = validator
        self.retriever = Tfidf_retriever(1)

    # log
    def log(self, query, time):
        self.logger.info({'query': query, 'state': 'complete', 'time': time})
    

    # evidence finder
    def evidence_finder(self, query, split_sentences):
        return self.validator.evidence_finder(query, split_sentences)
    
    # url recognition
    def url_recognition(self, web):
        url = self.model.generate("generator", self.config.url_instruction, web)
        return url


    # optimize method: self critical
    def self_critical(self, query, negative_source_list, source_list):
        # self.model.switch_adapter("correct")
        updated_web, updated_url = [], []
        # add numbers to the source list according to the index 
        source = ""
        for no in range(len(source_list)):
            source += str(no + 1) + ". " + source_list[no] + " "
        
        updated_evidence = {"hrefs": [], "evidences": []}
        
        for negative_source in negative_source_list:
            input = "[Query] " + query + "\n" + "[Website] " + source.strip() + "\n" + "[Suggestion] " + "{} is inaccessible or does not include content that meets the needs of user".format(negative_source)
            # generate optimized recommendation list
            updated_source = self.model.generate("optimizer", self.config.critical_instruction, input)
            # Optimized recommendation list
            updated_source = updated_source.split('[Corrected Website]')[1].strip()
            # remove the number and restore to list
            # 1. 2. 3. 4. 5. 6. 7. 8. 9. 10.
            pattern = re.compile(r'\d+\. ')
            updated_source = pattern.sub('[SEP]', updated_source)
            updated_source = [i.strip() for i in updated_source.split('[SEP]')]
            url = self.url_recognition("[Webiste] " + updated_source[-1]).split("[URL]")[1].strip()
            if url == "This page does not exist":
                source = ""
                for no in range(len(updated_source[:-1])):
                    source += str(no + 1) + ". " + updated_source[no] + " "
                updated_source = updated_source[:-1]
                continue

            if self.config.online_check_after_self_critical:

                res = self.validator.validate(query, query + " site:" + url, 'online')
                res = json.loads(res)
                if len(res['evidences']) > 0:
                    updated_evidence['hrefs'] += res['hrefs']
          
                    updated_evidence['evidences'] += res['evidences']
                    source = ""
                    updated_web.append(updated_source[-1])
                    updated_url.append(url)
                    for no in range(len(updated_source)):
                        source += str(no + 1) + ". " + updated_source[no] + " "
                else:
                    source = ""
                    for no in range(len(updated_source[:-1])):
                        source += str(no + 1) + ". " + updated_source[no] + " "
                    updated_source = updated_source[:-1]
            else:
                source = ""
                for no in range(len(updated_source)):
                    source += str(no + 1) + ". " + updated_source[no] + " "
                updated_web.append(updated_source[-1])
                updated_url.append(url)
        
        # {query: query, source_list: source_list, updated_source_list: updated_source_list}
        self.logger.info({'query': query, 'updated_source_list': updated_web})
        return updated_web, updated_url, updated_evidence
    

    # optimize method: online search
    def online_search(self, query):
        # search sources from Bing
        searched_results = self.op.search(query)
        if len(searched_results) == 0:
            # print("no results found in Bing for query: " + query)
            return [], [], {"hrefs": [], "evidences": []}
        max_page_per_query = min(self.config.max_page_per_query, self.op.get_page_num())
        updated_url_list, hrefs, evidences = [], [], []
        for page_idx in range(max_page_per_query):
            # print("Enter WebPage：" + searched_results[page_idx]["name"] + "\n")
            href, page_detail = self.op.load_page(page_idx)
            if page_detail is None:
                # print("your connection fails, no page rendered")
                continue
            if len(page_detail) == 0:
                # print("page no content, continue \n")
                continue
            # evidence finder
            split_sentences = cut_page(searched_results[page_idx]["name"] + '. ' + page_detail, self.config.segment_method, self.config.segment_length)
            if len(split_sentences) > 100:
                continue
            evidence = self.evidence_finder(query, split_sentences)
            if len(evidence) > 0:
                evidences.append(evidence)
                hrefs.append(href)
                # use domain name instead of url
                updated_url_list.append(href.split(url_to_domain(href))[0] + url_to_domain(href) + "/")
      
        # enerate optimized recommendation list
        if len(updated_url_list) > 0:
            # {query: query, source_list: source, updated_source_list: updated_source_list}
            self.logger.info({'query': query, 'updated_source_list': updated_url_list})
            return updated_url_list, {"hrefs": hrefs, "evidences": evidences}
        else:
            # print("no new sources found, continue")
            self.logger.info({'query': query, 'updated_source_list': []})
            return [], {"hrefs": [], "evidences": []}
    

    # optimize method: history mining
    def offline_search(self, query, negative_source_list, source_list):
        # search the most similar query source
        updated_web_list, updated_url_list = [], []
        updated_evidence = {"hrefs": [], "evidences": []}

        # use mongodb to GET query_web data
        # source_collection = self.source_pool.get_source_collection()
        # similar_data = source_collection.find({'$text': {'$search': query}}).sort([('query', 1)]).limit(1)
        # similar_data = list(similar_data)
        # if len(similar_data) > 0:
        #     similar_data = similar_data[0]
        #     updated_web_list = [line['web'] for line in similar_data['web-urls']]
        #     updated_url_list = [line['url'] for line in similar_data['web-urls']]
        #     updated_evidence_list = [line['evidence'] for line in similar_data['web-urls']]

        # use local file to GET query_web data
        source_data = self.source_pool.get_source_data()
        query_list = [line['query'] for line in source_data]
        # calculate the similarity between query and all queries in query_list
        similar_query_list, score = self.retriever.retrieve(query, query_list)
        if float(score[0]) > 0.5:
            similar_query = similar_query_list[0]
            similar_source = source_data[query_list.index(similar_query)]["web-urls"]
            similar_web_list = [line['web'] for line in similar_source]
            similar_url_list = [line['url'] for line in similar_source]
            for web, url in zip(similar_web_list, similar_url_list):
                if web not in source_list and web not in negative_source_list:
                    _, res = self.online_search(query + " site:" + url)
                    if len(res["hrefs"]) == 0:
                        continue
                    for href, evidence in zip(res["hrefs"], res["evidences"]):
                        updated_evidence["hrefs"].append(href)
                        updated_evidence["evidences"].append(evidence)
                    updated_web_list.append(web)
                    updated_url_list.append(url)

        # generate optimized recommendation list
        if len(updated_web_list) > 0:
            # {query: query, source_list: source, updated_source_list: updated_source_list}
            self.logger.info({'query': query, 'updated_source_list': updated_web_list})
            return updated_web_list, updated_url_list, updated_evidence   
        else:
            print("no new sources found, continue")
            self.logger.info({'query': query, 'updated_source_list': []})
            return [], [], {"hrefs": [], "evidences": []}
    
    # English version: optimize method
    def optimize(self, query, negative_source_list, source_list, optimizer="self_critical"):
        if optimizer == "self_critical":
            return self.self_critical(query, negative_source_list, source_list)
        elif optimizer == "online":
            return self.online_search(query)  
        elif optimizer == "history":
            return self.offline_search(query, negative_source_list, source_list)






