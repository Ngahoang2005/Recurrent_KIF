import os

import sys
from typing import List
from peft import PeftModel
import fire
import torch
import transformers
import shutil
from datasets import load_dataset
from transformers import AutoConfig
import gc


"""
Unused imports:
import torch.nn as nn
import bitsandbytes as bnb
"""
import time
from utils.lora_importance_bilevel import RankAllocator
from peft import (
    LoraConfig,
    get_peft_model,
    get_peft_model_state_dict,
    prepare_model_for_int8_training,
    set_peft_model_state_dict,
)
from transformers import LlamaForCausalLM, LlamaTokenizer

from utils.prompter import Prompter
from transformers import set_seed
from utils.dataset_order import get_dataset_order
from utils.load_data import load_current_task_data, load_memory_buffer, load_validation_set

set_seed(42)


def train(
    # 可以调节的超参数
    method_name: str = "",  # the only required argument
    inner_iterations: int = 8, #new
    outer_iterations: int = 4, #new
    train_batch_size_outer: int = 8,#new 16
    empty_inner_score_flag: int = 1, #是否清空累积的重要性梯度，0表示不清空 new 0 1
    empty_outer_score_flag: int = 0, #new 0 1
    quantile: float = 0.8,
    outer_lr: float = 1e-3, #new
    # model/data params
    base_model: str = "",  # the only required argument
    data_dir: str = "./data_longsequence_llama",
    output_path: str = "./checkpoint_files",
    cache_dir: str = "/cache",

    # training hyperparams
    batch_size: int = 128,
    micro_batch_size: int = 4,
    num_epochs: int = 10,
    learning_rate: float = 3e-4,
    cutoff_len: int = 512,
    val_set_size: int = 20,
    # lora hyperparams
    lora_r: int = 8,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    lora_target_modules: List[str] = [
        "q_proj",
        "v_proj",
    ],
    # llm hyperparams
    train_on_inputs: bool = False,  # if False, masks out inputs in loss
    add_eos_token: bool = True,
    group_by_length: bool = False,  # faster, but produces an odd training loss curve
    # wandb params
    wandb_project: str = "",
    wandb_run_name: str = "",
    wandb_watch: str = "",  # options: false | gradients | all
    wandb_log_model: str = "",  # options: false | true
    resume_from_checkpoint: str = None,  # either training checkpoint or final adapter
    prompt_template_name: str = "alpaca",  # The prompt template to use, will default to alpaca.
    dataset_id: int = 1, # 1 - 5  5次实验
    task_id: int = 0, # 这个表示从哪个service开始训练，默认从头开始训练
    beta1: float = 0.85, 
    beta2: float = 0.85,
    memory_data_ratio: int = 2, # 这个表示训练数据的比例；
):
    if int(os.environ.get("LOCAL_RANK", 0)) == 0:
        print(
            f"Training Alpaca-LoRA model with params:\n"
            f"base_model: {base_model}\n"
            f"method_name: {method_name}\n"
            f"batch_size: {batch_size}\n"
            f"train_batch_size_outer: {train_batch_size_outer}\n"
            f"micro_batch_size: {micro_batch_size}\n"
            f"inner_iterations: {inner_iterations}\n"
            f"outer_iterations: {outer_iterations}\n"
            f"num_epochs: {num_epochs}\n"
            f"learning_rate: {learning_rate}\n"
            f"cutoff_len: {cutoff_len}\n"
            f"val_set_size: {val_set_size}\n"
            f"lora_r: {lora_r}\n"
            f"lora_alpha: {lora_alpha}\n"
            f"lora_dropout: {lora_dropout}\n"
            f"lora_target_modules: {lora_target_modules}\n"
            f"train_on_inputs: {train_on_inputs}\n"
            f"add_eos_token: {add_eos_token}\n"
            f"group_by_length: {group_by_length}\n"
            f"wandb_project: {wandb_project}\n"
            f"wandb_run_name: {wandb_run_name}\n"
            f"wandb_watch: {wandb_watch}\n"
            f"wandb_log_model: {wandb_log_model}\n"
            f"resume_from_checkpoint: {resume_from_checkpoint or False}\n"
            f"prompt template: {prompt_template_name}\n"
        )
    assert (
        base_model
    ), "Please specify a --base_model, e.g. --base_model='huggyllama/llama-7b'"
    assert (
        method_name
    ), "Please specify a --method_name, e.g. --method_name='bilevel'"
    
    dataset_order = get_dataset_order(dataset_id)
    
    # new  新添加内容
    # 遍历每一个service
    # 注意下一个要从上一个的checkpoint处继续开始
    # 支持断点回复操作
    print(f"current service name: {dataset_order[task_id]}... begin fine tuning!")
    print(f"memory_data_ratio is : {memory_data_ratio/100}")
    
    model_name = base_model.split("/")[-1] + "lora"
    output_dir = os.path.join(output_path, model_name + "_"+ method_name +"_dataset_id_"+str(dataset_id), str(task_id)+"-"+dataset_order[task_id])
    print(f"output_dir: {output_dir}")
    
    
    # 首先需要检查一下上一个service的checkpoint文件是否存在
    if task_id == 0:
        lora_weights = ""
    else:
        last_service_name = dataset_order[task_id - 1]
 
        last_checkpoint_dir = os.path.join(output_path, model_name + "_"+ method_name +"_dataset_id_"+str(dataset_id), str(task_id-1)+"-"+last_service_name)
        lora_weights = last_checkpoint_dir
        if not os.path.exists(lora_weights):
            print(f"lora_weights dir {lora_weights} not find!")
            sys.exit(1)

    print(f"lora_weights: {lora_weights}\n")

    # 获取当前数据和memory buffer
    # vanilla training 只需简单合并两个数据集去训练即可
    data = load_current_task_data(dataset_id, task_id, data_dir, cache_dir, model_name)
    if task_id > 0: # task_id是从0开始
        memory_data = load_memory_buffer(dataset_id, task_id, data_dir, memory_data_ratio, cache_dir, model_name)
        
    else:
        memory_data = None
        


    #os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3,4,5'
    
    gradient_accumulation_steps = batch_size // micro_batch_size

    prompter = Prompter(prompt_template_name)

    device_map = "auto"
    world_size = int(os.environ.get("WORLD_SIZE", 1))
    ddp = world_size != 1
    if ddp:
        device_map = {"": int(os.environ.get("LOCAL_RANK") or 0)}
        gradient_accumulation_steps = gradient_accumulation_steps // world_size

    # Check if parameter passed or if set within environ
    use_wandb = len(wandb_project) > 0 or (
        "WANDB_PROJECT" in os.environ and len(os.environ["WANDB_PROJECT"]) > 0
    )
    # Only overwrite environ if wandb param passed
    if len(wandb_project) > 0:
        os.environ["WANDB_PROJECT"] = wandb_project
    if len(wandb_watch) > 0:
        os.environ["WANDB_WATCH"] = wandb_watch
    if len(wandb_log_model) > 0:
        os.environ["WANDB_LOG_MODEL"] = wandb_log_model


    model = LlamaForCausalLM.from_pretrained(
        base_model,
        load_in_8bit=True,
        torch_dtype=torch.float16,
        device_map=device_map,
    )
    tokenizer = LlamaTokenizer.from_pretrained(base_model)

    bos = tokenizer.bos_token_id
    eos = tokenizer.eos_token_id
    pad = tokenizer.pad_token_id
    print("pre-trained model's BOS EOS and PAD token id:",bos,eos,pad," => It should be 1,2,none")

    tokenizer.pad_token_id = (
        0  # unk. we want this to be different from the eos token
    )
    tokenizer.padding_side = "left"  # Allow batched inference

    def tokenize(prompt, add_eos_token=True):
        # there's probably a way to do this with the tokenizer settings
        # but again, gotta move fast
        result = tokenizer(
            prompt,
            truncation=True,
            max_length=cutoff_len,
            padding=False,
            return_tensors=None,
        )
        if (
            result["input_ids"][-1] != tokenizer.eos_token_id
            and len(result["input_ids"]) < cutoff_len
            and add_eos_token
        ):
            result["input_ids"].append(tokenizer.eos_token_id)
            result["attention_mask"].append(1)

        result["labels"] = result["input_ids"].copy()

        return result

    def generate_and_tokenize_prompt(data_point):
        full_prompt = prompter.generate_prompt(
            data_point["instruction"],
            data_point["input"],
            data_point["output"],
        )
        tokenized_full_prompt = tokenize(full_prompt)
        if not train_on_inputs:
            user_prompt = prompter.generate_prompt(
                data_point["instruction"], data_point["input"]
            )
            tokenized_user_prompt = tokenize(
                user_prompt, add_eos_token=add_eos_token
            )
            user_prompt_len = len(tokenized_user_prompt["input_ids"])

            if add_eos_token:
                user_prompt_len -= 1

            tokenized_full_prompt["labels"] = [
                -100
            ] * user_prompt_len + tokenized_full_prompt["labels"][
                user_prompt_len:
            ]  # could be sped up, probably
        return tokenized_full_prompt

    model = prepare_model_for_int8_training(model)

    config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=lora_target_modules,
        lora_dropout=lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    if task_id == 0:
        model = get_peft_model(model, config)
        print("fine tune lora from scratch!")
    # https://github.com/tloen/alpaca-lora/issues/44
    else:
        model = PeftModel.from_pretrained(model, lora_weights, is_trainable=True)
        print("continual fine tune lora!")
    

    if resume_from_checkpoint:
        # Check the available weights and load them
        checkpoint_name = os.path.join(
            resume_from_checkpoint, "pytorch_model.bin"
        )  # Full checkpoint
        if not os.path.exists(checkpoint_name):
            checkpoint_name = os.path.join(
                resume_from_checkpoint, "adapter_model.bin"
            )  # only LoRA model - LoRA config above has to fit
            resume_from_checkpoint = (
                False  # So the trainer won't try loading its state
            )
        # The two files above have a different name depending on how they were saved, but are actually the same.
        if os.path.exists(checkpoint_name):
            print(f"Restarting from {checkpoint_name}")
            adapters_weights = torch.load(checkpoint_name)
            set_peft_model_state_dict(model, adapters_weights)
        else:
            print(f"Checkpoint {checkpoint_name} not found")

    model.print_trainable_parameters()  # Be more transparent about the % of trainable params.

    if val_set_size > 0:

        val_data = load_validation_set(data_dir, dataset_id, task_id, cache_dir, model_name)


        val_data = (
            val_data.shuffle(seed=42).map(generate_and_tokenize_prompt)
        )

        train_data = (
            data.shuffle().map(generate_and_tokenize_prompt)
        )
    else:
        train_data = data["train"].shuffle().map(generate_and_tokenize_prompt)
        val_data = None

    # new 记得添加这两行
    if memory_data is not None:
        train_data_memory = memory_data.shuffle().map(generate_and_tokenize_prompt)
        print(f"memory数据总量：{len(train_data_memory)}")
    else:
        train_data_memory = None

    if not ddp and torch.cuda.device_count() > 1:
        # keeps Trainer from trying its own DataParallelism when more than 1 gpu is available
        model.is_parallelizable = True
        model.model_parallel = True

    rankallocator = RankAllocator(
        model,
        init_warmup=50,
        beta1=beta1, 
        beta2=beta2, 
        quantile=quantile,
        rank=lora_r,
        taylor="param_first",
    )

    trainer = transformers.Trainer(
        model=model,
        train_dataset=train_data,
        train_dataset_memory=train_data_memory, # new
        eval_dataset=val_data,
        ipt_score = rankallocator,
        outer_lr=outer_lr, # new
        empty_inner_score_flag=empty_inner_score_flag, # new
        empty_outer_score_flag=empty_outer_score_flag, # new
        outer_iterations=outer_iterations, # new
        args=transformers.TrainingArguments(
            per_device_train_batch_size=micro_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            train_batch_size_outer=train_batch_size_outer,# new
            inner_iterations=inner_iterations, # new
            warmup_steps=50,
            num_train_epochs=num_epochs,
            learning_rate=learning_rate,
            fp16=True,
            logging_steps=10,
            optim="adamw_torch",
            evaluation_strategy="steps" if val_set_size > 0 else "no",
            save_strategy="steps",
            eval_steps=40 if val_set_size > 0 else None,
            save_steps=40,
            output_dir=output_dir,
            save_total_limit=2,
            load_best_model_at_end=True if val_set_size > 0 else False,
            ddp_find_unused_parameters=False if ddp else None,
            group_by_length=group_by_length,
            report_to="wandb" if use_wandb else None,
            run_name=wandb_run_name if use_wandb else None,
        ),
        data_collator=transformers.DataCollatorForSeq2Seq(
            tokenizer, pad_to_multiple_of=8, return_tensors="pt", padding=True
        ),
    )
    model.config.use_cache = False

    old_state_dict = model.state_dict
    model.state_dict = (
        lambda self, *_, **__: get_peft_model_state_dict(
            self, old_state_dict()
        )
    ).__get__(model, type(model))

    if torch.__version__ >= "2" and sys.platform != "win32":
        model = torch.compile(model)

    trainer.train(resume_from_checkpoint=resume_from_checkpoint)

    model.save_pretrained(output_dir, safe_serialization=False)

    print(
        "\n If there's a warning about missing keys above, please disregard :)"
    )




      
if __name__ == "__main__":
    fire.Fire(train)
