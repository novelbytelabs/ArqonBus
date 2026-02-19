
import sys
import time
from arqonbus.holonomy import engine, HolonomyVerdict, DEFAULT_WORLD_SIZE

def test_consistency_engine():
    print("--- Testing Topological Truth Engine (Service Layer) ---")
    
    # 1. Initialize
    if not engine.kernel:
        print("❌ FAILED: Engine Kernel not initialized")
        sys.exit(1)
    
    print(f"Kernel Online: Size={DEFAULT_WORLD_SIZE}")
    
    # 2. Verify Consistent Flow
    # 0 -> 1 (Same)
    # 1 -> 2 (Same)
    print("Injecting Flow: 0 -> 1 -> 2 (Consistent)")
    v1 = engine.verify_triplet(0, 1, 0)
    v2 = engine.verify_triplet(1, 2, 0)
    
    if v1 != HolonomyVerdict.CONSISTENT or v2 != HolonomyVerdict.CONSISTENT:
        print(f"❌ FAILED: Expected CONSISTENT, got {v1}, {v2}")
        sys.exit(1)
        
    # 3. Verify Transitive Truth
    # 0 -> 2 (Same) - implicitly true
    print("Checking Transitive Truth: 0 -> 2")
    v3 = engine.verify_triplet(0, 2, 0)
    # Should be CONSISTENT (or 'redundant' but consistent)
    if v3 != HolonomyVerdict.CONSISTENT:
        print(f"❌ FAILED: Transitive check failed: {v3}")
        sys.exit(1)
        
    # 4. Verify The Lie
    # 0 -> 2 (Different) - Contradiction!
    print("Injecting Lie: 0 != 2")
    v4 = engine.verify_triplet(0, 2, 1)
    
    if v4 == HolonomyVerdict.CONTRADICTION:
        print("✅ LIE CAUGHT! (Verdict: CONTRADICTION)")
    else:
        print(f"❌ FAILED: Lie accepted as {v4}")
        sys.exit(1)
        
    print("\n✅ Service Layer Verified.")

if __name__ == "__main__":
    test_consistency_engine()
