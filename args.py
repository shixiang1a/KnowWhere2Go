import argparse
import os

def model_config(parser):
    """Model arguments"""
    parser.add_argument("--base_model", type=str, default="huggyllama/llama-65b", help="base model used for the generator, default to yahma/llama-7b-hf, huggyllama/llama-65b")
    parser.add_argument("--load_8bit", type=bool, default=False, help="whether to load the 8bit model, default to False")
    parser.add_argument("--source_lora_weights", type=str, default=os.path.abspath(os.path.join(os.getcwd(), ".")) + "/model/KW2G_model/65b", help="path to the source lora weights, default to $RESOURCE_LORA_WEIGHTS")
    parser.add_argument("--prompt_template", type=str, default="KW2G_template", help="prompt template for the generator, default to use the default prompt template")
    parser.add_argument("--temperature", type=int, default=0.1, help="temperature for the generator, default to 0")
    parser.add_argument("--top_p", type=float, default=0.75, help="top p for the generator, default to 0.75")
    parser.add_argument("--top_k", type=int, default=40, help="top k for the generator, default to 40")
    parser.add_argument("--num_beams", type=int, default=1, help="num beams for the generator, default to 1")
    parser.add_argument("--max_new_tokens", type=int, default=512, help="max new tokens for the generator, default to 512")
    parser.add_argument("--repeat_penalty", type=float, default=1, help="repeat penalty for the generator, default to 1.0")
    parser.add_argument("--use_org_query", type=bool, default=True, help="whether to use the original query, default to True")
    parser.add_argument("--online_check_after_self_critical", type=bool, default=True, help="whether to check the evidence after self critical, default to True")
    parser.add_argument("--score_only", type=bool, default=True, help="whether to use score only (validator), default to False")
    parser.add_argument("--score_threshold", type=float, default=1.7, help="score threshold for the generator, default to 1.7")

    # score model path (PEFT) (you can use any score model you want)
    # parser.add_argument("--score_lora_weights", type=str, default="model/score", help="path to the score checkpoint, default to $WEBGLM_SCORE_CKPT")

    # retriver model path (From WebGLM if you want to use the contriever)
    # parser.add_argument("--retriever_ckpt_path", type=str, default="", help="path to the retriever checkpoint, default to $WEBGLM_RETRIEVER_CKPT")
    
    # retriever and filter model path (User Defined)
    parser.add_argument("--validator", type=str, default="online", choices=['online', 'forbid'], help="validator to use (online, offline or forbid), default to online")
    parser.add_argument("--filter", type=str, default="webfilter", choices=['webfilter', 'contriver'], help="filter to use")
    parser.add_argument("--optimizer", type=str, default="online", choices=['self_critical', 'online', 'offline', 'forbid'], help="optimizer to use (self_critical, online or offline), default to online")
    parser.add_argument("--generate_answer", type=bool, default=False, help="whether to generate answer, default to False")
    
    # instructions
    parser.add_argument("--intent_instruction", type=str, default="[Intent Recognition] Recognizing five intents based on user's query.", help="instructions for the intent model")
    parser.add_argument("--expand_instruction", type=str, default="[Query Expansion] Expanding the original query according to the user's intent.", help="instructions for the expansion model")
    parser.add_argument("--retrieval_instruction", type=str, default="[Resource Retrieval] Retrieving five web resources that fulfill the user's requirement.", help="instructions for the retrieval model")
    parser.add_argument("--url_instruction", type=str, default="[URL Identification] Providing the homepage URL of the website. If the website does not exist, respond with 'This page does not exist.'", help="instructions for the url model")
    parser.add_argument("--web_instruction", type=str, default="[Website Identification] Providing the website name of the homepage URL.", help="instructions for the web model")
    parser.add_argument("--evidence_instruction", type=str, default="[Evidence Recognition] Identify evidence sentences from the document that can answer the query; if none exist, respond with 'No evidence.'", help="instructions for the evidence model")
    parser.add_argument("--check_instruction", type=str, default="[Evidence Check] Determine whether the evidence sentence can answer the query.", help="instrcution for the check model")
    parser.add_argument("--answer_instruction", type=str, default="[Answer Generation] Generating answer that can answer the query based on references.", help="instructions for the answer model")
    parser.add_argument("--critical_instruction", type=str, default="[Resource Correction] Modifying retrieved resources based on user queries and suggestions.", help="instructions for the critical model")
    
    # device
    parser.add_argument("--device", type=str, default="cuda:0", help="device to run the model, default to cuda")
    
    return parser


def data_config(parser):
    """Data arguments"""
    # parser.add_argument("--offline_data_path", type=str, default="/data_share/data/RedPajama-Data-1T/c4/c4-train.00000-of-01024.jsonl", help="path to the offline data, default to $OFFLINE_DATA_PATH")

    parser.add_argument("--source_file_path", type=str, default=os.path.abspath(os.path.join(os.getcwd(), ".")) + "/dataset/source_data.json", help="path to the source data, default to $SOURCE_DATA_PATH")
    # segement method
    parser.add_argument("--segment_method", type=str, default="sentence", choices=['sentence', 'length'], help="segment method to use (sentence or length), default to sentence")
    parser.add_argument("--segment_length", type=int, default=512, help="segment length for the segment method, default to 512")
    
    # evidence top_k
    parser.add_argument("--evidence_topk", type=int, default=1, help="top k evidence to use, default to 1")
    # log path
    parser.add_argument("--log_dir", type=str, default=os.path.abspath(os.path.join(os.getcwd(), ".")) + "/log/", help="path to the log directory, default to $LOG_DIR")
    
    # result path
    parser.add_argument("--result_dir", type=str, default=os.path.abspath(os.path.join(os.getcwd(), ".")) + "/result/", help="path to the result directory, default to $RESULT_DIR")
    return parser

def search_config(parser):
    """Search arguments"""
    
    parser.add_argument("--searcher", type=str, default="bing", help="searcher to use (local or bing), default to bing")
    parser.add_argument("--max_page_per_query", type=int, default=5, help="max page per query, default to 3")
    parser.add_argument("--use_elasticsearch", type=bool, default=False, help="whether to use elasticsearch")
    return parser

 
def get_args():
    """Get arguments"""
    parser = argparse.ArgumentParser(description="KW2G")
    parser = model_config(parser)
    parser = data_config(parser)
    parser = search_config(parser)
    return parser.parse_args()