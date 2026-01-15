import asyncio
import json
import sqlite3
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "benchmarks/analysis_cache.db"
RUNS_DIR = Path("benchmark_runs")

# --- Classification Logic ---

ERROR_PATTERNS = [
    (r"JSONDecodeError", "Malformed JSON"),
    (r"Invalid JSON", "Malformed JSON"),
    (r"Unexpected token", "Malformed JSON"),
    (r"Field required", "Schema Violation"),
    (r"Extra inputs are not permitted", "Schema Violation"),
    (r"validation error for", "Schema Violation"),
    (r"AttributeError: module .* has no attribute 'create_agent'", "Interface Violation: Missing create_agent"),
    (r"AttributeError", "Code Logic Error"),
    (r"ImportError", "Import Error"),
    (r"ModuleNotFoundError", "Import Error"),
    (r"SyntaxError", "Syntax Error"),
    (r"IndentationError", "Syntax Error"),
    (r"TypeError", "Runtime Error"),
    (r"NameError", "Runtime Error"),
    (r"TimeoutError", "Timeout"),
    (r"DeadlineExceeded", "Timeout"),
    (r"ResourceExhausted", "Quota Limit"),
    (r"429", "Quota Limit"),
    (r"Empty response", "Empty Response"),
    (r"NoneType", "Empty Response"),
]

def classify_error(error_msg):
    if not error_msg:
        return ["Unknown"], "No error message provided."
    
    classification = []
    explanation = str(error_msg)[:300] + "..." if len(str(error_msg)) > 300 else str(error_msg)

    for pattern, category in ERROR_PATTERNS:
        if re.search(pattern, str(error_msg), re.IGNORECASE):
            if category not in classification:
                classification.append(category)
    
    if not classification:
        classification.append("Unknown Logic Error")
        
    return classification, explanation

# --- Database Actor ---

class DatabaseWriter:
    def __init__(self, db_path):
        self.db_path = db_path
        self.queue = asyncio.Queue()
        self.running = False
        self.processed_cache = set()

    async def start(self):
        self.running = True
        self._init_db()
        self._load_cache()
        asyncio.create_task(self._process_queue())

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    timestamp TEXT,
                    benchmark_name TEXT,
                    suite TEXT,
                    generator TEXT,
                    attempt_number INTEGER,
                    error_type TEXT,
                    raw_error TEXT,
                    explanation TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_runs (
                    run_id TEXT PRIMARY KEY
                )
            """)
            conn.commit()

    def _load_cache(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT run_id FROM processed_runs")
            self.processed_cache = {row[0] for row in cursor.fetchall()}

    def is_processed(self, run_id):
        return run_id in self.processed_cache

    async def _process_queue(self):
        while self.running or not self.queue.empty():
            try:
                # Wait for batch or timeout
                batch = []
                try:
                    while len(batch) < 100:
                        item = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                        batch.append(item)
                        self.queue.task_done()
                except asyncio.TimeoutError:
                    pass
                
                if batch:
                    await asyncio.to_thread(self._write_batch, batch)
                    
            except Exception as e:
                logger.error(f"DB Writer Error: {e}")
                await asyncio.sleep(1)

    def _write_batch(self, batch):
        try:
            with sqlite3.connect(self.db_path) as conn:
                failures_data = []
                processed_runs = []
                
                for item in batch:
                    type_, data = item
                    if type_ == 'failure':
                        failures_data.append(data)
                    elif type_ == 'processed':
                        processed_runs.append((data,))
                        self.processed_cache.add(data)

                if failures_data:
                    conn.executemany("""
                        INSERT INTO failures (run_id, timestamp, benchmark_name, suite, generator, attempt_number, error_type, raw_error, explanation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, failures_data)
                
                if processed_runs:
                    conn.executemany("INSERT OR IGNORE INTO processed_runs (run_id) VALUES (?)", processed_runs)
                
                conn.commit()
        except Exception as e:
            logger.error(f"SQLite Write Error: {e}")

    async def stop(self):
        self.running = False
        await self.queue.join()

    def enqueue_failure(self, failure_tuple):
        self.queue.put_nowait(('failure', failure_tuple))

    def enqueue_processed(self, run_id):
        self.queue.put_nowait(('processed', run_id))

# --- Log Processing ---

def read_file_sync(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.readlines()

async def process_log_file(file_path: Path, db_writer: DatabaseWriter):
    run_id = file_path.parent.name
    
    # Double check cache to avoid duplicate work
    if db_writer.is_processed(run_id):
        return

    logger.info(f"Processing run: {run_id}")
    
    try:
        # Offload blocking IO
        lines = await asyncio.to_thread(read_file_sync, file_path)
        
        current_generator = "Unknown"
        failures_count = 0
        
        for line in lines:
            try:
                event = json.loads(line)
                evt_type = event.get("event_type")
                data = event.get("data", {})
                
                if evt_type == "section_start":
                    name = data.get("name", "")
                    if name.startswith("Generator: ") or name.startswith("Agent: "):
                        current_generator = name.replace("Generator: ", "").replace("Agent: ", "")
                
                elif evt_type == "test_result":
                    result_status = data.get("result")
                    if result_status != "pass":
                        benchmark_name = data.get("benchmark_name")
                        suite = data.get("suite")
                        attempts = data.get("generation_attempts", [])
                        
                        if attempts:
                            # Analyze attempt one (index 0)
                            attempt = attempts[0]
                            attempt_num = attempt.get("attempt_number", 1)
                            error_msg = attempt.get("error_message") or data.get("validation_error")
                            
                            error_types, explanation = classify_error(error_msg)
                            
                            db_writer.enqueue_failure((
                                run_id,
                                datetime.now().isoformat(), 
                                benchmark_name,
                                suite,
                                current_generator,
                                attempt_num,
                                json.dumps(error_types),
                                str(error_msg),
                                explanation
                            ))
                            failures_count += 1

            except json.JSONDecodeError:
                continue
        
        db_writer.enqueue_processed(run_id)
        logger.info(f"Finished {run_id}: {failures_count} failures found.")

    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")

async def main():
    db_writer = DatabaseWriter(DB_PATH)
    await db_writer.start()
    
    # 1. Discovery
    now = datetime.now()
    cutoff = now - timedelta(days=2)
    
    tasks = []
    
    if not RUNS_DIR.exists():
        logger.warning(f"{RUNS_DIR} does not exist.")
        await db_writer.stop()
        return

    # Sort runs by date desc to process latest first
    run_dirs = sorted([d for d in RUNS_DIR.iterdir() if d.is_dir()], reverse=True)

    for run_dir in run_dirs:
        try:
            # Parse timestamp from folder name
            try:
                run_time = datetime.strptime(run_dir.name, "%Y-%m-%d_%H-%M-%S")
            except ValueError:
                continue

            if run_time >= cutoff:
                if db_writer.is_processed(run_dir.name):
                    continue
                    
                log_file = run_dir / "trace.jsonl"
                if log_file.exists():
                    tasks.append(process_log_file(log_file, db_writer))
        except Exception:
            continue
                
    if not tasks:
        logger.info("No new logs found from the last 2 days.")
    else:
        logger.info(f"Found {len(tasks)} logs to process.")
        # 2. Concurrency
        sem = asyncio.Semaphore(10)
        
        async def sem_task(task):
            async with sem:
                await task

        await asyncio.gather(*(sem_task(t) for t in tasks))
    
    await db_writer.stop()
    logger.info("Analysis complete.")

if __name__ == "__main__":
    asyncio.run(main())