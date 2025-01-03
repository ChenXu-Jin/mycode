import logging
from threading import Lock
from typing import Dict, List, Any

NORMAL_MEMORY = '''
1. If you are joining multiple tables, make sure to use alias names for the tables and use the alias names to reference the columns in the query. Use T1, T2, T3, ... as alias names.
2. Predicted query should return all of the information asked in the question without any missing or extra information.
3. 
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
            self.long_term_memory.pop()
        self.long_term_memory.append(new_long_term_memory)

    def get_exist_memory(self) -> str:
        '''
        将长期记忆列表拼接成字符串并输出
        '''
        result = "\n".join(f"{i+1}. {s}" for i, s in enumerate(self.long_term_memory))
        return result