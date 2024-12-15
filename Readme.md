# Recurrent Knowledge Localization and Fusion for Language Model Continual Learning
Thank you for your interest in our work! This repository contains the original implementation of "Recurrent Knowledge Localization and Fusion for Language Model Continual Learning".

Reproducing the results from our paper is straightforward—just follow the steps outlined below.

## Local Setup
```
conda create -n KLF python=3.7
conda activate KLF
pip install -r requirements.txt
```

## Step 1. Preliminary Preparation
The data preprocessing pipeline follows the approach described in [O-LoRA](https://github.com/cmnfriend/O-LoRA). The implementation can be found in the `/data` folder. If you're interested in the preprocessing details, please refer to `data/preprocess.py`. For convenience, we also provide pre-processed datasets ready for use.


Download the required backbone models from Hugging Face:
* [T5-large](https://huggingface.co/google-t5/t5-large)
* [Flan-T5-xl](https://huggingface.co/google/flan-t5-xl)
* [LLaMA2-7B](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf)
* [LLaMA2-13B](https://huggingface.co/meta-llama/Llama-2-13b-chat-hf)

Replace the corresponding files in the Transformers package (usually located at `anaconda_path/envs/KLF/lib/python3.7/site-packages/transformers/`) with the latest versions of `trainer.py` and `training_args.py`. We’ve modified these files to implement our Recurrent Knowledge Localization and Fusion method.

If you're interested in the modifications, detailed comments have been added to the code for clarity.



## Step 2. Training Recurrent-KlF
### T5 Series Models (`./src/finetune_KlF_t5lora.py`)
To fine-tune T5 models, run:
```ruby
./scripts/run_train_KlF_t5lora.sh
```
### LLaMA-2-7B and 13B (`./src/finetune_KlF_llama.py`)
To fine-tune LLaMA-2-7B or LLaMA-2-13B models, run:
```ruby
./scripts_llama/run_train_KlF_llama.sh
```
Note:
* Use the `model_path` argument to specify the location of your downloaded models.
* We use [LoRA](https://github.com/microsoft/LoRA) to accelerate the fine-tuning process.
* Fine-tuned weights will be saved to `$checkpoint_files` at the end of training. 

## Step 3. Inference
We evaluate our model using two metrics: Overall Performance (OP) and Backward Transfer (BWT).

### **Overall Performance**
```ruby
./scripts/run_test_KlF_t5lora_avgPer.sh
```
### Backward Transfer (**BWT**)
```ruby
./scripts/run_test_KlF_t5lora_avgPer.sh
```
The prediction results will be stored in the `$output` folder.



## Step 4. Evaluation
To calculate the metrics, execute:
```ruby
./src/eval_avgJGA.py
./src/eval_bwt.py
```

We hope you find this repository useful! If you encounter any issues or have questions, feel free to open an issue or contact us.