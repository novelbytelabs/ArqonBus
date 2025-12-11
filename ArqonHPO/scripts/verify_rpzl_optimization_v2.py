import numpy as np
import time

def ackley(x, y):
    return -20.0 * np.exp(-0.2 * np.sqrt(0.5 * (x**2 + y**2))) -            np.exp(0.5 * (np.cos(2 * np.pi * x) + np.cos(2 * np.pi * y))) +            np.e + 20

def get_primes(n_max):
    # Sieve of Eratosthenes
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
    limit = 5.0
    N_dim = 1000 
    N_full = N_dim * N_dim
    budget = 1000
    
    print(f"Benchmark V2: Find Minimum of Ackley Function (Corrected Coverage)")
    print(f"Search Space: {N_full} points. Budget: {budget} samples.")

    # 1. RPZL Sampling (Strided Primes to cover full domain)
    # Generate ALL primes in domain
    t0 = time.time()
    all_primes = get_primes(N_full - 1)
    # Stride to fit budget
    if len(all_primes) > budget:
        step = len(all_primes) // budget
        rpzl_indices = all_primes[::step][:budget]
    else:
        rpzl_indices = all_primes
    
    # Map 1D index to 2D Raster Ackley domain
    def idx_to_domain(indices, n_dim, limit):
        rows = indices // n_dim
        cols = indices % n_dim
        x = (rows / n_dim) * 2 * limit - limit
        y = (cols / n_dim) * 2 * limit - limit
        return x, y

    rx, ry = idx_to_domain(rpzl_indices, N_dim, limit)
    rz = ackley(rx, ry)
    rpzl_best = np.min(rz)
    
    print(f"RPZL Best Found: {rpzl_best:.6f} (Indices range: {np.min(rpzl_indices)}-{np.max(rpzl_indices)})")

    # 2. Random Sampling 
    random_bests = []
    for _ in range(n_trials):
        rand_indices = np.random.choice(N_full, size=budget, replace=False)
        ux, uy = idx_to_domain(rand_indices, N_dim, limit)
        uz = ackley(ux, uy)
        random_bests.append(np.min(uz))
    
    avg_rand_best = np.mean(random_bests)
    best_rand_ever = np.min(random_bests)
    
    # 3. Head-to-Head Stats
    wins = sum(1 for r in random_bests if r >= rpzl_best) # Count times Random was WORSE or EQUAL (RPZL Win/Draw)
    # Actually let's count strict wins for Random
    rand_wins = sum(1 for r in random_bests if r < rpzl_best)
    
    print(f"Random Best (Avg): {avg_rand_best:.6f}")
    print(f"Head-to-Head Results:")
    print(f"Random Win Rate: {rand_wins}/{n_trials} ({rand_wins/n_trials:.1%})")
    print(f"RPZL Win Rate: {100 - rand_wins}/{n_trials} ({(100-rand_wins)/n_trials:.1%})")
    
    if rpzl_best < avg_rand_best:
        print(f"Conclusion: RPZL OUTPERFORMS Random on average by {avg_rand_best - rpzl_best:.6f} units.")
    else:
        print(f"Conclusion: Random OUTPERFORMS RPZL on average by {rpzl_best - avg_rand_best:.6f} units.")

if __name__ == "__main__":
    run_benchmark()
