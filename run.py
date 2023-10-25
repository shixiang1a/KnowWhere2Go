import os
os.environ['CUDA_VISIBLE_DEVICES'] = '1'
import fire
import gradio as gr
import torch
import json
from module.source_generator import SourceGenerator
from module.source_validator import SourceValidator
from module.source_optimizer import SourceOptimizer
from module.source_pool import SourcePool
from args import get_args
from nltk.tokenize import word_tokenize


def main(
    server_name: str = "0.0.0.0",
    share_gradio: bool = False,
):
    
    config = get_args()
    config.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # source generator init
    source_generator = SourceGenerator(config)
    # source pool init (use mongodb or json file)
    # source_pool = SourcePool(db_collection='KW2G')   
    source_pool = SourcePool(source_file_path=config.source_file_path) 
    # source validator init
    source_validator = SourceValidator(config, source_generator.model)
    # source optimizer init
    source_optimizer = SourceOptimizer(config, source_generator.model, source_pool, None, source_validator)
    
    def web_finder(
        query,
        choice_list=None,
        validator="online",
        filter="webfilter",
        optimizer="online",
        score_only=True,
        generate_answer=False,
        intent_num=5,
        web_num=5,
        **kwargs,
    ):
        
        config.validator = validator
        config.filter = filter
        config.intent_num = intent_num
        config.web_num = web_num
        config.generate_answer = generate_answer
        config.optimizer = optimizer
        config.score_only = score_only
        
        source_dataframe_show, url_check, access_url, accessed_web, negative_source_list= [], [], [], [], []
        # source retrieval (intent recognition, query expansion, source retrieval, url recognition)
        source_generator.set_adapter()
        intent_list, intent_show = source_generator.intent_recognition(query, choice_list, intent_num)
        expanded_query_list, expanded_query_show = source_generator.query_expansion(query, intent_list, choice_list)
        query_web, web_show = source_generator.source_retrieval(query, choice_list, expanded_query_list, web_num)
        _, web_url = source_generator.url_recognition(web_show)
        query_web_url_map = source_generator.get_query_web_url_map(query_web, web_url)

        url_evidence_show = ""
        evidence_score_dict = {}
        if config.validator == "forbid":
            for expanded_query in query_web_url_map.keys():
                for web, url in query_web_url_map[expanded_query].items():
                    if [web, "<" + url + ">", "🟨Wait for check"] not in source_dataframe_show and len(url) != 0:
                        source_dataframe_show.append([web, "<" + url + ">", "🟨Wait for check"])
        else:
            # source validation
            url_evidence_show = "<style>.clamp-lines {overflow: hidden;display: -webkit-box;-webkit-box-orient: vertical;-webkit-line-clamp: 2; /* 这里设置要显示的行数 */}</style><div style='max-width:100%; max-height:360px; overflow:auto'>"
            for expanded_query in query_web_url_map.keys():
                if len(query_web_url_map[expanded_query]) == 0:
                    continue

                evidence_count = 0
                for web, url in query_web_url_map[expanded_query].items():
                    search_query = expanded_query + " site:" + url
                    res = source_validator.validate(query, search_query, config.validator)
                    res = json.loads(res)
                    hrefs = res["hrefs"]
                    evidences = res["evidences"]

                    if len(hrefs) > 0:
                        for href, evidence in zip(hrefs, evidences):
                            url = href.replace("https://", "").replace("http://", "")
                            if "/" in url:
                                url = url.split("/")[0]
                            if "http://" in href:
                                url = "http://" + url + "/"
                            else:
                                url = "https://" + url + "/"
                            if web not in accessed_web:
                                accessed_web.append(web)
                                source_dataframe_show.append([web, "<" + url + ">", "✅Checked"])
                            else:
                                for rd_no, rd in enumerate(source_dataframe_show):
                                    if web == rd[0] and rd[2] == "🟨Wait for check":
                                        source_dataframe_show[rd_no][2] = "✅Checked"
                            for sub_evidence in evidence:
                                evidence_sentence = sub_evidence.split(" reliability_score: ")[0]
                                evidence_score = sub_evidence.split(" reliability_score: ")[1]
                                evidence_score_dict[evidence_sentence] = evidence_score
                                url_evidence_show += "<div><a href=\"" + href + "\" target='_blank'>" + href + "</a>" + "<p class='clamp-lines'>" + "[" + str(evidence_count + 1) + "] " + evidence_sentence + "</p></div>"
                                evidence_count += 1         
                            url_check.append(url)
                            access_url.append(href)
                    else:
                        if web not in accessed_web:
                            accessed_web.append(web)
                            negative_source_list.append(web)
                            source_dataframe_show.append([web, "<" + url + ">", "🟨Wait for check"])                
            source_validator.clear()
            
        # source optimization
        updated_source_dataframe_show = []
        source_list = [r[0] for r in source_dataframe_show]
        url_evidence_show_update = ""
        if len(negative_source_list) > 0 and config.optimizer !="forbid":
            url_evidence_show_update = "<style>.clamp-lines {overflow: hidden;display: -webkit-box;-webkit-box-orient: vertical;-webkit-line-clamp: 2; /* 这里设置要显示的行数 */}</style><div style='max-width:100%; max-height:360px; overflow:auto'>"
            if config.optimizer == "online":
                updated_url, res = source_optimizer.optimize(query, negative_source_list, source_list, config.optimizer)
                evidence_count = 0
                if len(res["evidences"]) > 0:
                    for url, evidence, href in zip(updated_url, res["evidences"], res["hrefs"]):
                        web = source_generator.web_name_recognition(url)
                        if [web, "<" + url + ">", "✅Checked"] not in updated_source_dataframe_show:
                            updated_source_dataframe_show.append([web, "<" + url + ">", "✅Checked"])
                        for sub_evidence in evidence:
                            evidence_sentence = sub_evidence.split(" reliability_score: ")[0]
                            evidence_score = sub_evidence.split(" reliability_score: ")[1]
                            evidence_score_dict[evidence_sentence] = evidence_score
                            url_evidence_show_update += "<div><a href=\"" + href + "\" target='_blank'>" + href + "</a>" + "<p class='clamp-lines'>" + "[" + str(evidence_count + 1) + "] " + evidence_sentence + "</p></div>"
                            evidence_count += 1

            elif config.optimizer == "history":
                updated_web, updated_url, evidences = source_optimizer.optimize(query, negative_source_list, source_list, config.optimizer)
                evidence_count = 0
                for web, url, evidence_score in zip(updated_web, updated_url, evidences):
                    if [web, "<" + url + ">", "✅Checked"] not in updated_source_dataframe_show:
                        updated_source_dataframe_show.append([web, "<" + url + ">", "✅Checked"])
                    for score in evidence_score:
                        evidence_score_dict[score[0]] = score[1]
                        url_evidence_show_update += "<div><a href=\"" + score[2] + "\" target='_blank'>" + score[2] + "</a>" + "<p class='clamp-lines'>" + "[" + str(evidence_count + 1) + "] " + score[0] + "</p></div>"
                        evidence_count += 1
            
            elif config.optimizer == "self_critical":
                updated_web, updated_url, res = source_optimizer.optimize(query, negative_source_list, source_list, config.optimizer)
                evidence_count = 0
                for web, url, evidence, href in zip(updated_web, updated_url, res["evidences"], res["hrefs"]):
                    if [web, "<" + url + ">", "✅Checked"] not in updated_source_dataframe_show:
                        updated_source_dataframe_show.append([web, "<" + url + ">", "✅Checked"])
                    for sub_evidence in evidence:
                        evidence_sentence = sub_evidence.split(" reliability_score: ")[0]
                        evidence_score = sub_evidence.split(" reliability_score: ")[1]
                        evidence_score_dict[evidence_sentence] = evidence_score
                        url_evidence_show_update += "<div><a href=\"" + href + "\" target='_blank'>" + href + "</a>" + "<p class='clamp-lines'>"+ "[" + str(evidence_count + 1) + "] " + evidence_sentence + "</p></div>"
                        evidence_count += 1
            else:
                pass
        
        print("evidence_score_dict: ", evidence_score_dict)
        
        # answer generation
        answer_show = ""
        if config.generate_answer and len(evidence_score_dict) > 0:
            sorted_evidence_score_dict = sorted(evidence_score_dict.items(), key=lambda x:x[1], reverse=True)
            used_for_answer_generate = []
            length_for_answer_generate = 0
            for evidence, score in sorted_evidence_score_dict:
                if length_for_answer_generate + len(word_tokenize(evidence)) < 500:
                    used_for_answer_generate.append(evidence)
                    length_for_answer_generate += len(word_tokenize(evidence))
                else:
                    break
            answer_show = source_validator.generate_answer(query, used_for_answer_generate)
        elif config.generate_answer:
            answer_show = "There is not enough evidence at the moment to construct an answer. You may browse through the recommended sources to obtain an answer."
        else: 
            pass
        
        yield intent_show, expanded_query_show, source_dataframe_show, url_evidence_show + "</div>", updated_source_dataframe_show, url_evidence_show_update + "</div>", answer_show


    gr.Interface(
        fn=web_finder,
        inputs=[
            gr.components.Textbox(
                lines=2,
                label="Query",
                placeholder="Tell me about alpacas.",
            ),
            gr.components.Textbox(
                lines=1,
                label="Choices",
                placeholder="['choice 1', 'choice 2', 'choice 3']"
            ),
            gr.Radio(["online", "forbid"], label="Validator", info="Whether to use validator", value="online"),
            gr.Radio(["webfilter"], label="Filter", info="Which filter to use", value="webfilter"),
            gr.Radio(["self_critical", "online", "history", "forbid"], label="Optimizer", info="Whether to use optimizer", value="forbid"),
            gr.Checkbox(label="Score Only", info="Whether to use score only evidence validator", value=True),
            gr.Checkbox(label="Generate Answer", info="Whether to generate answer", value=False),
            gr.components.Slider(
                minimum=1, maximum=5, step=1, value=2, label="Intent number"
            ),
            gr.components.Slider(
                minimum=1, maximum=5, step=1, value=1, label="Web number"
            ),
        ],
        examples=[
            ["What is the capital of France?"]
        ],
        outputs=[
            gr.components.HighlightedText(
                label="User Intent",
            ),
            gr.components.HighlightedText(
                label="Expanded Query",
            ),
            gr.components.Dataframe(
            headers=["Website", "URL", "Check"],
            datatype=["str", "markdown", "str"],
            label="The corresponding sources are:",
            max_rows=5,
            ),
            gr.HTML(
                label="Evidence",
            ),
            gr.components.Dataframe(
            headers=["Website", "URL", "Check"],
            datatype=["str", "markdown", "str"],
            label="Updated sources are:",
            max_rows=5,
            ),
            gr.HTML(
                label="Evidence Updated",
            ),
            gr.components.Textbox(
                lines=1,
                label="Answer generated based on evidence",
            ),
        ],
        title="KW2G",
        description="KW2G is a generation-based source retrieval system that has been developed based on the LLaMA model, fine-tuned to adhere to instructions. ✅ It represents verified sources, 🟨 while indicating sources that are inaccessible or invalid.",  # noqa: E501
    ).queue().launch(server_name=server_name, share=share_gradio)



if __name__ == "__main__":
    fire.Fire(main)
