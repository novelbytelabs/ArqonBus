import numpy as np
import optuna
import logging

logging.basicConfig(level=logging.INFO, format='[ArqonHPO] %(message)s')
logger = logging.getLogger("ArqonHPO")

class ArqonSolver:
    """
    The 'Always-Hybrid' Meta-Solver for ArqonBus vNext.
    Strategy: Always use RPZL (Prime-Indexed) Sampling to warm-start Optuna.
    """
    def __init__(self, objective_func, bounds, budget=1000, probe_ratio=0.10):
        self.objective = objective_func
        self.bounds = np.array(bounds)
        self.dim = len(bounds)
        self.budget = budget
        self.probe_budget = max(int(budget * probe_ratio), 10)
        self._primes = self._get_primes(2000)
        
    def _get_primes(self, n_max):
        primes = []
        is_prime = [True] * (n_max + 1)
        for p in range(2, n_max + 1):
            if is_prime[p]:
                primes.append(p)
                for i in range(p * p, n_max + 1, p):
                    is_prime[i] = False
        return np.array(primes)
        
    def _rpzl_sample(self, n_samples):
        samples = np.zeros((n_samples, self.dim))
        for d in range(self.dim):
            p = self._primes[d % len(self._primes)]
            phi = (np.sqrt(5) + 1) / 2
            seq = (np.arange(1, n_samples + 1) * p * phi) % 1.0
            low, high = self.bounds[d]
            samples[:, d] = seq * (high - low) + low
        return samples

    def optimize(self):
        logger.info(f"ArqonHPO: Initializing Hybrid Solver (Dim={self.dim}, Budget={self.budget})...")
        logger.info(f"Phase 1: RPZL Global Scan ({self.probe_budget} samples)...")
        probe_samples = self._rpzl_sample(self.probe_budget)
        probe_costs = np.array([self.objective(s) for s in probe_samples])
        
        best_probe_idx = np.argmin(probe_costs)
        best_probe_val = probe_costs[best_probe_idx]
        logger.info(f"   -> Best Probe Result: {best_probe_val:.6f}")

        logger.info(f"Phase 2: Seeding Bayesian Model...")
        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        
        for i in range(self.probe_budget):
            trial = optuna.trial.create_trial(
                params={f"x{d}": probe_samples[i, d] for d in range(self.dim)}, 
                distributions={f"x{d}": optuna.distributions.FloatDistribution(self.bounds[d][0], self.bounds[d][1]) for d in range(self.dim)},
                value=probe_costs[i]
            )
            study.add_trial(trial)
            
        remaining_budget = self.budget - self.probe_budget
        logger.info(f"Phase 3: Bayesian Refinement ({remaining_budget} trials)...")
        
        def objective_wrapper(trial):
            x = []
            for d in range(self.dim):
                low, high = self.bounds[d]
                x.append(trial.suggest_float(f"x{d}", low, high))
            return self.objective(x)
            
        study.optimize(objective_wrapper, n_trials=remaining_budget)
        
        if best_probe_val < study.best_value:
             return best_probe_val
        return study.best_value
