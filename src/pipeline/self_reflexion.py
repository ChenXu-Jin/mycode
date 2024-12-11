import logging
from llm.llm_models import async_llm_chain_call
from database_utils.database_manager import DatabaseManager
from pipeline.pipeline_manager import PipelineManager
from pipeline.utils import node_decorator, get_last_node_result
from typing import Dict, List, Any

MAX_REFLEXION_TIMES = 5

@node_decorator(check_schema_status=False)
def self_reflexion(task: Any, tentative_schema: Dict[str, Any], execution_history: Dict[str, Any]) -> str:
    logging.info(f"LLM self reflexion start for question: {task.quesiton_id}")
    first_time_sql = get_last_node_result(execution_history, "sql_generation")
    if first_time_sql is None:
        raise ValueError("The initial SQL generaion is not yet complete, self-reflexion cannot begin")
    
    actor = Actor(task=task, tentative_schema=tentative_schema)
    evaluator = Evaluator(task=task)
    self_reflection = SelfReflection(task=task)

    actor.short_term_mems.append(first_time_sql)


    for round in range(MAX_REFLEXION_TIMES):
        logging.info(f"Reflexion round: {round}")
        long_term_mems = self_reflection.get_long_term_memory()

        sql = actor.actor_generate_sql(long_term_mems)
        assert isinstance(sql, str)

class Actor:
    def __init__(self, task: Any, tentative_schema: Dict[str, Any]) -> None:
        self.short_term_mems = []
        self.task = task
        self.tentative_schema = tentative_schema
    
    def actor_generate_sql(self, long_term_mems):
        logging.info(f"Actor start working for task: {self.task.question_id}")
        request_kwargs = {
            "QUESTION": self.task.question,
            "HINT": self.task.evidence,
            "LONG_TERM_MEMORY": long_term_mems,
            "SHORT_TERM_MEMORY": self.short_term_mems
        }

        db_schema_string = DatabaseManager().get_database_schema_string(self.tentative_schema)
        engine, prompt, parser = PipelineManager().get_engine_prompt_parser(schema_string=db_schema_string)
        sampling_count = PipelineManager().self_reflexion.get("sampling_count", 1)
        response = async_llm_chain_call(engine=engine, prompt=prompt, parser=parser, request_list=[request_kwargs], step="actor_generate_sql", sampling_count=sampling_count)

        sqls = [res["SQL"] for res in response]
        sql = DatabaseManager().aggregate_sqls(sqls)
        result = next(res for res in response if res["SQL"] == sql)
        self.short_term_mems.append(result)
        logging.info("Actor's work complete")

        return result

class Evaluator:
    def __init__(self, task) -> None:
        self.is_pass = False
        self.task = task
    
    def execute_current_sql(self, current_sql: str) -> Any:
        current_sql_result = DatabaseManager().execute_sql(sql=current_sql, fetch="one")
        return current_sql_result
    
    def evaluate(self) -> Any:
        logging.info(f"Actor start working for task: {self.task.question_id}")

class SelfReflection:
    def __init__(self, task) -> None:
        self.long_term_mems = []
        self.task = task
    
    def generate_feedback_mems():
        pass

    def set_long_term_memory(self, long_term_mem_item: str):
        self.long_term_mems.append(long_term_mem_item)
    
    def get_long_term_memory(self) -> List[str]:
        return self.long_term_mems