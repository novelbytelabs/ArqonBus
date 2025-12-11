import json

notebook_path = 'docs/ArqonBus/context/substrates/rpzl_adjoint_hybrid.ipynb'

with open(notebook_path, 'r') as f:
    nb = json.load(f)

# 1. Guide Text
cell_text = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 12. Engineering Guide: Structure vs. Chaos (When to use RPZL)\n",
        "\n",
        "**User Question**: \"What is the difference between a structure problem and a chaos one and how would I know which solution to use?\"\n",
        "\n",
        "### Definitions\n",
        "1.  **Structured Problems**: The landscape has a coherent global shape, trend, or gradient (e.g., a smooth valley, a funnel). \n",
        "    -   *Examples*: Tuning Neural Network learning rates, Physics simulations, Aerodynamics, Manufacturing tolerances.\n",
        "    -   *Best Solver*: **Hybrid RPZL** (10x Faster).\n",
        "2.  **Chaotic Problems**: The landscape is extremely rugged, random, or high-frequency with no global trend. \"Neighbors\" give no clue about the value.\n",
        "    -   *Examples*: Cryptographic hashing, HFT strategies, random forests with bad seeds, Rastrigin function.\n",
        "    -   *Best Solver*: **Standard Optuna** (Robust random exploration).\n",
        "\n",
        "### The \"Litmus Test\" (Heuristic)\n",
        "How do you know which one you have? Run the **RPZL Variance Test**:\n",
        "1.  Sample 50 points using RPZL.\n",
        "2.  Calculate the variance of the differences between neighbors.\n",
        "    -   **Low Variance**: The values change smoothly. **It is Structured.** $\rightarrow$ **Use RPZL.**\n",
        "    -   **High Variance**: The values jump randomly. **It is Chaotic.** $\rightarrow$ **Use Optuna.**"
    ]
}

nb['cells'].extend([cell_text])

with open(notebook_path, 'w') as f:
    json.dump(nb, f, indent=1)
