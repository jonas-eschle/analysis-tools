#!/usr/bin/env bash
#   install test utilities
echo "============================ Install test utilities ============================"
conda install pytest coverage > tmp.txt && echo 'test utils installed'
pip install diff_cover > tmp.txt && echo 'diff code checker installed'

#    run tests
echo "======================= Running tests with coverage FULL ======================="
# excluding a test in test_data.py
coverage run -m pytest -k "not (test_load_with_weights or test_sumfactory_ratio_load)" tests/ && \
coverage report analysis/*/*.py && \
coverage xml analysis/*/*.py && \
echo "================================ Coverage DIFF =================================" && \
diff-cover coverage.xml | tail -n 5 && \
echo "=============================== Finished tests ================================="
