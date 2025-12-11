import json
path = 'ArqonHPO/docs/rpzl_adjoint_hybrid.ipynb'
with open(path, 'r') as f: nb = json.load(f)
nb['cells'].append({
 "cell_type": "markdown",
 "metadata": {},
 "source": ["## Engineering Guide: Litmus Test\n", "Run 50 samples.\nLow variance = Structure -> Use RPZL.\nHigh Variance = Chaos -> Use Optuna."]
})
with open(path, 'w') as f: json.dump(nb, f)
