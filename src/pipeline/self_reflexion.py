import logging
from run_manager.memory import Memory
from llm.llm_models import async_llm_chain_call
from database_utils.database_manager import DatabaseManager
from pipeline.pipeline_manager import PipelineManager
from pipeline.utils import node_decorator, get_last_node_result
from typing import Dict, List, Any

MAX_REFLEXION_TIMES = 5

@node_decorator(check_schema_status=False)
def self_reflexion(task: Any, tentative_schema: Dict[str, Any], execution_history: Dict[str, Any]) -> str:
    """
    Self-reflection loop for SQL generation and evaluation.

    Args:
        task (Any): Task containing details like question and metadata.
        tentative_schema (Dict[str, Any]): Schema details for SQL generation.
        execution_history (Dict[str, Any]): Execution history, including generated SQL.

    Returns:
        str: Final SQL query that passes evaluation.
    """
    logging.info(f"LLM self reflexion start for question: {task.question_id}")

    first_time_sql = get_last_node_result(execution_history, "sql_generation")["SQL"]
    if first_time_sql is None:
        raise ValueError(f"Initial SQL generation is incomplete for task {task.question_id}. Self-reflexion cannot begin.")

    actor = Actor(task=task, tentative_schema=tentative_schema)
    evaluator = Evaluator(task=task, current_sql=first_time_sql)
    self_reflection = SelfReflection(task=task)

    current_sql = first_time_sql
    iteration_count = 0
    while iteration_count < MAX_REFLEXION_TIMES:
        iteration_count += 1
        logging.info(f"Iteration {iteration_count}: Evaluating SQL")

        evaluation_result = evaluator.evaluate(tentative_schema)

        if evaluation_result["judgment"] == "Valid":
            if iteration_count > 1:
                Memory().update_memory(incorrect_sql=actor.short_term_mems, correct_sql=current_sql, question=task.question)
            logging.info("SQL passed evaluation")
            return {"SQL": current_sql}
        
        logging.info("SQL failed evaluation. Generating feedback.")
        execute_result = evaluator.execute_current_sql()["result"]
        current_sql_feedback = self_reflection.generate_feedback_mems(execute_result, evaluation_result, current_sql)

        long_term_mems = Memory().get_exist_memory(current_sql_feedback)

        logging.info("Generating new SQL using actor.")
        actor.short_term_mems.append(current_sql)
        actor.check_mems_length()

        current_sql = actor.actor_generate_sql(long_term_mems)
        evaluator.sql = current_sql
    
    logging.error("Max iterations reached. Could not generate a valid SQL query.")
    return {"SQL": current_sql}

class Actor:
    def __init__(self, task: Any, tentative_schema: Dict[str, Any]) -> None:
        self.short_term_mems: List[str] = []
        self.task = task
        self.tentative_schema = tentative_schema
    
    def actor_generate_sql(self, long_term_mems) -> str:
        logging.info(f"Actor start working for task: {self.task.question_id}")
        request_kwargs = {
            "QUESTION": self.task.question,
            "HINT": self.task.evidence
        }

        try:
            db_schema_string = DatabaseManager().get_database_schema_string(self.tentative_schema)
            engine, prompt, parser = PipelineManager().get_engine_prompt_parser(
                schema_string=db_schema_string, 
                long_term_mems=long_term_mems, 
                short_term_mems=self.short_term_mems
                )
            sampling_count = PipelineManager().self_reflexion.get("sampling_count", 1)
            response = async_llm_chain_call(
                engine=engine, 
                prompt=prompt, 
                parser=parser, 
                request_list=[request_kwargs], 
                step="actor_generate_sql", 
                sampling_count=sampling_count
                )[0]

            sqls = [res["SQL"] for res in response]
            sql = DatabaseManager().aggregate_sqls(sqls)

            result = next(res for res in response if res["SQL"] == sql)["SQL"]
            if result is None:
                raise ValueError("No valid SQL found in the response.")

            logging.info("Actor's work complete")
            return result
        except Exception as e:
            logging.error(f"Failed to generate SQL for task {self.task.question_id}: {e}")
            raise RuntimeError(f"Actor failed to generate SQL for task {self.task.question_id}.") from e
    
    def check_mems_length(self, max_mems_length: int = 5) -> None:
        if len(self.short_term_mems) > max_mems_length:
            self.short_term_mems.pop(0)

class Evaluator:
    def __init__(self, task: Any, current_sql: str) -> None:
        self.task = task
        self.sql = current_sql
    
    def evaluate(self, tentative_schema: Dict[str, Any]) -> Dict[str, Any]:
        logging.info(f"Evaluator start working for task: {self.task.question_id}")
        sql_execute_result = self.execute_current_sql()["result"]

        request_kwargs = {
            "QUESTION": self.task.question,
            "SQL": self.sql
        }

        engine, prompt, parser = PipelineManager().get_engine_prompt_parser(schema_string=tentative_schema)
        sampling_count = PipelineManager().self_reflexion.get("sampling_count", 1)
        response = async_llm_chain_call(
            engine=engine, 
            prompt=prompt, 
            parser=parser, 
            request_list=[request_kwargs], 
            step="evaluator_generate_result", 
            sampling_count=sampling_count
            )[0]
        
        if not response or not isinstance(response[0], dict):
            raise ValueError("Invalid response format from async_llm_chain_call.")
        result = response[0]
        
        return result

    def execute_current_sql(self) -> Any:
        try:
            current_sql_result = DatabaseManager().execute_sql(sql=self.sql, fetch="one")
            return {"result": current_sql_result, "STATS": "CORRECT"}
        except Exception as e:
            logging.error(f"Error executing SQL '{self.sql}': {e}")
            return {"result": str(e), "STATS": "ERROR"}

class SelfReflection:
    def __init__(self, task: Any) -> None:
        self.task = task
    
    def generate_feedback_mems(self, execute_result: Dict[str, Any], evaluate_result: Dict[str, Any], sql: str) -> str:
        logging.info(f"SelfReflection start working for task: {self.task.question_id}")

        request_kwargs = {
            "QUESTION": self.task.question,
            "SQL": sql
        }

        engine, prompt, parser = PipelineManager().get_engine_prompt_parser(execute_result=execute_result, evaluate_result=evaluate_result)
        sampling_count = PipelineManager().self_reflexion.get("sampling_count", 1)
        response = async_llm_chain_call(
            engine=engine, 
            prompt=prompt, 
            parser=parser, 
            request_list=[request_kwargs], 
            step="Generate feedbacks", 
            sampling_count=sampling_count
            )[0]
        
        if not response or not isinstance(response[0], dict) or "feedback" not in response[0]:
            logging.error("Invalid response from async_llm_chain_call. Missing 'feedback'.")
            raise ValueError("Response from LLM does not contain 'feedback'.")

        feedback_dict = response[0]
        feedback = feedback_dict["feedback"]
        if not isinstance(feedback, str):
            logging.warning("Feedback is not a string. Converting to string format.")
            feedback = str(feedback)

        return feedback