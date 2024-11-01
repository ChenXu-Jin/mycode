import logging
import pickle
from datasketch import MinHash, MinHashLSH
from pathlib import Path
from tqdm import tqdm
from database_utils.execution import execute_sql
from typing import Dict, List, Any, Tuple

def make_db_lsh(db_directory_path: str, **kwargs: Any) -> None:
    db_id = Path(db_directory_path).name
    preprocessed_path = Path(db_directory_path) / "preprocessed"
    preprocessed_path.mkdir(exist_ok=True)

    unique_values = _get_unique_values(str(Path(db_directory_path) / f"{db_id}.sqlite"))
    logging.info("Unique values obtained")

    with open(preprocessed_path / f"{db_id}_unique_values.pkl", "wb") as file:
        pickle.dump(unique_values, file)
    logging.info("Saved unique values")

    lsh, minhashes = make_lsh(unique_values, **kwargs)

    with open(preprocessed_path / f"{db_id}_lsh.pkl", "wb") as file:
        pickle.dump(lsh, file)
    with open(preprocessed_path / f"{db_id}_minhashes.pkl", "wb") as file:
        pickle.dump(minhashes, file)

def _get_unique_values(db_path: str) -> Dict[str, Dict[str, List[str]]]:
    table_names = [table[0] for table in execute_sql(db_path, "SELECT name FROM sqlite_master WHERE type='table';", fetch="all")]
    primary_keys = []

    for table_name in table_names:
        columns = execute_sql(db_path, f"PRAGMA table_info('{table_name}')", fetch="all")
        for column in columns:
            if column[5] > 0:
                column_name = column[1]
                if column_name.lower() not in [c.lower() for c in primary_keys]:
                    primary_keys.append(column_name)
    
    unique_values: Dict[str, Dict[str, List[str]]] = {}
    for table_name in table_names:
        if table_name == "sqlite_sequence":
            continue
        logging.info(f"Processing {table_name}")
        columns = [col[1] for col in execute_sql(db_path, f"PRAGMA table_info('{table_name}')", fetch="all") if ("TEXT" in col[2] and col[1].lower() not in [c.lower() for c in primary_keys])]
        table_values: Dict[str, List[str]] = {}
        
        for column in columns:
            if any(keyword in column.lower() for keyword in ["_id", " id", "url", "email", "web", "time", "phone", "date", "address"]) or column.endswith("Id"):
                continue

            result = execute_sql(db_path, f"""
                SELECT SUM(LENGTH(unique_values)), COUNT(unique_values)
                FROM (
                    SELECT DISTINCT `{column}` AS unique_values
                    FROM `{table_name}`
                    WHERE `{column}` IS NOT NULL
                ) AS subquery
            """, fetch="one")
            sum_of_lengths, count_distinct = result
            if sum_of_lengths is None or count_distinct == 0:
                continue
         
            average_length = sum_of_lengths / count_distinct
            logging.info(f"Column: {column}, sum_of_lengths: {sum_of_lengths}, count_distinct: {count_distinct}, average_length: {average_length}")
            
            if ("name" in column.lower() and sum_of_lengths < 5000000) or (sum_of_lengths < 2000000 and average_length < 25):
                logging.info(f"Fetching distinct values for {column}")
                values = [str(value[0]) for value in execute_sql(db_path, f"SELECT DISTINCT `{column}` FROM `{table_name}` WHERE `{column}` IS NOT NULL", fetch="all")]
                logging.info(f"Number of different values: {len(values)}")
                table_values[column] = values
        
        unique_values[table_name] = table_values

    return unique_values

def make_lsh(unique_values: Dict[str, Dict[str, List[str]]], signature_size: int, n_gram: int, threshold: float, verbose: bool = True) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    lsh = MinHashLSH(threshold=threshold, num_perm=signature_size)
    minhashes: Dict[str, Tuple[MinHash, str, str, str]] = {}
    try:
        total_unique_values = sum(len(column_values) for table_values in unique_values.values() for column_values in table_values.values())
        logging.info(f"Total unique values: {total_unique_values}")
        progress_bar = tqdm(total=total_unique_values, desc="Creating LSH") if verbose else None
        for table_name, table_values in unique_values.items():
            for column_name, column_values in table_values.items():
                logging.info(f"Processing {table_name} - {column_name} - {len(column_values)}")
                
                for id, value in enumerate(column_values):
                    minhash = _create_minhash(signature_size, value, n_gram)
                    minhash_key = f"{table_name}_{column_name}_{id}"
                    minhashes[minhash_key] = (minhash, table_name, column_name, value)
                    lsh.insert(minhash_key, minhash)
                    
                    if verbose:
                        progress_bar.update(1)
        
        if verbose:
            progress_bar.close()
    except Exception as e:
        logging.error(f"Error creating LSH: {e}")

def _create_minhash(signature_size: int, string: str, n_gram: int) -> MinHash:
    m = MinHash(num_perm=signature_size)
    for d in [string[i:i + n_gram] for i in range(len(string) - n_gram + 1)]:
        m.update(d.encode('utf8'))
    return m