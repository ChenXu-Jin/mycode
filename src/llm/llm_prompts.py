import logging
import os
from langchain.prompts import ChatPromptTemplate
from langchain.prompts import HumanMessagePromptTemplate
from langchain.prompts import PromptTemplate

TEMPLATES_ROOT_PATH = "templates"

def get_llm_prompt(template_name: str, schema_string: str=None) -> ChatPromptTemplate:
    template_configs = {
        "get_keywords_from_question": {"input_variables": ["HINT", "QUESTION"]},
    }

    if template_name not in template_configs:
        raise ValueError(f"Invalid template name: {template_name}")
    
    config = template_configs[template_name]
    input_variables = config["input_variables"]
    partial_variables = config.get("partial_variables", {})
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
    file_name = f"template_{template_name}.txt"
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