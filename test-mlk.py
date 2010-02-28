from mext.test_suite import *

suite = TestSuite('tests', coverage='html_coverage', pkg='webob')

for test in ['do-it-yourself', 'file-example', 'index', 'reference']:
    suite.add_doctest('../docs/' + test)

map(suite.add_doctest, ['test_dec', 'test_request', 'test_response', 'multidict'])


try:
    for test in ['test_request', 'test_response']:
        suite.add_unittest(test, nose=True)
except ImportError:
    if __name__ != '__main__':
        raise
    import subprocess, sys
    subprocess.check_call("pip install -q -E testenv nose dtopt meld3 paste pyprof2calltree repoze.profile tempita webtest wsgiproxy mext.test coverage")
    subprocess.check_call("testenv\Scripts\python.exe %s" % __file__, stdout=sys.stdout, stderr=sys.stdout) #@@ make non-win-specific
    sys.exit()


if __name__ == '__main__':
    #suite.run_text(verbose=True)
    suite.run_text()
