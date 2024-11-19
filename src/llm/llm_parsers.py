import logging
import json
import re
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

class SQLGenerationOutputParser(BaseModel):
    chain_of_thought_reasoning: str = Field(description="One line explanation of why or why not the column information is relevant to the question and the hint.")
    is_column_information_relevant: str = Field(description="Yes or No")

def get_llm_parser(parser_name: str):
    parser_configs = {
        "keyword_extraction": PythonListOutputParser,
        "sql_generation": lambda: JsonOutputParser(pydantic_object=SQLGenerationOutputParser)
    }

    if parser_name not in parser_configs:
        logging.error(f"Invalid parser name: {parser_name}")
        raise ValueError(f"Invalid parser name: {parser_name}")
    
    logging.info(f"Retrieving parser for: {parser_name}")
    parser = parser_configs[parser_name]() if callable(parser_configs[parser_name]) else parser_configs[parser_name]
    return parser