import os
# os.environ['CUDA_VISIBLE_DEVICES'] = '1'
import re
from urllib import parse
from utils import url_to_domain
from model import KW2G_Model


class ResourceGenerator:
    def __init__(self, config):
        self.config = config
        self.model = KW2G_Model(self.config.base_model, self.config.device, self.config.prompt_template, self.config)
        self.model.load_adapter(self.config.source_lora_weights, adapter_name="source")
        # self.model.eval()
        self.num_dict = {2: "two", 3: "three", 4: "four", 5: "five"}
    
    def set_adapter(self):
        self.model.switch_adapter("source")
    
    def transform_output(self, output, title):
        output = output.replace(title, "")
        output_list = []
        # macth 1. 2. 3. 4. 5.
        pattern = re.compile(r'\d+\.\s')
        output = pattern.sub(title, output)
        output_list = output.split(title)[1:]
        output_list = [i.strip() for i in output_list]
        return output_list
    
    # step 1: intent recognition
    def intent_recognition(self, query, choice_list, intent_num=5):
        if intent_num == 1:
            instruction = self.config.intent_instruction.replace("five intents", "one intent")
        else:
            instruction = self.config.intent_instruction.replace("five", self.num_dict[intent_num])
        if len(choice_list) == 0:
            intent = self.model.generate("generator", instruction, "[Query] {}".format(query))
        else:
            # used for question answering that has choices
            intent = self.model.generate("generator", instruction, "[Query] {}\n[Choices] {}".format(query, choice_list))
        intent_list = self.transform_output(intent, "[Intent]")
        intent_show = [(i, str(no + 1)) for no, i in enumerate(intent_list)]
        return intent_list, intent_show
    
    # step 2: query expansion
    def query_expansion(self, query, intent_list, choice_list):
        expanded_query_list = []
        expanded_query_show = []
        for no, intent in enumerate(intent_list):
            if len(choice_list) == 0:
                eq = self.model.generate("generator", self.config.expand_instruction, "[Query] {}\n[Intent] {}".format(query, intent))
            else:
                # used for question answering that has choices
                eq = self.model.generate("generator", self.config.expand_instruction, "[Query] {}\n[Choices] {}\n[Intent] {}".format(query, choice_list, intent))
            expanded_query_list.append(eq)
            expanded_query_show.append((eq.replace("[Expanded query]", "").strip(), str(no + 1)))
        expanded_query_list = list(set(expanded_query_list))
        return expanded_query_list, expanded_query_show
    
    # step 3: source retrieval
    def source_retrieval(self, query, choice_list, expanded_query_list, web_num=5):
        if web_num == 1:
            instruction = self.config.retrieval_instruction.replace("five web sources", "one web source")
        else:
            instruction = self.config.retrieval_instruction.replace("five", self.num_dict[web_num])
        source_list = []

        # using original query to get source
        if self.config.use_org_query:
            if len(choice_list) == 0:
                source_list.append((query, self.model.generate("generator", instruction, "[Query] {}".format(query))))
            else:
                source_list.append((query, self.model.generate("generator", instruction, "[Query] {}\n[Choices] {}".format(query, choice_list))))
        
        # using expanded query to get source
        for expanded_query in expanded_query_list:
            if '[Expanded query]' in expanded_query:
                source_query = expanded_query.replace("[Expanded query]", '[Query]')
            else:
                # in case the expanded query does not generate correctly
                source_query = '[Query] ' + expanded_query
            source_list.append((source_query, self.model.generate("generator", instruction, source_query)))
        
        query_web = {}
        for web in source_list:
            wlist = self.transform_output(web[1], "[Website]")
            query_web[web[0]] = wlist
        web_show = list(set([i for w in query_web.values() for i in w]))
        return query_web, web_show
    
    # step 4: url recognition
    def url_recognition(self, web_show):
        url_list, url_show, web_url = [], [], {}
        # self check and get url
        for no, web in enumerate(web_show):
            url = self.model.generate("generator", self.config.url_instruction, "[Website] " + web)
            url_list.append(url.replace("[URL]", "").strip())
            if url not in url_show:
                if url != "This page does not exist":
                    url_show.append(url.replace("[URL]", "").strip())
                    web_url[web] = url.replace("[URL]", "").strip()
        return url_list, web_url
    
    # query web url map
    def get_query_web_url_map(self, query_web, web_url):    
        query_web_url_map = {}
        for q, web_list in query_web.items():
            q = q.replace("[Query]", "").strip()
            query_web_url_map[q] = {}
            for web in web_list:
                if web in web_url.keys():
                    query_web_url_map[q][web] = web_url[web]
        return query_web_url_map
    
    # web name recognition
    def web_name_recognition(self, url):
        web_name = self.model.generate("generator", self.config.web_instruction, "[URL] " + url)
        return web_name.replace("[Website]", "").strip()










    

    

