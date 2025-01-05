import logging
from threading import Lock
from typing import Dict, List, Any

NORMAL_MEMORY = '''
1. When you need to find the highest or lowest values based on a certain condition, using ORDER BY + LIMIT 1 is prefered over using MAX/MIN within sub queries.
2. If predicted query includes an ORDER BY clause to sort the results, you should only include the column(s) used for sorting in the SELECT clause if the question specifically ask for them. Otherwise, omit these columns from the SELECT.
3. If the question doesn't specify exactly which columns to select, between name column and id column, prefer to select id column.
4. Make sure you only output the information that is asked in the question. If the question asks for a specific column, make sure to only include that column in the SELECT clause, nothing more.
5. Predicted query should return all of the information asked in the question without any missing or extra information.
6. For key phrases mentioned in the question, we have provided the most similar values within the columns denoted by "-- examples" in front of the corresponding column names. This is a crucial hint indicating the correct columns to use for your SQL query.
7. No matter of how many things the question asks, you should only return one SQL query as the answer having all the information asked in the question, seperated by a comma.
8. Never use || to concatenate columns in the SELECT. Rather output the columns as they are.
9. If you are joining multiple tables, make sure to use alias names for the tables and use the alias names to reference the columns in the query. Use T1, T2, T3, ... as alias names.
10. If you are doing a logical operation on a column, such as mathematical operations and sorting, make sure to filter null values within those columns.
'''

class Memory:
    _instance = None
    _lock = Lock()

    def __new__(cls, max_memory_count: int):
        if max_memory_count is not None:
            with cls._lock:
                cls._instance = super(Memory, cls).__new__(cls)
                cls._instance.__init__()
        else:
            if cls._instance is None:
                raise ValueError("Long term memory instance has not been initialized yet.")
        return cls._instance
    
    def __init__(self, max_memory_counts: int):
        self.max_memory_counts = max_memory_counts
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
        
        return init_memory

    def update_memory(self, new_long_term_memory: str) -> None:
        '''
        接收新的长期记忆进行整合
        '''
        logging.info("Update long term memory")
        if len(self.long_term_memory) > self.max_memory_counts:
            self.long_term_memory['dynamic'].pop()
        self.long_term_memory['dynamic'].append(new_long_term_memory)

    def get_exist_memory(self) -> str:
        '''
        将长期记忆列表拼接成字符串并输出
        '''
        result = []
        
        for index, memory_item in enumerate(self.long_term_memory['static'], start=1):
            result.append(f"{index}. {memory_item}")
        
        for index, memory_item in enumerate(self.long_term_memory['dynamic'], start=len(self.long_term_memory['static'])+1):
            result.append(f"{index}. {memory_item}")

        return "\n".join(result)