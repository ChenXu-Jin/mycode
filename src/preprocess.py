import os
import logging
import argparse
import multiprocessing
from dotenv import load_dotenv

load_dotenv(override=True)
PROCESS_WORKERS = 1

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def preprocess(db_id: str, args: argparse.Namespace):
    pass

if __name__ == "__main___":
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--db_root_directory', type=str, required=True, help="Root directory of the databases")
    args_parser.add_argument('--signature_size', type=int, default=20, help="Size of the MinHash signature")
    args_parser.add_argument('--n_gram', type=int, default=3, help="N-gram size for the MinHash")
    args_parser.add_argument('--threshold', type=float, default=0.01, help="Threshold for the MinHash LSH")
    args_parser.add_argument('--db_id', type=str, default='all', help="Database ID or 'all' to process all databases")
    args_parser.add_argument('--verbose', type=bool, default=True, help="Enable verbose logging")
    args_parser.add_argument('--use_value_description', type=bool, default=True, help="Include value descriptions")
    args = args_parser.parse_args()

    if args.db_id == 'all':
        with multiprocessing.Pool(PROCESS_WORKERS) as pool:
            for db_id in os.listdir(args.db_root_directory):
                pool.apply_async(preprocess, args=(db_id, args))
            pool.close()
            pool.join()
    else:
        preprocess(args.db_id, args)

    logging.info("Preprocessing is complete.")