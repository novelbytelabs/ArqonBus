import json

notebook_path = 'docs/ArqonBus/context/substrates/rpzl_adjoint_hybrid.ipynb'

with open(notebook_path, 'r') as f:
    nb = json.load(f)

# 1. Product Text
cell_text = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "## 13. The Product: ArqonHPO (Production Solver)\n",
        "\n",
        "**User Question**: \"So what should we do?\"\n",
        "\n",
        "**The Answer**: We built **ArqonSolver**. \n",
        "Instead of forcing you to choose strategies, we Productized the \"Hybrid\" approach as the default. \n",
        "Why? Because the penalty for using Hybrid on Chaos is small, but the penalty for NOT using it on Structure is huge (10x slowdown). The robust engineering choice is to **Always Warm-Start with Primes**.\n",
        "\n",
        "Below is the production-ready class you can drop into ArqonBus vNext."
    ]
}

# 2. Product Code
# Read the file I just wrote
with open('src/arqon_hpo.py', 'r') as src_file:
    source_code = src_file.read()

cell_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": source_code.splitlines(keepends=True)
}

nb['cells'].extend([cell_text, cell_code])

with open(notebook_path, 'w') as f:
    json.dump(nb, f, indent=1)
