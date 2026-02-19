from setuptools import setup, find_packages
setup(
    name='arqon_hpo',
    version='1.0.0',
    description='Adaptive Hyperparameter Optimization with Prime-Indexed Warm Start',
    author='ArqonBus Team',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=['numpy', 'optuna', 'scipy'],
)
