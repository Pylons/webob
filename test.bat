@echo off
pip install -q -E testenv nose dtopt meld3 paste pyprof2calltree repoze.profile tempita webtest wsgiproxy
testenv\Scripts\python setup.py test
testenv\Scripts\nosetests