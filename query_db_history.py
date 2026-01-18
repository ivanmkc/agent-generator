import sqlite3

DB_PATH = "benchmarks/analysis_cache.db"

def query_history():
    conn = sqlite3.connect(DB_PATH)
    
    targets = [
        "api_understanding:which_plugin_callback_method_can_return_a_value_to",
        "api_understanding:where_does_the_adk_define_the_data_model_for_a_ses",
        "api_understanding:what_is_the_foundational_class_for_all_agents_in_t"
    ]
    
    print(f"Querying history for {len(targets)} cases...\n")
    
    for t in targets:
        print(f"--- {t} ---")
        query = "SELECT run_id, generator, error_type, explanation FROM failures WHERE benchmark_name = ? ORDER BY run_id DESC LIMIT 5"
        try:
            cursor = conn.execute(query, (t,))
            rows = cursor.fetchall()
            if not rows:
                print("  No historical failures found in DB.")
            for r in rows:
                print(f"  Run: {r[0]} | Gen: {r[1]}")
                print(f"    Error: {r[2]}")
                print(f"    Exp: {r[3][:100]}...")
        except Exception as e:
            print(f"  DB Error: {e}")

if __name__ == "__main__":
    query_history()

