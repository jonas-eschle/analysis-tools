Analysis tools
==============

This repository provides basic tools for doing physics analysis, with emphasis on specialization for each particular analysis.

To install this folder, first install a github dependency

```bash
pip install git+https://github.com/ibab/root_pandas.git
```

then, do

```bash
pip install -e .
```

To install the pre-commit hook that runs `pytest`, please do

```bash
ln -s ../../hooks/pre-commit.sh .git/hooks/pre-commit
```
