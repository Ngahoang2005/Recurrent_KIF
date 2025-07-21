# Recurrent Knowledge Identification and Fusion for Language Model Continual Learning
Thank you for your interest in our work! This is the original implementation of our ACL 2025 paper, ["Recurrent Knowledge Identification and Fusion for Language Model Continual Learning"](https://arxiv.org/abs/2502.17510).

We also invite you to explore our previous work on continual learning, [TaSL](https://github.com/WoodScene/TaSL), which is the predecessor of Recurrent KIF and was published at ACL 2024.

Reproducing the results from our paper is straightforward—just follow the steps outlined below.

## Local Setup
```
conda create -n RKIF python=3.8
conda activate RKIF
pip install -r requirements.txt
```

> **Important:**
> Please ensure the following package versions:
>
> * `transformers==4.28.1`
> * `peft==0.4.0`

Then, replace the corresponding files in the `transformers` package (typically located at `anaconda_path/envs/RKIF/lib/python3.8/site-packages/transformers/`) with the modified versions of `trainer.py` and `training_args.py`.
These modifications are required to support our **Recurrent Knowledge Identification and Fusion** framework.

> Detailed comments are included in the modified files to help you understand the changes.


## Step 1. Preliminary Preparation
The data preprocessing pipeline follows the approach described in [O-LoRA](https://github.com/cmnfriend/O-LoRA). The implementation can be found in the `/data` folder. If you're interested in the preprocessing details, please refer to `data/preprocess.py`. For convenience, we also provide pre-processed datasets ready for use.

Download the required backbone models from Hugging Face:
* [T5-large](https://huggingface.co/google-t5/t5-large)
* [Flan-T5-xl](https://huggingface.co/google/flan-t5-xl)
* [LLaMA2-7B](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf)
* [LLaMA2-13B](https://huggingface.co/meta-llama/Llama-2-13b-chat-hf)


## Step 2. Training Recurrent-KIF
### T5 Series Models (`./src/finetune_KIF_t5lora.py`)
To fine-tune T5 models, run:
```ruby
./scripts/run_train_KIF_t5lora.sh
```
### LLaMA-2-7B and 13B (`./src/finetune_KIF_llama.py`)
To fine-tune LLaMA-2-7B or LLaMA-2-13B models, run:
```ruby
./scripts_llama/run_train_KIF_llama.sh
```
Note:
* Use the `model_path` argument to specify the location of your downloaded models.
* We use [LoRA](https://github.com/microsoft/LoRA) to accelerate the fine-tuning process.
* Fine-tuned weights will be saved to `$checkpoint_files` at the end of training. 

## Step 3. Inference
We evaluate our model using two metrics: Overall Performance (OP) and Backward Transfer (BWT).

### **Overall Performance**
```ruby
./scripts/run_test_KIF_t5lora_avgPer.sh
```
### Backward Transfer (**BWT**)
```ruby
./scripts/run_test_KIF_t5lora_avgPer.sh
```
The prediction results will be stored in the `$output` folder.



## Step 4. Evaluation
To calculate the metrics, execute:
```ruby
./src/eval_avgPerf.py
./src/eval_bwt.py
```

We hope you find this repository useful! If you encounter any issues or have questions, feel free to open an issue or contact us.


## Citation
If this work proves beneficial or use our code for your research, citing our paper would be greatly appreciated.
```ruby
@article{feng2025recurrent,
  title={Recurrent knowledge identification and fusion for language model continual learning},
  author={Feng, Yujie and Wang, Xujia and Lu, Zexin and Fu, Shenghong and Shi, Guangyuan and Xu, Yongxin and Wang, Yasha and Yu, Philip S and Chu, Xu and Wu, Xiao-Ming},
  journal={arXiv preprint arXiv:2502.17510},
  year={2025}
}
```
