import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(here, "README.rst")) as f:
        README = f.read()
    with open(os.path.join(here, "CHANGES.txt")) as f:
        CHANGES = f.read()
except IOError:
    README = CHANGES = ""

testing_extras = [
    "pytest >= 3.1.0",  # >= 3.1.0 so we can use pytest.param
    "coverage",
    "pytest-cov",
    "pytest-xdist",
]

docs_extras = [
    "Sphinx >= 1.7.5",
    "pylons-sphinx-themes",
    "setuptools",
]

setup(
    name="WebOb",
    version="2.0.0dev0",
    description="WSGI request and response object",
    long_description=README + "\n\n" + CHANGES,
    classifiers=[
        "Development Status :: 6 - Mature",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords="wsgi request web http",
    author="Ian Bicking",
    author_email="ianb@colorstudy.com",
    maintainer="Pylons Project",
    url="http://webob.org/",
    license="MIT",
    packages=find_packages("src", exclude=["tests"]),
    package_dir={"": "src"},
    python_requires=">=3.9.0",
    install_requires=[
        "multipart~=1.1",
    ],
    zip_safe=True,
    extras_require={"testing": testing_extras, "docs": docs_extras},
)
