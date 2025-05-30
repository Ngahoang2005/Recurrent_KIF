#!/bin/bash

# 设置起始变量
begin_id=0

# Standard CL Benchmark
for data_id in 4 5 6
do
    # 循环从 begin_id 到 4
    for ((ORDER=$begin_id; ORDER<4; ORDER++))
    do
        # 执行 Python 文件，传递参数 $i

        CUDA_VISIBLE_DEVICES=0 python src/finetune_KIF_llama.py \
            --base_model 'your_model_path' \
            --method_name 'RKIF' \
            --num_epochs=10 \
            --cutoff_len=512 \
            --group_by_length \
            --lora_target_modules='[q_proj,v_proj]' \
            --micro_batch_size=16 \
            --batch_size=64 \
            --dataset_id=${data_id} \
            --task_id=${ORDER} \
            --inner_iterations=8 \
            --outer_iterations=4 \
            --train_batch_size_outer=64 \
            --empty_inner_score_flag=1 \



    done
done

wait

# Long Sequence Benchmark
for data_id in 1 2 3
do
    # 循环从 begin_id 到 15
    for ((ORDER=$begin_id; ORDER<15; ORDER++))
    do
        # 执行 Python 文件，传递参数 $i

        CUDA_VISIBLE_DEVICES=0 python src/finetune_KIF_llama.py \
            --base_model 'your_model_path' \
            --method_name 'RKIF' \
            --num_epochs=10 \
            --cutoff_len=512 \
            --group_by_length \
            --lora_target_modules='[q_proj,v_proj]' \
            --micro_batch_size=16 \
            --batch_size=64 \
            --dataset_id=${data_id} \
            --task_id=${ORDER} \
            --inner_iterations=8 \
            --outer_iterations=4 \
            --train_batch_size_outer=64 \
            --empty_inner_score_flag=1 \



    done
done

