import sqlite3
import logging
import random
from typing import Dict, List, Any, Union

def execute_sql(db_path: str, sql: str, fetch: Union[str, int] = "all") -> Any:
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            if fetch == "all":
                return cursor.fetchall()
            elif fetch == "one":
                return cursor.fetchone()
            elif fetch == "random":
                samples = cursor.fetchmany(10)
                return random.choice(samples) if samples else []
            elif isinstance(fetch, int):
                return cursor.fetchmany(fetch)
            else:
                raise ValueError("Invalid fetch argument. Must be 'all', 'one', 'random', or an integer.")
    except Exception as e:
        logging.error(f"Error in execute_sql: {e}\nSQL: {sql}")
        raise e

def get_sql_result(db_path: str, sql: str, max_returned_rows: int = 30) -> Dict[str, Any]:
    try:
        result = execute_sql(db_path=db_path, sql=sql, fetch=max_returned_rows)
        return {"SQL": sql, "RESULT": result, "STATUS": "CORRECT"}
    except Exception as e:
        logging.error(f"Error in validate_sql_query: {e}")
        return {"SQL": sql, "RESULT": str(e), "STATUS": "ERROR"}

def aggregate_sqls(db_path: str, sqls: List[str]) -> str:
    results = [get_sql_result(db_path=db_path, sql=sql) for sql in sqls]
    aggregate_result = {}

    for result in results:
        if result['STATUS'] == 'OK':
            key = frozenset(tuple(row) for row in result['RESULT'])
            if key in aggregate_result:
                aggregate_result[key].append(result['SQL'])
            else:
                aggregate_result[key] = [result['SQL']]
    
    if aggregate_result:
        largest_cluster = max(aggregate_result.values(), key=len, default=[])
        if largest_cluster:
            return min(largest_cluster, key=len)