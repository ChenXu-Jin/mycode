import os
import pickle
from threading import Lock
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from database_utils.execution import execute_sql
from database_utils.utils import query_lsh, get_db_schema
from typing import Dict, List, Any, Callable

load_dotenv(override=True)
DB_ROOT_PATH=Path(os.getenv("DB_ROOT_PATH"))

class DatabaseManager:
    _instance = None
    _lock = Lock()

    def __new__(cls, db_mode=None, db_id=None):
        if (db_mode is not None) and (db_id is not None):
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._init(db_mode, db_id)
                elif cls._instance.db_id != db_id:
                    cls._instance._init(db_mode, db_id)
                return cls._instance
        else:
            if cls._instance is None:
                raise ValueError("DatabaseManager instance has not been initialized yet.")
            return cls._instance
    
    def _init(self, db_mode: str, db_id: str):
        self.db_mode = db_mode
        self.db_id = db_id
        self.lsh = None
        self.minhashes = None
        self.vector_db = None
        self._set_paths()
    
    def _set_paths(self):
        self.db_path = DB_ROOT_PATH / f"{self.db_mode}_databases" / self.db_id / f"{self.db_id}.sqlite"
        self.db_directory_path = DB_ROOT_PATH / f"{self.db_mode}_databases" / self.db_id
    
    def set_lsh(self) -> str:
        with self._lock:
            if self.lsh is None:
                try:
                    with (self.db_directory_path / "preprocessed" / f"{self.db_id}_lsh.pkl").open("rb") as file:
                        self.lsh = pickle.load(file)
                    with (self.db_directory_path / "preprocessed" / f"{self.db_id}_minhashes.pkl").open("rb") as file:
                        self.minhashes = pickle.load(file)
                    return "success"
                except Exception as e:
                    self.lsh = "error"
                    self.minhashes = "error"
                    print(f"Error loading LSH for {self.db_id}: {e}")
                    return "error"
            elif self.lsh == "error":
                return "error"
            else:
                return "success"
            
    def query_lsh(self, keyword:str, signature_size:int=20, n_gram:int=3, top_n:int=10) -> Dict[str, List[str]]:
        lsh_status = self.set_lsh()
        if lsh_status == "success":
            return query_lsh(self.lsh, self.minhashes, keyword, signature_size, n_gram, top_n)
        else:
            raise Exception(f"Error loading LSH for {self.db_id}")
    
    @classmethod
    def add_methods_to_class(cls, funcs: List[Callable]):
        for func in funcs:
            method = cls.with_db_path(func)
            setattr(cls, func.__name__, method)
    
    @staticmethod
    def with_db_path(func: Callable):
        def wrapper(self, *args, **kwargs):
            return func(self.db_path, *args, **kwargs)
        return wrapper

functions_to_add = [
    execute_sql,
    get_db_schema
]
DatabaseManager.add_methods_to_class(functions_to_add)