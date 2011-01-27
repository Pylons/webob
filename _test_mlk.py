import sys, site, os, tempfile

testenv_dir = os.path.join(tempfile.gettempdir(), 'webob-testenv')
if not os.path.exists(testenv_dir):
    os.makedirs(testenv_dir)
    from setuptools.command.easy_install import main
    site.USER_SITE = testenv_dir
    libs = 'nose dtopt webtest mext.test>=0.4.2 coverage'.split()
    main(['-x', '-N', '-d', testenv_dir] + libs)

site.addsitedir(testenv_dir)

from mext.test_suite import TestSuite
suite = TestSuite('tests', coverage=True, pkg='webob')

doctests = ['test_dec', 'test_request', 'test_response', 'html_escape', 'multidict']
doctests += map('../docs/'.__add__, ['do-it-yourself', 'file-example', 'index', 'reference'])
map(suite.add_doctest, doctests)
map(suite.add_nosetest, ['test_request', 'test_response', 'test_multidict'])


if __name__ == '__main__':
    suite.run_text()
