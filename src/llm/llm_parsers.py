import logging
import re
# import json
from langchain_core.output_parsers.base import BaseOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Dict, List, Any

class PythonListOutputParser(BaseOutputParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def parse(self, output: str) -> Any:
        logging.debug(f"Parsing output with PythonListOutputParser: {output}")
        if "```python" in output:
            output = output.split("```python")[1].split("```")[0]
        output = re.sub(r"^\s+", "", output)
        return eval(output)

# class SafeJsonOutputParser(BaseOutputParser):
#     """一个安全的 JSON 解析器，可以从 Claude 的输出中提取 JSON 并解析成 Pydantic 对象"""

#     def __init__(self, pydantic_object: type[BaseModel]):
#         super().__init__()
#         self.pydantic_object = pydantic_object  # 确保正确存储 Pydantic 模型

#     def parse(self, output: str):
#         """从 LLM 输出中提取 JSON 并解析"""
#         logging.debug(f"Raw LLM Output: {output}")

#         # 1. 尝试提取 JSON 代码块（适配 Claude 可能的额外文本）
#         match = re.search(r"\{[\s\S]*\}", output)
#         if match:
#             json_str = match.group(0)
#         else:
#             logging.error(f"Could not extract JSON from output: {output}")
#             raise ValueError(f"Could not extract JSON from output: {output}")

#         # 2. 解析 JSON
#         try:
#             json_obj = json.loads(json_str)
#             return self.pydantic_object(**json_obj)  # 使用 Pydantic 解析
#         except json.JSONDecodeError as e:
#             logging.error(f"JSON decoding error: {e}")
#             raise ValueError(f"Invalid JSON format: {json_str}")

#     def get_format_instructions(self) -> str:
#         """告诉 LLM 需要返回 JSON 格式"""
#         return "Please return a JSON object following the required schema."

#     @property
#     def _type(self) -> str:
#         """返回解析器的类型"""
#         return "safe_json"

class SQLGenerationOutputParser(BaseModel):
    chain_of_thought_reasoning: str = Field(description="Your thought process on how you arrived at the final SQL query.")
    SQL: str = Field(description="The generated SQL query in a single string.")

class SelfReflectionOutputParser(BaseModel):
    feedback: str = Field(description="Specific, actionable steps to modify the SQL query to align with the question's intent.")

class MemoryGenerationParser(BaseModel):
    step: str = Field(description="The step you must check when generating SQL statements.")

def get_llm_parser(parser_name: str):
    parser_configs = {
        "keyword_extraction": PythonListOutputParser,
        "sql_generation": lambda: JsonOutputParser(pydantic_object=SQLGenerationOutputParser),
        "actor_generate_sql": lambda: JsonOutputParser(pydantic_object=SQLGenerationOutputParser),
        "generate_feedback_mems": lambda: JsonOutputParser(pydantic_object=SelfReflectionOutputParser),
        "feedback_summarize": lambda: JsonOutputParser(pydantic_object=MemoryGenerationParser)
    }

    if parser_name not in parser_configs:
        logging.error(f"Invalid parser name: {parser_name}")
        raise ValueError(f"Invalid parser name: {parser_name}")
    
    logging.info(f"Retrieving parser for: {parser_name}")
    parser = parser_configs[parser_name]() if callable(parser_configs[parser_name]) else parser_configs[parser_name]
    return parser