import sys, site, os
from os.path import *

def create_suite():
    from mext.test_suite import TestSuite
    suite = TestSuite('tests', coverage=True, pkg='webob')

    for test in ['do-it-yourself', 'file-example', 'index', 'reference']:
        suite.add_doctest('../docs/' + test)
    map(suite.add_doctest, ['test_dec', 'test_request', 'test_response', 'html_escape', 'multidict'])

    for test in ['test_request', 'test_response', 'test_multidict']:
        suite.add_nosetest(test)
    return suite

testenv_dir = join(os.environ['TEMP'], 'webob-testenv')
if not exists(testenv_dir):
    os.makedirs(testenv_dir)
    from setuptools.command.easy_install import main
    site.USER_SITE = testenv_dir
    libs = 'nose dtopt webtest mext.test>=0.4.2 coverage'.split()
    main(['-x', '-N', '-d', testenv_dir] + libs)

site.addsitedir(testenv_dir)
suite = create_suite()

if __name__ == '__main__':
    suite.run_text()
