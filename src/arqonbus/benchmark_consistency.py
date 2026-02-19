
import time
import random
import sys
from arqonbus.holonomy import engine, HolonomyVerdict

def run_benchmark():
    print("==========================================")
    print("   TOPOLOGICAL TRUTH ENGINE BENCHMARK (v1.0)    ")
    print("==========================================")
    
    # Ensure fresh start
    engine.initialize()
    if not engine.kernel:
        print("❌ Kernel missing. Aborting.")
        return

    # Configuration
    SCALES = [1000, 10000, 65536]
    OPERATIONS = 100000

    for N in SCALES:
        print(f"\n--- Scale N={N} Nodes ---")
        
        # 1. Write Benchmark (Union)
        # Create a linear chain: 0-1, 1-2, 2-3...
        print(f"Running {OPERATIONS} UNION operations...")
        start_ns = time.perf_counter_ns()
        
        for i in range(min(N-1, OPERATIONS)):
            # Link i and i+1 with parity 0
            engine.verify_triplet(i, i+1, 0)
            
        end_ns = time.perf_counter_ns()
        duration_us = (end_ns - start_ns) / 1000.0
        ops_per_sec = min(N-1, OPERATIONS) / (duration_us / 1_000_000.0)
        avg_latency_us = duration_us / min(N-1, OPERATIONS)
        
        print(f"Result: {ops_per_sec:,.0f} ops/sec")
        print(f"Latency: {avg_latency_us:.4f} µs/op")

        if avg_latency_us > 10.0:
            print("⚠️ WARNING: Latency > 10µs (Python overhead?)")

        # 2. Read Benchmark (Find/Verify)
        # Check transitivity: 0 vs Random Node in the chain
        print(f"Running {OPERATIONS} READ operations (Transitive Path Compression)...")
        
        # Verify 0 vs N/2 (Long path if not compressed)
        target = min(N-1, OPERATIONS) // 2
        
        start_ns = time.perf_counter_ns()
        for _ in range(OPERATIONS):
            # Verify 0 and target are consistent (should be True)
            engine.verify_triplet(0, target, 0)
            
        end_ns = time.perf_counter_ns()
        duration_us = (end_ns - start_ns) / 1000.0
        ops_per_sec = OPERATIONS / (duration_us / 1_000_000.0)
        avg_latency_us = duration_us / OPERATIONS
        
        print(f"Result: {ops_per_sec:,.0f} ops/sec")
        print(f"Latency: {avg_latency_us:.4f} µs/op")

    print("\n------------------------------------------")
    print("✅ Benchmark Complete.")

if __name__ == "__main__":
    run_benchmark()
