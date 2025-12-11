import numpy as np
from scipy.interpolate import griddata
import time
import json

def generate_2d_signal(N):
    x = np.linspace(0, 1, N)
    y = np.linspace(0, 1, N)
    X, Y = np.meshgrid(x, y)
    # A complex, multi-scale 2D function (e.g. Ackley-like or modulated sine)
    Z = np.sin(2 * np.pi * 3 * X) * np.cos(2 * np.pi * 5 * Y) +         0.5 * np.sin(2 * np.pi * 10 * X + Y) +         0.2 * np.random.normal(0, 0.05, size=X.shape)
    return X, Y, Z

def get_primes(n_max):
    primes = []
    is_prime = [True] * (n_max + 1)
    for p in range(2, n_max + 1):
        if is_prime[p]:
            primes.append(p)
            for i in range(p * p, n_max + 1, p):
                is_prime[i] = False
    return np.array(primes)

def run_experiment():
    np.random.seed(42)
    N_dim = 100
    N_full = N_dim * N_dim
    X, Y, Z = generate_2d_signal(N_dim)
    
    # Flatten for indexing
    Z_flat = Z.ravel()
    coords = np.column_stack((X.ravel(), Y.ravel()))
    
    # 1. RPZL Sampling (Prime Indices on Flattened Raster)
    primes = get_primes(N_full - 1)
    indices_rpzl = primes[primes < N_full]
    sample_size = len(indices_rpzl)
    
    # 2. Uniform Random Sampling (Same size)
    indices_uni = np.random.choice(N_full, size=sample_size, replace=False)
    
    # Interpolation Reconstruction (using griddata cubic)
    # This simulates "learning" the surface from the samples
    
    # RPZL Reconstruction
    t0 = time.time()
    try:
        Z_pred_rpzl = griddata(coords[indices_rpzl], Z_flat[indices_rpzl], coords, method='cubic', fill_value=0)
        mse_rpzl = np.mean((Z_flat - Z_pred_rpzl)**2)
    except Exception as e:
        mse_rpzl = 999.0 # Fail
    
    # Uniform Reconstruction
    try:
        Z_pred_uni = griddata(coords[indices_uni], Z_flat[indices_uni], coords, method='cubic', fill_value=0)
        mse_uni = np.mean((Z_flat - Z_pred_uni)**2)
    except Exception as e:
        mse_uni = 999.0
    
    # Spectral Analysis (Relational Matrix Construction on subset to save time)
    # Taking a smaller subset of the samples for spectral analysis to permit SVD
    subset_size = min(500, sample_size)
    
    # RPZL Sub-sample for spectrum
    idx_rpzl_sub = indices_rpzl[:subset_size]
    # Simple Gaussian Kernel
    dist_sq_rpzl = np.sum((coords[idx_rpzl_sub][:, None, :] - coords[idx_rpzl_sub][None, :, :])**2, axis=2)
    val_sq_rpzl = (Z_flat[idx_rpzl_sub][:, None] - Z_flat[idx_rpzl_sub][None, :])**2
    R_rpzl = np.exp(-10.0 * dist_sq_rpzl) * np.exp(-1.0 * val_sq_rpzl)
    
    try:
        vals_rpzl = np.linalg.eigvalsh(R_rpzl)
        # Spectral gap: difference between top 2 eigenvalues
        gap_rpzl = vals_rpzl[-1] - vals_rpzl[-2]
    except:
        gap_rpzl = 0.0
    
    # Uni Sub-sample for spectrum
    idx_uni_sub = indices_uni[:subset_size]
    dist_sq_uni = np.sum((coords[idx_uni_sub][:, None, :] - coords[idx_uni_sub][None, :, :])**2, axis=2)
    val_sq_uni = (Z_flat[idx_uni_sub][:, None] - Z_flat[idx_uni_sub][None, :])**2
    R_uni = np.exp(-10.0 * dist_sq_uni) * np.exp(-1.0 * val_sq_uni)
    
    try:
        vals_uni = np.linalg.eigvalsh(R_uni)
        gap_uni = vals_uni[-1] - vals_uni[-2]
    except:
        gap_uni = 0.0
    
    print(f"RESULTS_JSON={{\"sample_size\": {sample_size}, \"compression\": {sample_size/N_full:.4f}, \"mse_rpzl\": {mse_rpzl:.6f}, \"mse_uni\": {mse_uni:.6f}, \"gap_rpzl\": {gap_rpzl:.6f}, \"gap_uni\": {gap_uni:.6f}}}")

if __name__ == "__main__":
    run_experiment()
