import sys, subprocess

def create_suite():
    from mext.test_suite import TestSuite
    suite = TestSuite('tests', coverage='html_coverage', pkg='webob')

    for test in ['do-it-yourself', 'file-example', 'index', 'reference']:
        suite.add_doctest('../docs/' + test)
    map(suite.add_doctest, ['test_dec', 'test_request', 'test_response', 'multidict'])

    for test in ['test_request', 'test_response']:
        suite.add_nosetest(test)
    return suite

if __name__ == '__main__':
    try:
        suite = create_suite()
        #suite.run_text(verbose=True)
        suite.run_text()
    except ImportError:
        if 'inner' in sys.argv:
            raise
        subprocess.check_call(
            "pip install -q -E testenv nose dtopt meld3 paste pyprof2calltree "
                "repoze.profile tempita webtest wsgiproxy mext.test>=0.4 coverage"
        )
        #@@ make non-win-specific
        subprocess.check_call(
            "testenv\Scripts\python.exe %s inner" % __file__,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
else:
    suite = create_suite()
