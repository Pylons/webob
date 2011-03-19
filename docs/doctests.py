import unittest
import doctest

def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite('test_request.txt'),
        doctest.DocFileSuite('test_response.txt'),
        doctest.DocFileSuite('test_dec.txt'),
        doctest.DocFileSuite('do-it-yourself.txt'),
        doctest.DocFileSuite('file-example.txt'),
        doctest.DocFileSuite('index.txt'),
        doctest.DocFileSuite('reference.txt'),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
