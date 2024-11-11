data_mode='dev'
data_path='/root/data/dev/small_dev.json'
pipeline_nodes='schema_retrieval'

########## engines ##########
engine1='gpt-3.5-turbo-0125'

entity_retrieval_mode='ask_model'

### pipeline nodes setup ###
pipeline_setup='{
    "get_keywords_from_question": {
        "engine": "'${engine1}'",
        "temperature": 0.2,
    },
    "entity_retrieval": {
        "mode": "'${entity_retrieval_mode}'"
    }
}'

echo "run start"
python -u ./src/main.py --data_mode ${data_mode} --data_path ${data_path} --pipeline_nodes ${pipeline_nodes} --pipeline_setup "$pipeline_setup"