import logging
import pickle
from pathlib import Path
from datasketch import MinHash, MinHashLSH
from database_utils.preprocess import _create_minhash
from database_utils.execution import execute_sql
from typing import Dict, List, Tuple

#==================== Queries the LSH for similar values ====================#
def query_lsh(lsh:MinHashLSH, minhashes:Dict[str, Tuple[MinHash, str, str, str]], keyword: str, signature_size:int=20, n_gram:int=3, top_n:int=10) -> Dict[str, Dict[str, List[str]]]:
    query_minhash = _create_minhash(signature_size, keyword, n_gram)
    results = lsh.query(query_minhash)

    similarities = [(result, _jaccard_similarity(query_minhash, minhashes[result][0])) for result in results]
    similarities = sorted(similarities, key=lambda x: x[1], reverse=True)[:top_n]

    similar_values_trimmed: Dict[str, Dict[str, List[str]]] = {}
    for result, similarity in similarities:
        table_name, column_name, value = minhashes[result][1:]
        if table_name not in similar_values_trimmed:
            similar_values_trimmed[table_name] = {}
        if column_name not in similar_values_trimmed[table_name]:
            similar_values_trimmed[table_name][column_name] = []
        similar_values_trimmed[table_name][column_name].append(value)

    return similar_values_trimmed

def load_db_lsh(db_directory_path: str) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    db_id = Path(db_directory_path).name
    try:
        with open(Path(db_directory_path) / "preprocessed" / f"{db_id}_lsh.pkl", "rb") as file:
            lsh = pickle.load(file)
        with open(Path(db_directory_path) / "preprocessed" / f"{db_id}_minhashes.pkl", "rb") as file:
            minhashes = pickle.load(file)
        return lsh, minhashes
    except Exception as e:
        logging.error(f"Error loading LSH for {db_id}: {e}")
        raise e

def _jaccard_similarity(x: MinHash, y: MinHash) -> float:
    return x.jaccard(y)

#==================== Retrieves the schema of the database ====================#
def get_db_schema(db_path: str) -> Dict[str, List[str]]:
    try:
        table_names = get_tables_from_db(db_path)
        return {table_name: get_columns_from_table(db_path, table_name) for table_name in table_names}
    except Exception as e:
        logging.error(f"Error in get_db_schema: {e}")
        raise e

def get_tables_from_db(db_path: str) -> List[str]:
    try:
        raw_table_names = execute_sql(db_path, "SELECT name FROM sqlite_master WHERE type='table';")
        return [table[0].replace('\"', '').replace('`', '') for table in raw_table_names if table[0] != "sqlite_sequence"]
    except Exception as e:
        logging.error(f"Error in get_db_all_tables: {e}")
        raise e

def get_columns_from_table(table_name: str, db_path: str) -> List[str]:
    try:
        table_info_rows = execute_sql(db_path, f"PRAGMA table_info(`{table_name}`);")
        return [row[1].replace('\"', '').replace('`', '') for row in table_info_rows]
    except Exception as e:
        logging.error(f"Error in get_table_all_columns: {e}\nTable: {table_name}")
        raise e