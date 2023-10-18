import sys
sys.path.append("./")
from flask import Flask, request
from utils.search import Operator
import json
from tqdm import tqdm
from utils.utils import cut_page
from args import get_args
from retriever.retriever import Retriever
from nltk.tokenize import sent_tokenize
from module.source_generator import SourceGenerator
from module.source_pool import SourcePool
# from retriever.contriver import ReferenceFilter
import torch

app = Flask(__name__)

class link:
    def __init__(self):
        self.accessed_links = []
    
    def add(self, link):
        self.accessed_links.append(link)
    
    def check(self, link):
        return link in self.accessed_links
    
    def clear(self):
        self.accessed_links = []

class SourceValidator:
    def __init__(self, config, model):
        self.config = config
        self.model = model
        # you can use any score and evidence model here
        # self.model.load_multiple_adapters(["./model/extract_sent/"], ["evidence"])
        # self.model.load_multiple_adapters([config.score_lora_weights], ["scorer"])
        # self.evidence_model = ReferenceFilter(self.config.retriever_ckpt_path)

        # offline retriever based on ElasticSearch
        if self.config.use_elasticsearch:
            self.retriever = Retriever('web_search')
        # online retriever based on Bing
        self.op = Operator()
        # record accessed links
        self.accessed_links = link()
    
    def evidence_finder(self, query, split_sentences):
        # recognize the content that can respond to the query in the window
        evidence = []
        # search the evidence in the window
        if self.config.filter == 'webfilter':     
            if len(split_sentences) > 0:

                sub_evidence = []
                for idx in range(len(split_sentences)):

                    if not self.config.score_only:
                        # hybrid evidence finder
                        candidate_evidence_hybrid = self.model.generate("validator", self.config.evidence_instruction, "[Query] " + query + "\n[Document] " + split_sentences[idx])
                        candidate_evidence_hybrid, evidence_score = self.model.generate_with_score("validator", self.config.evidence_instruction, "[Query] " + query + "\n[Document] " + split_sentences[idx])
                        candidate_evidence_hybrid = candidate_evidence_hybrid.replace("[Evidence]", "").strip()
                        final_evidence = candidate_evidence_hybrid

                        if final_evidence != "No Evidence.":
                            _, check_score = self.model.generate_with_score("validator", self.config.check_instruction, "[Query] " + query + "\n[Evidence] " + final_evidence)
                            if check_score > self.config.score_threshold:
                                sub_evidence.append(final_evidence + " reliability_score: " + str(check_score))           
                    else:
                        # score only evidence finder
                        candidate_evidence_score_list = []
                        sentences = sent_tokenize(split_sentences[idx])
                        for sentence in sentences:
                            evidence_check, evidence_score = self.model.generate_with_score("validator", self.config.check_instruction, "[Query] " + query + "\n[Evidence] " + sentence)
                            if "Yes" in evidence_check:
                                candidate_evidence_score_list.append(sentence + " reliability_score: " + str(evidence_score))

                        # 
                        if len(candidate_evidence_score_list) != 0:
                            for e in candidate_evidence_score_list:
                                if float(e.split(" reliability_score: ")[1]) > self.config.score_threshold:
                                    sub_evidence.append(e)
                        else:
                            final_evidence = "No Evidence."
                    
                # record the evidence
                if len(sub_evidence) != 0:
                    evidence += sub_evidence
                
        elif self.config.filter == 'contriver':
            sub_evidence = self.evidence_model.evidence(query, split_sentences, topk=1)
            evidence.append(sub_evidence[0])
            print("sub_evidence: " + sub_evidence[0] + "\n")
        else:
            raise NotImplementedError
        return evidence
        
    
    def online_validate(self, query, search_query):
        evidences, hrefs  = [], []
        searched_results = self.op.search(search_query)
        if searched_results is None or len(searched_results) == 0:
            # print("no results found in Bing for query: " + search_query)
            return json.dumps({"hrefs": [], "evidences": []})
        max_page_per_query = min(self.config.max_page_per_query, self.op.get_page_num())
        for page_idx in range(max_page_per_query):
            if self.accessed_links.check(searched_results[page_idx]["url"]):
                continue
            else:
                self.accessed_links.add(searched_results[page_idx]["url"])

            print("page:" + searched_results[page_idx]["name"] + "\n")
                
            href, page_detail = self.op.load_page(page_idx)
            if page_detail is None:
                print("your connection fails, no page rendered")
                continue
            if len(page_detail) == 0:
                print("page no content, continue \n")
                continue
            print("content:" + page_detail)
            print(href)
            print("\n")
            split_sentences = cut_page(searched_results[page_idx]["name"] + '. ' + page_detail, self.config.segment_method, self.config.segment_length)
            print("dividing into " + str(len(split_sentences)) + "sub pages")
            if len(split_sentences) > 100:
                continue
            evidence = self.evidence_finder(query, split_sentences)
            if len(evidence) > 0:
                hrefs.append(href)
                evidences.append(evidence)
        return json.dumps({"hrefs": hrefs, "evidences": evidences})
    

    def offline_validate(self, query, search_query):
        evidences, hrefs  = [], []
        searched_results = self.retriever.search(search_query, self.config.max_page_per_query)
        if len(searched_results) == 0:
            print("no results found in local dataset for query: " + search_query)
            return json.dumps({"hrefs": [], "evidences": [], "answers": []})
        max_page_per_query = self.config.max_page_per_query
        for page_idx in range(max_page_per_query):
            href = searched_results[page_idx]["_source"]["url"]
            print("page:" + href + "\n")
            page_detail = searched_results[page_idx]["_source"]["document"]
            if len(page_detail) == 0:
                print("page no content, continue \n")
                continue
            print("content:" + page_detail)
            print("\n")
            split_sentences = cut_page(page_detail, self.config.segment_method, self.config.segment_length)
            print("dividing into " + str(len(split_sentences)) + "sub pages")
            evidence = self.evidence_finder(query, split_sentences)
            if len(evidence) > 0:
                hrefs.append(href)
                evidences.append(evidence)
        return json.dumps({"hrefs": hrefs, "evidences": evidences})
        
    
    def validate(self, query, search_query, validate_mode='online'):
        if validate_mode == 'online':
            return self.online_validate(query, search_query)
        elif validate_mode == 'offline':
            return self.offline_validate(query, search_query)
        else:
            raise NotImplementedError
    

    def generate_answer(self, query, evidence):
        # self.model.switch_adapter("answer")
        ref = ""
        for i in range(len(evidence)):
            ref += "[" + str(i + 1) + "]" + evidence[i] + " "
        ref = ref.strip()
        answer = self.model.generate("validator", self.config.answer_instruction, "[Query] {}\n[References] {}".format(query.split("site:")[0].strip(), ref))
        if "[Answer]" not in answer:
            return "No Answer."
        return answer.split("[Answer]")[1].strip()
        
    
    # clear accessed links after each round of source validation
    def clear(self):
        self.accessed_links.clear()
   

