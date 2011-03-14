from setuptools import setup
import sys, os

version = '1.0.5'

setup(
    name='WebOb',
    version=version,
    description="WSGI request and response object",
    long_description="""\
WebOb provides wrappers around the WSGI request environment, and an
object to help create WSGI responses.

The objects map much of the specified behavior of HTTP, including
header parsing and accessors for other standard parts of the
environment.

You may install the `in-development version of WebOb
<http://bitbucket.org/ianb/webob/get/tip.gz#egg=WebOb-dev>`_ with
``pip install WebOb==dev`` (or ``easy_install WebOb==dev``).

See also: `changelog <http://pythonpaste.org/webob/news>`_,
`mailing list <http://bit.ly/paste-users>`_,
`bug tracker <https://bitbucket.org/ianb/webob/issues>`_.
""",
    classifiers=[
        "Development Status :: 6 - Mature",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Programming Language :: Python :: 2.4",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    keywords='wsgi request web http',
    author='Ian Bicking',
    author_email='ianb@colorstudy.com',
    maintainer='Sergey Schetinin',
    maintainer_email='sergey@maluke.com',
    url='http://pythonpaste.org/webob/',
    license='MIT',
    packages=['webob'],
    zip_safe=True,
    test_suite='nose.collector',
    tests_require=['Tempita', 'WSGIProxy', 'WebTest', 'dtopt', 'nose',
                   'coverage', 'repoze.profile'],
)
