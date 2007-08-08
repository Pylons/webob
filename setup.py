from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='WebOb',
      version=version,
      description="WSGI request and response object",
      long_description="""\
""",
      classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Paste",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],
      keywords='wsgi request web http',
      author='Ian Bicking',
      author_email='ianb@colorstudy.com',
      url='http://pythonpaste.org/webob/',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      #install_requires=[
      #],
      #entry_points="""
      #""",
      )
