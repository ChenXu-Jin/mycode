data_mode='dev'
data_path='/root/data/dev/small_dev.json'

#all nodes: keyword_extraction schema_filter sql_generation evaluation
pipeline_nodes='keyword_extraction+schema_filter+sql_generation+evaluation'

########## engines ##########
engine1='gemini-1.5-pro'
engine2='gpt-3.5-turbo'
engine3='gpt-4o-mini'
engine4='gpt-4-turbo'
engine5='claude-3-opus-20240229'

schema_filter_mode="ask_model"
### pipeline nodes setup ###
pipeline_setup='{
    "keyword_extraction": {
        "engine": "'${engine2}'",
        "temperature": 0.2,
        "base_uri": ""
    },
    "schema_filter": {
        "mode": "'${schema_filter_mode}'"
    },
    "sql_generation": {
        "engine": "'${engine3}'",
        "temperature": 0,
        "base_uri": "",
        "sampling_count": 1
    }
    "self_reflexion: {
        "engine": "'${engine3}'",
        "temperature": 0,
        "base_uri": "",
        "sampling_count": 1
    }"
}'

echo "run start"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mycode
python3 -m debugpy --listen 5678 --wait-for-client ./src/main.py \
  --data_mode ${data_mode} \
  --data_path ${data_path} \
  --pipeline_nodes ${pipeline_nodes} \
  --pipeline_setup "$pipeline_setup"
# python -u ./src/main.py --data_mode ${data_mode} --data_path ${data_path} --pipeline_nodes ${pipeline_nodes} --pipeline_setup "$pipeline_setup"