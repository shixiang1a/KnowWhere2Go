from prompter import Prompter
from peft import PeftModel
from transformers import GenerationConfig, LlamaForCausalLM, LlamaTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch


class KW2G_Model:
    def __init__(self, base_model_name, device, prompt_template, config):
        self.device = device
        self.tokenizer = LlamaTokenizer.from_pretrained(base_model_name)
        self.max_memory = f'80000MB'
        if "65b" in base_model_name:
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                load_in_4bit=True,
                device_map='auto',
                max_memory={i: self.max_memory for i in range(1)},
                torch_dtype=torch.bfloat16,
                quantization_config=BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type='nf4'
                ),
            )
        else:
            self.model = LlamaForCausalLM.from_pretrained(base_model_name, torch_dtype=torch.float16, device_map="auto")
        self.config = config
        self.generation_config = GenerationConfig(
            top_k=self.config.top_k,
            top_p=self.config.top_p,
            num_beams=self.config.num_beams,
        )
        self.prompter = Prompter(prompt_template)
        self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model.eval()
    
    def load_adapter(self, adapter_path, adapter_name):
        self.model = PeftModel.from_pretrained(self.model, adapter_path, adapter_name=adapter_name)
        self.model.eval()
    
    def load_multiple_adapters(self, adapter_paths, adapter_names):
        for i in range(0, len(adapter_paths)):
            self.model.load_adapter(adapter_paths[i], adapter_name=adapter_names[i])
        self.model.eval()
    
    def switch_adapter(self, adapter_name):
        self.model.set_adapter(adapter_name)
    
    def generate(self, module, task, input):
        prompt = self.prompter.generate_search_prompt(module, task, input)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = torch.ones(input_ids.shape)

        with torch.no_grad():
            generation_output = self.model.generate(
                input_ids=input_ids,
                generation_config=self.generation_config,
                return_dict_in_generate=True,
                output_scores=True,
                max_new_tokens=self.config.max_new_tokens,
                eos_token_id=self.tokenizer.eos_token_id,
                attention_mask=attention_mask,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=self.config.repeat_penalty,
            )
        s = generation_output.sequences[0]
        output = self.tokenizer.decode(s)
        return self.prompter.get_response(output)
    
    def generate_with_score(self, module, task, input):
        prompt = self.prompter.generate_search_prompt(module, task, input)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = torch.ones(input_ids.shape)

        with torch.no_grad():
            generation_output = self.model.generate(
                input_ids=input_ids,
                generation_config=self.generation_config,
                return_dict_in_generate=True,
                output_scores=True,
                max_new_tokens=self.config.max_new_tokens,
                eos_token_id=self.tokenizer.eos_token_id,
                attention_mask=attention_mask,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=self.config.repeat_penalty,
            )

        gen_sequences = generation_output.sequences[:, input_ids.shape[-1]:]
        probs = torch.stack(generation_output.scores, dim=1).softmax(-1)
        gen_probs = torch.gather(probs, 2, gen_sequences[:, :, None]).squeeze(-1)

        s = generation_output.sequences[0]
        output = self.tokenizer.decode(s)
        output = self.prompter.get_response(output)

        if "[Evidence Recognition]" in task:
            if "No Evidence" not in output:
                score = 1 + gen_probs[0][5].item()
            else:
                score = 1 - gen_probs[0][5].item()
        elif "[Evidence Check]" in task:
            if "[Result] Yes" in output:
                score = 1 + gen_probs[0][3].item()
            elif "[Result] No" in output:
                score = 1 - gen_probs[0][3].item()
            else:
                score = 1

        return output, score