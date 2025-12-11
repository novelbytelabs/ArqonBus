import numpy as np
import time

def ackley(x, y):
    """Ackley function (global min at 0,0)"""
    return -20.0 * np.exp(-0.2 * np.sqrt(0.5 * (x**2 + y**2))) -            np.exp(0.5 * (np.cos(2 * np.pi * x) + np.cos(2 * np.pi * y))) +            np.e + 20

def get_primes(n_max):
    primes = []
    is_prime = [True] * (n_max + 1)
    for p in range(2, n_max + 1):
        if is_prime[p]:
            primes.append(p)
            for i in range(p * p, n_max + 1, p):
                is_prime[i] = False
    return np.array(primes)

def run_benchmark(n_trials=100):
    np.random.seed(42)
    
    # Domain: [-5, 5] x [-5, 5]
    limit = 5.0
    N_dim = 1000 # 1 million points total resolution
    
    # Pre-compute Full Grid (Ground Truth) for indexing logic
    # In reality we don't compute Z for all, just the indices we pick
    # But for RPZL index mapping we need the conceptual grid size N_full
    N_full = N_dim * N_dim
    
    # Sampling Budget: Small! Let's say 1,000 points (0.1%)
    # This is where "structure" matters most.
    budget = 1000
    
    print(f"Benchmark: Find Minimum of Ackley Function")
    print(f"Search Space: {N_full} points. Budget: {budget} samples ({budget/N_full:.4%} coverage).")
    print("-" * 40)

    # 1. RPZL Sampling (Deterministic)
    # Map primes to 2D coordinates
    primes = get_primes(N_full - 1)
    # Take first 'budget' primes (or primes within range that fit budget)
    # To be fair to "Sampling Strategy", we take the *first* N primes that fall in the grid
    # or primes up to some number. Let's strictly limit to 'budget'.
    rpzl_indices = primes[primes < N_full][:budget]
    
    # Map 1D index to 2D Ackley domain
    def idx_to_domain(indices, n_dim, limit):
        # row = idx // n_dim, col = idx % n_dim
        # then map [0, n_dim] to [-limit, limit]
        rows = indices // n_dim
        cols = indices % n_dim
        x = (rows / n_dim) * 2 * limit - limit
        y = (cols / n_dim) * 2 * limit - limit
        return x, y

    rx, ry = idx_to_domain(rpzl_indices, N_dim, limit)
    # Evaluate cost
    rz = ackley(rx, ry)
    rpzl_best = np.min(rz)
    print(f"RPZL Best Found: {rpzl_best:.6f}")

    # 2. Random Sampling (Stochastic - run 100 trials)
    random_bests = []
    for _ in range(n_trials):
        rand_indices = np.random.choice(N_full, size=budget, replace=False)
        ux, uy = idx_to_domain(rand_indices, N_dim, limit)
        uz = ackley(ux, uy)
        random_bests.append(np.min(uz))
    
    avg_rand_best = np.mean(random_bests)
    std_rand_best = np.std(random_bests)
    best_rand_ever = np.min(random_bests)
    
    print(f"Random Best (Avg of {n_trials} runs): {avg_rand_best:.6f} +/- {std_rand_best:.6f}")
    print(f"Random Absolute Best Record: {best_rand_ever:.6f}")
    
    # 3. Head-to-Head Stats
    wins = sum(1 for r in random_bests if r < rpzl_best)
    print("-" * 40)
    print(f"Head-to-Head Results:")
    print(f"Frequency Random beat RPZL: {wins}/{n_trials} ({wins/n_trials:.1%})")
    
    diff = avg_rand_best - rpzl_best
    if diff > 0:
        print(f"Conclusion: RPZL is {diff:.6f} units CLOSER to global min (0.0) on average.")
    else:
        print(f"Conclusion: Random is {-diff:.6f} units CLOSER to global min.")

if __name__ == "__main__":
    run_benchmark()
