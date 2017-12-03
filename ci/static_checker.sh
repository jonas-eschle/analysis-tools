echo "========== Install static checker =========="
conda install pylint pycodestyle > tmp.txt && echo 'static code checker installed'
pip install diff_cover > tmp.txt && echo 'diff code checker installed'

echo "========== Pylint check (force pass) =========="
pylint --rcfile=ci/pylintrc analysis > pylint_report.txt && (exit 0)
tail -n 3
diff-quality --violations=pylint --fail-under=95 pylint_report.txt --options="--rcfile=ci/pylintrc"

echo "========== Codestyle check (force pass) =========="
pycodestyle --max-line-length=1000 analysis > report_pycodestyle.txt || (exit 0)
pycodestyle --statistics -qq --max-line-length=100 analysis || (exit 0)
diff-quality --violations=pycodestyle --fail-under=95 report_pycodestyle.txt  --options="--max-line-length=100"
