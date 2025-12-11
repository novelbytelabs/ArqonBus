import numpy as np
import optuna
import time

def ackley_XD(x):
    x = np.array(x)
    d = len(x)
    sum_sq = np.sum(x**2)
    sum_cos = np.sum(np.cos(2 * np.pi * x))
    term1 = -20 * np.exp(-0.2 * np.sqrt(sum_sq / d))
    term2 = -np.exp(sum_cos / d)
    return term1 + term2 + 20 + np.e

def get_primes(n_max):
    primes = []
    is_prime = [True] * (n_max + 1)
    for p in range(2, n_max + 1):
        if is_prime[p]:
            primes.append(p)
            for i in range(p * p, n_max + 1, p):
                is_prime[i] = False
    return np.array(primes)

# --- HYBRID SOLVER ---
def run_hybrid(dim, budget):
    # Strategy: 
    # 1. Warm Start with RPZL (10% of budget = 50 samples)
    # 2. Finish with Optuna (90% of budget = 450 samples)
    
    start_budget = int(budget * 0.1) # 50
    optuna_budget = budget - start_budget # 450
    
    # 1. RPZL Sweep
    primes = get_primes(1000)
    samples = np.zeros((start_budget, dim))
    limit = 5.0
    
    for d in range(dim):
        p = primes[d]
        phi = (np.sqrt(5) + 1) / 2
        seq = (np.arange(1, start_budget + 1) * p * phi) % 1.0
        samples[:, d] = seq * 2 * limit - limit
        
    # Evaluate RPZL points
    costs = [ackley_XD(s) for s in samples]
    
    # 2. Optuna with Warm Start
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    
    # Inject RPZL knowledge into Optuna
    for i in range(start_budget):
        trial = optuna.trial.create_trial(
            params={f"x{d}": samples[i, d] for d in range(dim)}, 
            distributions={f"x{d}": optuna.distributions.FloatDistribution(-5.0, 5.0) for d in range(dim)},
            value=costs[i]
        )
        study.add_trial(trial)
        
    # Run remaining budget
    def objective(trial):
        x = []
        for i in range(dim):
            x.append(trial.suggest_float(f"x{i}", -5.0, 5.0))
        return ackley_XD(x)
        
    study.optimize(objective, n_trials=optuna_budget)
    return study.best_value

# --- PURE OPTUNA (Control) ---
def run_pure_optuna(dim, budget):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    
    def objective(trial):
        x = []
        for i in range(dim):
            x.append(trial.suggest_float(f"x{i}", -5.0, 5.0))
        return ackley_XD(x)
        
    study.optimize(objective, n_trials=budget)
    return study.best_value

def run_benchmark():
    DIM = 10
    BUDGET = 500
    
    print(f"=== HYBRID CHALLENGE: 10D Ackley (Budget: {BUDGET}) ===")
    
    t0 = time.time()
    score_optuna = run_pure_optuna(DIM, BUDGET)
    t_opt = time.time() - t0
    print(f"[Pure Optuna] Best: {score_optuna:.6f} (Time: {t_opt:.4f}s)")
    
    t0 = time.time()
    score_hybrid = run_hybrid(DIM, BUDGET)
    t_hybrid = time.time() - t0
    print(f"[Hybrid RPZL] Best: {score_hybrid:.6f} (Time: {t_hybrid:.4f}s)")
    
    if score_hybrid < score_optuna:
        print(f"🏆 WINNER: Hybrid Approach! Improvement: {score_optuna - score_hybrid:.6f}")
    else:
        print(f"Winner: Pure Optuna. Hybrid overhead didn't help.")

if __name__ == "__main__":
    run_benchmark()