# 初始化资源验证器（接口）
@app.route("/validate", methods=["POST"])
def search():

    # 获取请求参数
    query = request.form.get("search_query")
    org_query = request.form.get("original_query")
    validate_mode = request.form.get("validate_mode")
    query = eval(query)[0]
    org_query = eval(org_query)[0]

    config = get_args()
    
    # 设置检索器和筛选器
    source_validator = SourceValidator(config)
    
    # 搜索文档
    print("current query is: " + query + "\n")

    if validate_mode == "online" or validate_mode == "offline":
        return source_validator.validate(query.rstrip(), org_query.rstrip(), validate_mode)
    else:
        print("validate mode error")
        return json.dumps({"hrefs": [], "evidences": [], "answers": []})


def preload():
    config = get_args()
    config.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    config.use_org_query = False
    config.validator = "offline"
    config.filter = 'webfilter'

    source_generator = SourceGenerator(config)
    source_validator = SourceValidator(config, source_generator.model)
    source_pool = SourcePool(source_file_path=config.source_file_path)

    seed_file = open("./dataset/seed_query.txt", "r")
    seed_query = [query.strip() for query in seed_file.readlines()]
    seed_file.close()

    for query in tqdm(seed_query):
        res = source_validator.validate(query, query, config.validator)
        res = json.loads(res)
        hrefs = res["hrefs"]
        evidences = res["evidences"]
        data = {"query": query, "web-urls": []}
        if len(hrefs) > 0:
            for href, evidence in zip(hrefs, evidences):
                url = href.replace("https://", "").replace("http://", "").split("/")[0]
                if "https://" in href:
                    url = "https://" + url + "/"
                elif "http://" in href:
                    url = "http://" + url + "/"
                else:
                    continue
                web_name =  source_generator.web_name_recognition(url)
                evidence_score = []
                for sub_evidence in evidence:
                    evidence_score.append([sub_evidence.split(" reliability_score: ")[0], sub_evidence.split(" reliability_score: ")[1], href])
                data["web-urls"].append({"web": web_name, "url": url, "evidence": evidence_score})
        source_pool.write_query_web_file(data)

  
if __name__ == "__main__":
    # app.run(debug=False, use_reloader=False)
    
    # pre fulfill source pool
    preload()