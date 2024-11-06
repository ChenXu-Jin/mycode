import logging
import difflib
import numpy as np
from llm.llm_models import async_llm_chain_call
from pipeline.utils import node_decorator
from pipeline.pipeline_manager import PipelineManager
from database_utils.database_manager import DatabaseManager
from langchain_openai import OpenAIEmbeddings
from typing import Dict, List, Any, Tuple, Optional

EMBEDDING_FUNCTION = OpenAIEmbeddings(model="text-embedding-3-small")

@node_decorator()
def schema_retrieval(task: Any) -> Dict[str, List[str]]:
    question = task.question
    hint = task.evidence
    keywords = get_keywords_from_question(question=question, hint=hint)
    entities = entity_retrieval(keywords=keywords, question=question, hint=hint)

def get_keywords_from_question(question: str, hint: str):
    request_kwargs = {
        "HINT": hint,
        "QUESTION": question
    }

    logging.info("Fetching engine, prompt and parser")
    engine, prompt, parser = PipelineManager.get_engine_prompt_parser()
    logging.info("Initiating asynchronous LLM chain call for keyword extraction")
    response = async_llm_chain_call( 
        engine=engine,
        prompt=prompt,
        parser=parser,
        request_list=[request_kwargs],
        step="keyword_extraction",
        sampling_count=1
    )[0]
    keywords = response[0]
    
    return keywords

def entity_retrieval(keywords: List[str], question: str, hint: str) -> Dict:
    logging.info("Starting entity retrieval")
    result = {}
    

def get_similar_columns(keywords: List[str], question: str, hint: str) -> Dict[str, List[str]]:
    pass

def get_similar_column_names(keyword: str, question: str, hint: str) -> List[Tuple[str, str]]:
    keyword = keyword.strip()
    potential_column_names = [keyword]
    column, value = divided_by_equal_sign(keyword)
    if column:
        potential_column_names.append(column)
    
    potential_column_names.extend(extract_paranthesis(keyword))

    if " " in keyword:
        potential_column_names.extend(part.strip() for part in keyword.split())
    
    schema = DatabaseManager().get_db_schema()

    similar_column_names = []
    for table, columns in schema.items():
        for column in columns:
            for potential_column_name in potential_column_names:
                if does_keyword_match_column(potential_column_name, column):
                    similarity_score = get_semantic_similarity_with_openai(f"`{table}`.`{column}`", [f"{question} {hint}"])[0]
                    similar_column_names.append((table, column, similarity_score))

    similar_column_names.sort(key=lambda x: x[2], reverse=True)
    return [(table, column) for table, column, _ in similar_column_names[:1]]

def divided_by_equal_sign(string: str) -> Tuple[Optional[str], Optional[str]]:
    if "=" in string:
        left_equal = string.find("=")
        first_part = string[:left_equal].strip()
        second_part = string[left_equal + 1:].strip() if len(string) > left_equal + 1 else None
        return first_part, second_part
    return None, None

def extract_paranthesis(string: str) -> List[str]:
    paranthesis_matches = []
    open_paranthesis = []
    for i, char in enumerate(string):
        if char == "(":
            open_paranthesis.append(i)
        elif char == ")" and open_paranthesis:
            start = open_paranthesis.pop()
            found_string = string[start:i + 1]
            if found_string:
                paranthesis_matches.append(found_string)
    return paranthesis_matches

def does_keyword_match_column(keyword: str, column_name: str, threshold: float = 0.9) -> bool:
    keyword = keyword.lower().replace(" ", "").replace("_", "").rstrip("s")
    column_name = column_name.lower().replace(" ", "").replace("_", "").rstrip("s")
    similarity = difflib.SequenceMatcher(None, column_name, keyword).ratio()
    return similarity >= threshold

def get_semantic_similarity_with_openai(target_string: str, list_of_similar_words: List[str]) -> List[float]:
    target_string_embedding = EMBEDDING_FUNCTION.embed_query(target_string)
    all_embeddings = EMBEDDING_FUNCTION.embed_documents(list_of_similar_words)
    similarities = [np.dot(target_string_embedding, embedding) for embedding in all_embeddings]
    return similarities