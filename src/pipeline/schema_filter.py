from pipeline.utils import node_decorator, get_last_node_result
from database_utils.database_manager import DatabaseManager
from typing import Dict, List, Any

@node_decorator(check_schema_status=False)
def schema_filter(task: Any, tentative_schema: Dict[str, Any], execution_history: Dict[str, Any]) -> Dict[str, Any]:
    keywords = get_last_node_result(execution_history, "keyword_extraction")
    question = task.question
    hint = task.evidence
    for keyword in keywords:
        potential_column_names = keyword_decomposition(keyword, question, hint)
    
    all_schema = DatabaseManager().get_db_schema()

    result = {}

def divied_by_equal_sign(keyword: str) -> str:
    if "=" in keyword:
        left_equal = keyword.find("=")
        column_part = keyword[:left_equal].strip()
        return column_part
    return None

def _extract_paranthesis(keyword: str) -> List[str]:
    paranthesis_matches = []
    open_paranthesis = []
    for i, char in enumerate(keyword):
        if char == "(":
            open_paranthesis.append(i)
        elif char == ")" and open_paranthesis:
            start = open_paranthesis.pop()
            found_string = keyword[start:i + 1]
            if found_string:
                paranthesis_matches.append(found_string)
    return paranthesis_matches
    
def keyword_decomposition(keyword: str) -> List[str]:
    potential_column_names = []
    keyword = keyword.strip()
    potential_column_names.append(keyword)

    _column = divied_by_equal_sign(keyword=keyword)
    if _column:
        potential_column_names.append(_column)

    potential_column_names.extend(_extract_paranthesis(keyword))

    if " " in keyword:
        potential_column_names.extend(part.strip() for part in keyword.split())

    return potential_column_names