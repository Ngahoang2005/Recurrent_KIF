# 设置起始变量

for data_id in 1 2 3 4 5 6
do
    CUDA_VISIBLE_DEVICES=2 python src/generate_avgPerf.py \
        --base_model 'your_model_path' \
        --dataset_id=${data_id} \
        --method_name='RKIF' \
        --model_type='' \

done