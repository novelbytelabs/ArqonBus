import numpy as np
import optuna
import time

# ==========================================
# 1. The "Final Boss": 20D Rastrigin Function
# ==========================================
def rastrigin_XD(x):
    """
    Rastrigin function. Highly multimodal.
    Global minimum at 0,0,...,0 with value 0.
    Search domain: [-5.12, 5.12]^D
    """
    x = np.array(x)
    A = 10
    d = len(x)
    return A * d + np.sum(x**2 - A * np.cos(2 * np.pi * x))

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
# 2. Solver: HybridOptuna (The Challenger)
# ==========================================
class HybridOptuna:
    def __init__(self, dim, budget):
        self.dim = dim
        self.budget = budget
        self.limit = 5.12
        
    def optimize(self):
        # Phase 1: RPZL Warm Start (10% Budget)
        start_budget = int(self.budget * 0.1)
        optuna_budget = self.budget - start_budget
        
        primes = get_primes(2000)
        samples = np.zeros((start_budget, self.dim))
        
        for d in range(self.dim):
            p = primes[d]
            phi = (np.sqrt(5) + 1) / 2
            seq = (np.arange(1, start_budget + 1) * p * phi) % 1.0
            samples[:, d] = seq * 2 * self.limit - self.limit
            
        costs = [rastrigin_XD(s) for s in samples]
        
        # Phase 2: Optuna with Injection
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
        
        # Seed trials
        for i in range(start_budget):
            trial = optuna.trial.create_trial(
                params={f"x{d}": samples[i, d] for d in range(self.dim)}, 
                distributions={f"x{d}": optuna.distributions.FloatDistribution(-self.limit, self.limit) for d in range(self.dim)},
                value=costs[i]
            )
            study.add_trial(trial)
            
        def objective(trial):
            x = []
            for i in range(self.dim):
                x.append(trial.suggest_float(f"x{i}", -self.limit, self.limit))
            return rastrigin_XD(x)
            
        study.optimize(objective, n_trials=optuna_budget)
        return study.best_value

# ==========================================
# 3. Solver: Standard Optuna (The Champion)
# ==========================================
def run_std_optuna(dim, budget):
    limit = 5.12
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    
    def objective(trial):
        x = []
        for i in range(dim):
            x.append(trial.suggest_float(f"x{i}", -limit, limit))
        return rastrigin_XD(x)
        
    study.optimize(objective, n_trials=budget)
    return study.best_value

# ==========================================
# 4. Solver: Random (Baseline)
# ==========================================
def run_random(dim, budget):
    np.random.seed(42)
    limit = 5.12
    samples = np.random.uniform(-limit, limit, (budget, dim))
    costs = np.array([rastrigin_XD(s) for s in samples])
    return np.min(costs)

# ==========================================
# 5. Execution
# ==========================================
def run_final_boss():
    DIM = 20 # 20 Dimensions (Very Hard)
    BUDGET = 1000 # Constraints help separate efficiency
    
    print(f"=== FINAL BOSS: 20D Rastrigin (Budget: {BUDGET}) ===")
    
    # Random
    t0 = time.time()
    res_rand = run_random(DIM, BUDGET)
    t_rand = time.time() - t0
    print(f"[Random]       Best: {res_rand:.6f} (Time: {t_rand:.4f}s)")
    
    # Standard Optuna
    t0 = time.time()
    res_std = run_std_optuna(DIM, BUDGET)
    t_std = time.time() - t0
    print(f"[Std. Optuna]  Best: {res_std:.6f} (Time: {t_std:.4f}s)")
    
    # HybridOptuna
    t0 = time.time()
    solver = HybridOptuna(DIM, BUDGET)
    res_hybrid = solver.optimize()
    t_hybrid = time.time() - t0
    print(f"[HybridOptuna] Best: {res_hybrid:.6f} (Time: {t_hybrid:.4f}s)")
    
    # Verdict
    print("-" * 40)
    scores = {"HybridOptuna": res_hybrid, "Std. Optuna": res_std, "Random": res_rand}
    winner = min(scores, key=scores.get)
    print(f"🏆 CHAMPION: {winner} (Score: {scores[winner]:.6f})")
    
    if winner == "HybridOptuna":
        margin = res_std - res_hybrid
        print(f"Conclusion: HybridOptuna validated! It beat standard Optuna by {margin:.6f} points.")
        print(f"Efficiency Gain: {(margin / res_std)*100:.1f}% improvement.")
    else:
        print("Conclusion: Standard Optuna retains the title.")

if __name__ == "__main__":
    run_final_boss()
