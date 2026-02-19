import numpy as np

def get_primes(n: int):
    """Sieve of Eratosthenes to get primes up to n."""
    sieve = np.ones(n + 1, dtype=bool)
    sieve[0:2] = False
    for i in range(2, int(n**0.5) + 1):
        if sieve[i]:
            sieve[i*i::i] = False
    return np.nonzero(sieve)[0]

class TwistField:
    """
    Prototype implementation of the Twist Field from 'prime_twist_models.md'.
    Math: twist_{i,k} = cos(r_i * ln(p_k)) / p_k^s
    """
    def __init__(self, n_primes=50, s=0.5):
        self.primes = get_primes(1000)[:n_primes]
        self.s = s
        
    def compute_twist(self, vector: np.ndarray) -> np.ndarray:
        """
        Embeds a vector (e.g., hyperparameters) into the Prime-Twist Field.
        
        Args:
            vector: Input parameter vector (1D array)
            
        Returns:
            Mean Resonance Score (Scalar). 
            High (>0.8) = Structure/Resonance.
            Low (<0.3) = Chaos/Destructive Interference.
        """
        # 1. Expand vector elements r_i against primes p_k
        # Shape: (len(vector), len(primes))
        r_i = vector[:, np.newaxis]
        p_k = self.primes[np.newaxis, :]
        
        # 2. Twist Formula: cos(r * ln(p)) / p^s
        log_p = np.log(p_k)
        twist_matrix = np.cos(r_i * log_p) / (p_k ** self.s)
        
        # 3. Compute Resonance (Mean Similarity / Magnitude)
        # In the doc, this is "mean cosine similarity between twist vectors".
        # For HPO pruning, we can use the mean magnitude of the twist field.
        resonance = np.mean(np.abs(twist_matrix))
        
        return resonance

# Example Usage for the AI
if __name__ == "__main__":
    tf = TwistField(n_primes=20, s=0.5)
    
    # 1. Structured Input (Harmonic)
    v_struct = np.array([1.0, 2.0, 3.0, 4.0]) 
    score_struct = tf.compute_twist(v_struct)
    print(f"Structured Score: {score_struct:.4f}")
    
    # 2. Random Input (Chaotic)
    v_chaos = np.random.rand(4) * 10
    score_chaos = tf.compute_twist(v_chaos)
    print(f"Chaotic Score:    {score_chaos:.4f}")
