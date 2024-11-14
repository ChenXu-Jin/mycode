
from llm.llm_models import async_llm_chain_call
from pipeline.utils import node_decorator, get_last_node_result
from typing import Dict, List, Any

@node_decorator(check_schema_status=False)
def sql_generation(task: Any, tentative_schema: Dict[str, Any], execution_history: Dict[str, Any]):
    question = task.question
    hint = task.evidence

    