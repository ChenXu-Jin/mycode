import logging
from sqlglot import parse_one
from sqlglot.expressions import Expression
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
    evaluator = Evaluator(task=task, current_sql=first_time_sql)
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
    def __init__(self, task: Any, current_sql: str) -> None:
        self.is_pass = False
        self.task = task
        self.sql = current_sql
    
    def evaluate(self) -> Any:
        logging.info(f"Evaluator start working for task: {self.task.question_id}")
        sql_skeleton_schema = self.extract_sql_skeleton_and_schema()

        request_kwargs = {
            "QUESTION": self.task.question,
            "SQL": self.sql,
            "skeleton": sql_skeleton_schema["skeleton"],
            "tables": sql_skeleton_schema["tables"],
            "columns": sql_skeleton_schema["columns"],
            "conditions": sql_skeleton_schema["conditions"]
        }

        engine, prompt, parser = PipelineManager().get_engine_prompt_parser()
        sampling_count = PipelineManager().self_reflexion.get("sampling_count", 1)
        response = async_llm_chain_call(
            engine=engine, 
            prompt=prompt, 
            parser=parser, 
            request_list=[request_kwargs], 
            step="evaluator_generate_result", 
            sampling_count=sampling_count
            )[0]

        result = response[0]
        return result

    def execute_current_sql(self) -> Any:
        try:
            current_sql_result = DatabaseManager().execute_sql(sql=self.sql, fetch="one")
            return {"result": current_sql_result, "STATS": "CORRECT"}
        except Exception as e:
            logging.info(f"Error in reflecting sql: {self.sql}")
            return {"result": str(e), "STATS": "ERROR"}
    
    def extract_sql_skeleton_and_schema(self) -> Dict[str, Any]:
        """
        Parses a SQL query to extract its skeleton and schema-related elements.

        Args:
            sql (str): The SQL query to parse.

        Returns:
            dict: A dictionary containing the SQL skeleton and schema elements.
                Example:
                {
                    "skeleton": "SELECT col FROM table WHERE col = ?",
                    "tables": ["table"],
                    "columns": ["col"],
                    "conditions": ["col = ?"]
                }
        """
        # Parse SQL into an abstract syntax tree (AST)
        parsed = parse_one(self.sql)
    
        skeleton_parts = []
        tables = set()
        columns = set()
        conditions = []

        # Helper to recursively traverse the AST
        def traverse_expression(expr: Expression):
            if expr is None:
                return

            if expr.is_type("Identifier") and expr.parent and expr.parent.is_type("Table"):
                tables.add(expr.name)
            elif expr.is_type("Column"):
                columns.add(expr.name)
            elif expr.is_type("Condition"):
                # Simplify condition with placeholders
                condition_str = str(expr).replace(str(expr.args.get("this")), "?")
                conditions.append(condition_str)

            # General skeleton builder
            if expr.is_type("Literal"):
                skeleton_parts.append("?")
            else:
                skeleton_parts.append(expr.sql(dialect="sqlite"))

            for child in expr.args.values():
                traverse_expression(child)

            # Traverse the AST
        traverse_expression(parsed)

            # Generate SQL skeleton
        skeleton = " ".join(skeleton_parts)

        return {
            "skeleton": skeleton,
            "tables": list(tables),
            "columns": list(columns),
            "conditions": conditions,
        }

class SelfReflection:
    def __init__(self, task: Any) -> None:
        self.long_term_mems = []
        self.task = task
    
    def generate_feedback_mems():
        pass

    def set_long_term_memory(self, long_term_mem_item: str):
        self.long_term_mems.append(long_term_mem_item)
    
    def get_long_term_memory(self) -> List[str]:
        return self.long_term_mems