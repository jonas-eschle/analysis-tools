#!/usr/bin/env bash
#   install test utilities
echo "========== Install test utilities =========="
conda install pytest coverage > tmp.txt && echo 'test utils installed'
#    run tests

echo "========== Running tests with coverage FULL =========="
coverage run -m pytest -k "not test_load_with_weights" tests/ # excluding a test in test_data.py
coverage report analysis/*/*.py
coverage xml analysis/*/*.py
echo "========== Coverage DIFF =========="
diff-cover coverage.xml | tail -n 5
