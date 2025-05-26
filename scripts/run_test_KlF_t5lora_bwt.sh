#!/bin/bash

# 设置起始变量 从0开始，14截至，不是15截至了
begin_id=0

for data_id in 1 2 3 4 5 6
do
    # 循环从 begin_id 到 15
    for ((ORDER=$begin_id; ORDER<14; ORDER++))
    do
        # 执行 Python 文件，传递参数 $i
        CUDA_VISIBLE_DEVICES=3 python src/generate_bwt_t5lora.py \
            --base_model 'your_model_path' \
            --dataset_id=${data_id} \
            --service_begin_id=${ORDER} \
            --method_name='RKIF' \
            
        # 可以在这里添加任何你需要的其他操作，如等待一段时间等
    done
done