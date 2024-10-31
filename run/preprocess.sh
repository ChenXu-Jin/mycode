db_root_directory="/root/data/dev/dev_databases"
db_id="all"
verbose=true
signature_size=100
n_gram=3
threshold=0.01

python3 -u ./src/preprocess.py --db_root_directory "${db_root_directory}" \
                              --signature_size "${signature_size}" \
                              --n_gram "${n_gram}" \
                              --threshold "${threshold}" \
                              --db_id "${db_id}" \
                              --verbose "${verbose}"
