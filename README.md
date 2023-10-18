[![Gradio](https://img.shields.io/badge/Gradio-Online%20Demo-blue)]()

# KnowWhere2Go

<font size=7><div align='center'>Make LLM a Relevant, Responsible, and Trustworthy Searcher</div></font>

<font size=7><div align='center' > <a href="">**Paper**</a> | [**Training**](#training) | [**Local Deployment**](#deployment) | [**Dataset**](#dataset) | <a href="">**Online Demo**</a></div></font>

<p align="center"> <img src="https://github.com/shixiang1a/KnowWhere2Go/blob/main/framework.png" width="100%"> </p>

## Installation
```
pip install -r requirements.txt
```

## Training
```
python trainer.py \
  --base_model="yahma/llama-7b-hf" \
  --data_path="PATH_TO_DATA" \
  --output_dir="PATH_TO_MODEL" 
```

## Dataset
### Training Data
The training data consists of 54.2k instructions categorized into intent recognition (3.8k), query expansion (4.8k), source generation (11k), URL identification (3.4k), Web name identification (3.8k), evidence recognition (4.5k), evidence check (5.4k), source correction (2.5k), and answer generation (15k). The training data can be found in the `dataset/KW2G_train.json` file.
### Evaluation Data
The evaluation data consists of a total of five categories, each used to assess the abilities of intent recognition `test_data/intent_test.json`, query expansion `test_data/query_expansion_test.json`, URL identification `test_data/url_test.json`, web name identification `test_data/web_test.json`, and evidence recognition `test_data/evidence_test.json`.
### Pre-filled data
The optimization method using the `history_mining` strategy requires pre-filling the source_pool. The `dataset/seed_query.txt` file contains the queries used for filling, while `dataset/source_data.json` contains the source data. We provide some sample data in the files.
Running `source_validator.py` will pre-fill the source pool.
```
python source_validator.py 
```

## Model Weights
You can now download the 7B and 13B model lora weights from [Google Drive](https://drive.google.com/file/d/1xOgYGyhQcSKMSWVCTxXw2LFKYhwIGAnv/view?usp=share_link). The weights are placed respectively in `model/KW2G_model/7b` and `model/KW2G_model/13b`.

## Local Deployment
```
python run.py \
  --base_model="yahma/llama-7b-hf" \
  --source_lora_weights="PATH_TO_LORA" \
```
Note: If an offline database (Elasticsearch) is being used, please set `use_elasticsearch=True` before starting the system.
