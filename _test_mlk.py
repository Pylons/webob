import sys, subprocess, site, os

def create_suite():
    from mext.test_suite import TestSuite
    suite = TestSuite('tests', coverage='html_coverage', pkg='webob')

    for test in ['do-it-yourself', 'file-example', 'index', 'reference']:
        suite.add_doctest('../docs/' + test)
    map(suite.add_doctest, ['test_dec', 'test_request', 'test_response', 'multidict'])

    for test in ['test_request', 'test_response']:
        suite.add_nosetest(test)
    return suite


try:
    suite = create_suite()
except ImportError:
    if not os.path.exists('testenv'):
        subprocess.check_call("pip install -q -E testenv nose dtopt webtest mext.test>=0.4 coverage")
    site.addsitedir('testenv/Lib/site-packages')
    suite = create_suite()

if __name__ == '__main__':
    suite.run_text()
