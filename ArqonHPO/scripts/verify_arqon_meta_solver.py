import numpy as np
import sys
import os
sys.path.append(os.path.abspath("src"))
from arqon_hpo import ArqonSolver

# 1. Rosenbrock (Structure)
def rosenbrock_20d(x):
    x = np.array(x)
    return np.sum(100.0 * (x[1:] - x[:-1]**2.0)**2.0 + (1 - x[:-1])**2.0)

# 2. Rastrigin (Chaos)
def rastrigin_20d(x):
    x = np.array(x)
    A = 10
    d = len(x)
    return A * d + np.sum(x**2 - A * np.cos(2 * np.pi * x))

def run_verification():
    bounds = [(-5.0, 5.0)] * 20
    budget = 200 # Small budget for fast check
    
    print("=== TEST 1: Rosenbrock (Should detect STRUCTURE) ===")
    solver1 = ArqonSolver(rosenbrock_20d, bounds, budget=budget)
    best1 = solver1.optimize()
    print(f"Result: {best1:.4f}\n")
    
    print("=== TEST 2: Rastrigin (Should detect CHAOS) ===")
    solver2 = ArqonSolver(rastrigin_20d, bounds, budget=budget)
    best2 = solver2.optimize()
    print(f"Result: {best2:.4f}\n")

if __name__ == "__main__":
    run_verification()
