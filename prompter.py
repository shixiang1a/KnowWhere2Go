"""
A dedicated helper to manage templates and prompt building.
"""

import json
import os.path as osp
from typing import Union


class Prompter(object):
    __slots__ = ("template", "_verbose")

    def __init__(self, template_name: str = "", verbose: bool = False):
        self._verbose = verbose
        if not template_name:
            # Enforce the default here, so the constructor can be called with '' and will not break.
            template_name = "KW2G_template"
        file_name = osp.join("/home/llmtrainer/KW2G/dataset", f"{template_name}.json")
        if not osp.exists(file_name):
            raise ValueError(f"Can't read {file_name}")
        with open(file_name) as fp:
            self.template = json.load(fp)
        if self._verbose:
            print(
                f"Using prompt template {template_name}: {self.template['description']}"
            )
    
    def generate_search_prompt(
        self,
        module: str,
        task: str, # instruction
        input: Union[None, str] = None,
        output: Union[None, str] = None,
    ) -> str:
        res = self.template["system_description"] + self.template["prompt"].format(
                module=module, task=task, input=input
        )

        if output:
            res = f"{res}{output}"
        if self._verbose:
            print(res)
        return res
          

    def get_response(self, output: str) -> str:
        output = output.split(self.template["response_split"])[1].strip()
        output = output.replace("</s>", "")
        return output