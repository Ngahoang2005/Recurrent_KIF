# 设置起始变量

for data_id in 1 2 3 4 5 6
do
    CUDA_VISIBLE_DEVICES=3 python src/generate_avgPerf_t5lora.py \
        --base_model 'your_model_path' \
        --dataset_id=${data_id} \
        --method_name='RKIF' \

done