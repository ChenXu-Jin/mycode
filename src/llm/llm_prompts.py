import logging
import os
from langchain.prompts import ChatPromptTemplate
from langchain.prompts import HumanMessagePromptTemplate
from langchain.prompts import PromptTemplate
from typing import Dict, List, Any

TEMPLATES_ROOT_PATH = "templates"

def get_llm_prompt(
        template_name: str,
        **kwargs: Any
    ) -> ChatPromptTemplate:
    template_configs = {
        "keyword_extraction": {"input_variables": ["HINT", "QUESTION"]},
        "sql_generation": {"input_variables": ["HINT", "QUESTION"]},
        "evaluate": {"input_variables": ["QUESTION", "SQL"]},
        "actor_generate_sql": {"input_variables": ["HINT", "QUESTION"]},
        "generate_long_term_mems": {"input_variables": ["HINT", "QUESTION"]}
    }

    if template_name not in template_configs:
        raise ValueError(f"Invalid template name: {template_name}")

    config = template_configs[template_name]
    input_variables = config.get("input_variables", [])
    partial_variables = config.get("partial_variables", {})

    # Dynamically update partial variables based on provided kwargs
    if "long_term_mems" in kwargs and kwargs["long_term_mems"] is not Ellipsis:
        partial_variables["LONG_TERM_MEMS"] = kwargs["long_term_mems"]
    if "short_term_mems" in kwargs and kwargs["short_term_mems"] is not Ellipsis:
        partial_variables["SHORT_TERM_MEMS"] = kwargs["short_term_mems"]
    if "schema_string" in kwargs and kwargs["short_term_mems"] is not Ellipsis:
        partial_variables["DATABASE_SCHEMA"] = kwargs["schema_string"]
    if "execute_result" in kwargs and kwargs["execute_result"] is not Ellipsis:
        partial_variables["EXECUTE_RESULT"] = kwargs["execute_result"]
    if "evaluate_result" in kwargs and kwargs["evaluate_result"] is not Ellipsis:
        partial_variables["EVALUATE_RESULT"] = kwargs["evaluate_result"]

    template_content = load_template(template_name)

    human_message_prompt_template = HumanMessagePromptTemplate(
        prompt=PromptTemplate(
            template=template_content,
            input_variables=input_variables,
            partial_variables=partial_variables
        )
    )

    combined_prompt_template = ChatPromptTemplate.from_messages(
        [human_message_prompt_template]
    )

    return combined_prompt_template

def load_template(template_name: str) -> str:
    file_name = f"{template_name}.txt"
    template_path = os.path.join(TEMPLATES_ROOT_PATH, file_name)
    
    try:
        with open(template_path, "r") as file:
            template = file.read()
        logging.info(f"Template {template_name} loaded successfully.")
        return template
    except FileNotFoundError:
        logging.error(f"Template file not found: {template_path}")
        raise
    except Exception as e:
        logging.error(f"Error loading template {template_name}: {e}")
        raise