import logging
from llm.llm_models import async_llm_chain_call
from pipeline.utils import node_decorator
from database_utils.database_manager import DatabaseManager
from pipeline.pipeline_manager import PipelineManager
from typing import Dict, List, Any

@node_decorator(check_schema_status=False)
def sql_generation(task: Any, tentative_schema: Dict[str, Any], execution_history: Dict[str, Any]) -> Dict[str, Any]:
    request_kwargs = {
        "QUESTION": task.question,
        "HINT": task.evidence
    }

    db_schema_string = DatabaseManager().get_database_schema_string(tentative_schema)

    logging.info("Fetching engine, prompt and parser")
    engine, prompt, parser = PipelineManager().get_engine_prompt_parser(schema_string=db_schema_string)
    logging.info("Initiating asynchronous LLM chain call for keyword extraction")
    sampling_count = PipelineManager().sql_generation.get("sampling_count", 1)
    response = async_llm_chain_call(
        engine=engine, 
        prompt=prompt, 
        parser=parser, 
        request_list=[request_kwargs], 
        step="sql_generate", 
        sampling_count=sampling_count
        )[0]

    sqls = [res["SQL"] for res in response]
    sql = DatabaseManager().aggregate_sqls(sqls)
    result = next(res for res in response if res["SQL"] == sql)

    logging.info("sql generation complete")
    return result