import numpy as np
import optuna
import time

# ==========================================
# 1. Structured Problem: 20D Rosenbrock
# ==========================================
def rosenbrock_XD(x):
    """
    Rosenbrock function: The "Banana Valley".
    Global minimum at (1,1,...,1) with value 0.
    Highly structured, curved dependency between variables.
    Search Domain: [-5, 5]^D
    """
    x = np.array(x)
    return np.sum(100.0 * (x[1:] - x[:-1]**2.0)**2.0 + (1 - x[:-1])**2.0)

def get_primes(n_max):
    primes = []
    is_prime = [True] * (n_max + 1)
    for p in range(2, n_max + 1):
        if is_prime[p]:
            primes.append(p)
            for i in range(p * p, n_max + 1, p):
                is_prime[i] = False
    return np.array(primes)

# ==========================================
# 2. RPZL Runner
# ==========================================
def run_rpzl(dim, budget):
    start_time = time.time()
    
    # Generate points
    primes = get_primes(2000)
    samples = np.zeros((budget, dim))
    limit = 5.0
    
    for d in range(dim):
        p = primes[d]
        # Golden Ratio * Prime phase strategy
        phi = (np.sqrt(5) + 1) / 2
        seq = (np.arange(1, budget + 1) * p * phi) % 1.0
        samples[:, d] = seq * 2 * limit - limit
        
    costs = np.array([rosenbrock_XD(s) for s in samples])
    best_val = np.min(costs)
    duration = time.time() - start_time
    
    return best_val, duration

# ==========================================
# 3. Optuna Chase Runner
# ==========================================
def run_optuna_chase(dim, target_val, max_budget=2000):
    limit = 5.0
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    
    start_time = time.time()
    reached = False
    trials_needed = 0
    best_so_far = float('inf')
    
    # We iterate manually to check time-to-match
    for i in range(max_budget):
        trial = study.ask()
        
        x = []
        for d in range(dim):
            x.append(trial.suggest_float(f"x{d}", -limit, limit))
            
        val = rosenbrock_XD(x)
        study.tell(trial, val)
        
        if val < best_so_far:
            best_so_far = val
        
        if val <= target_val:
            reached = True
            trials_needed = i + 1
            break
            
    duration = time.time() - start_time
    
    if not reached:
        return None, duration, best_so_far
    return trials_needed, duration, target_val

# ==========================================
# 4. Execution
# ==========================================
def run_speed_test():
    DIM = 20
    BUDGET_RPZL = 1000
    
    print(f"=== SPEED BENCHMARK: 20D Rosenbrock (Structural Problem) ===")
    
    # 1. Run RPZL
    print("Running RPZL...")
    rpzl_val, rpzl_time = run_rpzl(DIM, BUDGET_RPZL)
    print(f"[RPZL] Best Value: {rpzl_val:.6f}")
    print(f"[RPZL] Time:       {rpzl_time:.6f} sec")
    
    # 2. Run Optuna Chase
    print(f"Running Optuna (Target to beat: {rpzl_val:.6f})...")
    trials, opt_time, opt_best = run_optuna_chase(DIM, rpzl_val, max_budget=3000)
    
    if trials is not None:
        print(f"[Optuna] Matched RPZL quality in {opt_time:.6f} sec ({trials} trials).")
        speedup = opt_time / rpzl_time
        print(f"🚀 Speedup Factor: RPZL was {speedup:.1f}x Faster to reach this quality.")
    else:
        print(f"[Optuna] Failed to match RPZL quality within 3000 trials.")
        print(f"[Optuna] Best found: {opt_best:.6f}")
        print(f"Conclusion: RPZL superior in limited budget.")

if __name__ == "__main__":
    run_speed_test()
