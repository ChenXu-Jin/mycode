import logging
import difflib
import numpy as np
import concurrent.futures
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

def entity_retrieval(keywords: List[str], question: str, hint: str) -> Dict[str, Any]:
    logging.info("Starting entity retrieval")
    result = {}
    similar_columns = get_similar_columns(keywords=keywords, question=question, hint=hint)
    similar_entities = get_similar_entities(keywords=keywords)
    result = {
        "similar_columns": similar_columns,
        "similar_entities": similar_entities
    }

    return result
'''
retrieving similar columns for keywords
'''
def get_similar_columns(keywords: List[str], question: str, hint: str) -> Dict[str, List[str]]:
    logging.info("Retrieving similar columns")
    selected_columns = {}
    for keyword in keywords:
        similar_columns = get_similar_column_names(keyword=keyword, question=question, hint=hint)
        for table_name, column_name in similar_columns:
            selected_columns.setdefault(table_name, []).append(column_name)
    return selected_columns

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
'''
retrieving similar entities for keywords
'''
def get_similar_entities(keywords: List[str]) -> Dict[str, Dict[str, List[str]]]:
    logging.info("Retrieving similar entities")
    selected_values = {}

    def get_similar_values_target_string(target_string: str):
        unique_similar_values = DatabaseManager().query_lsh(keyword=target_string, signature_size=100, top_n=10)
        return target_string, get_similar_entities_to_keyword(target_string, unique_similar_values)

    for keyword in keywords:
        keyword = keyword.strip()
        to_search_values = [keyword]
        if (" " in keyword) and ("=" not in keyword):
            for i in range(len(keyword)):
                if keyword[i] == " ":
                    first_part = keyword[:i]
                    second_part = keyword[i+1:]
                    if first_part not in to_search_values:
                        to_search_values.append(first_part)
                    if second_part not in to_search_values:
                        to_search_values.append(second_part)
        
        to_search_values.sort(key=len, reverse=True)
        hint_column, hint_value = divided_by_equal_sign(keyword)
        if hint_value:
            to_search_values = [hint_value, *to_search_values]
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(get_similar_values_target_string, ts): ts for ts in to_search_values}
            for future in concurrent.futures.as_completed(futures):
                target_string, similar_values = future.result()
                print(similar_values)
                for table_name, column_values in similar_values.items():
                    for column_name, entities in column_values.items():
                        if entities:
                            selected_values.setdefault(table_name, {}).setdefault(column_name, []).extend(
                                [(ts, value, edit_distance, embedding) for ts, value, edit_distance, embedding in entities]
                            )

    for table_name, column_values in selected_values.items():
        for column_name, values in column_values.items():
            max_edit_distance = max(values, key=lambda x: x[2])[2]
            selected_values[table_name][column_name] = list(set(
                value for _, value, edit_distance, _ in values if edit_distance == max_edit_distance
            ))
    return selected_values

def get_similar_entities_to_keyword(keyword: str, unique_values: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, List[Tuple[str, str, float, float]]]]:
    return {
        table_name: {
            column_name: get_similar_values(keyword, values)
            for column_name, values in column_values.items()
        }
        for table_name, column_values in unique_values.items()
    }

def get_similar_values(target_string: str, values: List[str]) -> List[Tuple[str, str, float, float]]:
    edit_distance_threshold = 0.3
    top_k_edit_distance = 5
    embedding_similarity_threshold = 0.6
    top_k_embedding = 1

    edit_distance_similar_values = [
        (value, difflib.SequenceMatcher(None, value.lower(), target_string.lower()).ratio())
        for value in values
        if difflib.SequenceMatcher(None, value.lower(), target_string.lower()).ratio() >= edit_distance_threshold
    ]
    edit_distance_similar_values.sort(key=lambda x: x[1], reverse=True)
    edit_distance_similar_values = edit_distance_similar_values[:top_k_edit_distance]

    similarities = get_semantic_similarity_with_openai(target_string, [value for value, _ in edit_distance_similar_values])
    embedding_similar_values = [
        (target_string, edit_distance_similar_values[i][0], edit_distance_similar_values[i][1], similarities[i])
        for i in range(len(edit_distance_similar_values))
        if similarities[i] >= embedding_similarity_threshold
    ]
    embedding_similar_values.sort(key=lambda x: x[2], reverse=True)

    return embedding_similar_values[:top_k_embedding]