import json
import argparse
from datetime import datetime
from run_manager.run_manager import RunManager
from typing import Dict, List, Any

def args_parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_mode', type=str, required=True)
    parser.add_argument('--data_path', type=str, required=True)
    parser.add_argument('--pipeline_nodes', type=str, required=True)
    parser.add_argument('--pipeline_setup', type=str, required=True)
    parser.add_argument('--log_level', type=str, default='warning')
    args = parser.parse_args()
    args.run_start_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    return args

def load_dataset(data_path: str) -> List[Dict[str, Any]]:
    with open(data_path, 'r') as file:
        dataset = json.load(file)
    return dataset

def main():
    args = args_parse()
    dataset = load_dataset(args.data_path)
    
    runner = RunManager(args)
    runner.initialize_tasks(dataset)
    runner.run_tasks()
    runner.generate_sql_files()

if __name__ == '__main__':
    main()