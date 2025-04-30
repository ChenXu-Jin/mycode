data_mode='dev'
data_path='/root/data/dev/DAIL-SQL.json'
is_experiments='True'

#all nodes: keyword_extraction schema_filter sql_generation self_reflexion evaluation
pipeline_nodes='keyword_extraction+schema_filter+self_reflexion+evaluation'
max_memory_count=10

########## engines ##########
engine1='gemini-1.5-pro'
engine2='gpt-3.5-turbo'
engine3='gpt-4o-mini'
engine4='gpt-4-turbo'
engine5='gemini-2.0-flash'
engine6='gemini-2.0-pro-exp-02-05'
engine7='gemini-2.5-pro-exp-03-25'

schema_filter_mode="ask_model"
### pipeline nodes setup ###
pipeline_setup='{
    "keyword_extraction": {
        "engine": "'${engine3}'",
        "temperature": 0.2,
        "base_uri": ""
    },
    "schema_filter": {
        "mode": "'${schema_filter_mode}'"
    },
    "sql_generation": {
        "engine": "'${engine6}'",
        "temperature": 0,
        "sampling_count": 1,
        "base_uri": ""
    },
    "self_reflexion": {
        "engine": "'${engine7}'",
        "temperature": 0,
        "sampling_count": 1,
        "base_uri": ""
    },
    "feedback_summarize": {
        "engine": "'${engine7}'",
        "temperature": 0,
        "base_uri": ""
    }
}'

echo "run start"
# source ~/miniconda3/etc/profile.d/conda.sh
# conda activate mycode
# python3 -m debugpy --listen 5678 --wait-for-client ./src/main.py \
#   --data_mode ${data_mode} \
#   --data_path ${data_path} \
#   --pipeline_nodes ${pipeline_nodes} \
#   --pipeline_setup "$pipeline_setup" \
#   --max_memory_count ${max_memory_count} \
#   --is_experiments ${is_experiments}
python -u ./src/main.py \
    --data_mode ${data_mode} \
    --data_path ${data_path} \
    --pipeline_nodes ${pipeline_nodes} \
    --pipeline_setup "$pipeline_setup" \
    --max_memory_count ${max_memory_count} \
    --is_experiments ${is_experiments}