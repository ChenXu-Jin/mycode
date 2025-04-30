import logging
from pipeline.pipeline_manager import PipelineManager
from llm.llm_models import async_llm_chain_call
from threading import Lock
from typing import Dict, List, Any

NORMAL_MEMORY = '''
1. Prefer ORDER BY + LIMIT over MAX/MIN: When finding the highest or lowest values, prioritize using ORDER BY + LIMIT 1 instead of MAX/MIN in subqueries.
2. Select columns as needed: Include sorting columns in SELECT only if explicitly requested. If no specific columns are mentioned, prefer the id column over the name column.
3. Match the question's requirements precisely: Ensure the query returns only the columns and information explicitly asked for, avoiding extra or missing content.
4. Use table aliases and filter nulls: When joining multiple tables, use T1, T2, ... as table aliases and filter null values in columns used for logical operations (e.g., sorting or calculations).
5. Avoid column concatenation: Do not use || to concatenate columns in SELECT; output the columns as they are.
'''

DYNAMIC_MEMORY = '''
1. Verify if the query requires both aggregate calculations (e.g., AVG, SUM, COUNT) across a set of rows and details from individual rows within that set. If so, calculate the aggregate value independently (e.g., using a subquery or window function) rather than mixing it directly with the selection of individual row columns in the main SELECT clause.
2. Confirm if conditions involving MIN/MAX require all tied records; use aggregate functions (MIN/MAX) for comparison instead of `ORDER BY ... LIMIT 1` to include all ties.
3. Confirm that table joins and filter conditions accurately map the entities (e.g., posts, users, votes) and constraints (e.g., owner name, vote count) described in the question.
4. Verify the database schema to confirm how entities (e.g., posts, users, tags, comments) are related and which specific columns store the required information before constructing joins and selecting columns.
5. When performing arithmetic operations on aggregate function results (e.g., SUM, AVG), check if the aggregate function could return NULL (e.g., if no rows match the condition). If so, use COALESCE or a similar function to replace potential NULLs with a default value (like 0) to ensure the arithmetic operation yields a numerical result.
6. Verify how conditions like 'no value' or specific categories (e.g., 'no eye color') are represented in the database schema or data (e.g., check if it's represented by NULL or a specific ID/placeholder value).
7. Ensure string comparisons in WHERE clauses are case-insensitive, using functions like LOWER() or UPPER() when comparing against literal values or potentially mixed-case data.
8. Verify if the condition in the question should filter rows before aggregation (WHERE clause) or define the value/group within the aggregation function (e.g., CASE inside AVG/COUNT).
9. Verify that the column specified in the `WHERE` clause condition exists in the correct table, and use `JOIN` if the condition column and the selected columns are in different tables.
10. Ensure that values extracted from the question (e.g., names, locations) are correctly mapped to the actual data values present in the relevant database columns.
'''

class Memory:
    _instance = None
    _lock = Lock()

    def __new__(cls, max_memory_count: int = None):
        if max_memory_count is not None:
            with cls._lock:
                cls._instance = super(Memory, cls).__new__(cls)
                cls._instance._init(max_memory_count=max_memory_count)
        else:
            if cls._instance is None:
                raise ValueError("Long term memory instance has not been initialized yet.")
        return cls._instance
    
    def _init(self, max_memory_count: int):
        self.max_memory_count = max_memory_count
        # 长期记忆存储
        self.long_term_memory = self.initialize_long_term_memory()

    def initialize_long_term_memory(self) -> Dict[str, List[str]]:
        init_memory = {
            'static': [],
            'dynamic': []
        }

        lines = NORMAL_MEMORY.strip().split('\n')
        for line in lines:
            content = line.split(' ', 1)[1]
            init_memory['static'].append(content)
        
        if DYNAMIC_MEMORY != '''''':
            lines1 = DYNAMIC_MEMORY.strip().split('\n')
            for line in lines1:
                content = line.split(' ', 1)[1]
                init_memory['dynamic'].append(content)
        
        return init_memory

    def update_memory(self, incorrect_sql: List[str], correct_sql: str, question: str) -> None:
        '''
        接收新的长期记忆进行整合
        '''
        logging.info("Update long term memory")

        new_long_term_memory = self.feedback_summarize(incorrect_sql, correct_sql, question)

        if new_long_term_memory is not None:
            if len(self.long_term_memory['dynamic']) >= self.max_memory_count:
                self.long_term_memory['dynamic'].pop(0)
            self.long_term_memory['dynamic'].append(new_long_term_memory)
            print(len(self.long_term_memory['dynamic']))

    def get_exist_memory(self, current_sql_feedback: str) -> str:
        '''
        将长期记忆列表拼接成字符串并输出
        '''
        result = []
        
        for index, memory_item in enumerate(self.long_term_memory['static'], start=1):
            result.append(f"{index}. {memory_item}")
        
        for index, memory_item in enumerate(self.long_term_memory['dynamic'], start=len(self.long_term_memory['static'])+1):
            result.append(f"{index}. {memory_item}")

        result.append(f"{len(result)+1}. {current_sql_feedback}")

        return "\n".join(result)
    
    def feedback_summarize(self, incorrect_sql: List[str], correct_sql: str, question: str) -> str:
        print("Summerizing candidate memories for LONG TERM MEMORY")
        incorrect_sql_str = "\n".join(incorrect_sql)

        request_kwargs = {
            "QUESTION": question,
            "INCORRECT_SQL": incorrect_sql_str,
            "CORRECT_SQL": correct_sql
        }

        engine, prompt, parser = PipelineManager().get_engine_prompt_parser()
        sampling_count = PipelineManager().self_reflexion.get("sampling_count", 1)
        response = async_llm_chain_call(
            engine=engine,
            prompt=prompt,
            parser=parser,
            request_list=[request_kwargs],
            step="Feedback summarize",
            sampling_count=sampling_count
        )[0]

        result_dict = response[0]
        new_long_term_memory = result_dict["step"]

        return new_long_term_memory