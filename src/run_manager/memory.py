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
        self.candidate_feedback = List[str]
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

    def update_memory(self) -> None:
        '''
        接收新的长期记忆进行整合
        '''
        logging.info("Update long term memory")
        new_long_term_memory = self.feedback_summarize()
        if new_long_term_memory is not None:
            if len(self.long_term_memory) > self.max_memory_count:
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
    
    def feedback_summarize(self) -> str:
        print("Summerizing candidate memories for LONG TERM MEMORY")
        if self.candidate_feedback is None:
            print("No candidate memory has been store")
            return None
        
        request_kwargs = {
            "QUESTION": "",
        }

        feedback_str = "\n".join(self.candidate_feedback)

        engine, prompt, parser = PipelineManager().get_engine_prompt_parser(
            feedback_str = feedback_str
        )
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
        new_long_term_memory = result_dict[0]

        return new_long_term_memory
        
    def handle_candidate_feedback(self, operator: str, **kwargs: Any) -> Any:
        if operator is None:
            raise ValueError("The operator cannot be empty; it should be ins, del, or sum.")
        
        if operator == "ins":
            if kwargs["new_memory"] is None:
                raise ValueError("No new candidate memory input")
            self.candidate_feedback.append(kwargs["new_memory"])
        if operator == "del":
            self.candidate_feedback.clear()
        if operator == "sum":
            new_long_term_memory = self.feedback_summarize()
            return new_long_term_memory