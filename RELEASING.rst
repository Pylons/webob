Releasing WebOb
===============

- For clarity, we define releases as follows.

  - Alpha, beta, dev and similar statuses do not qualify whether a release is
    major or minor. The term "pre-release" means alpha, beta, or dev.

  - A release is final when it is no longer pre-release.

  - A *major* release is where the first number either before or after the
    first dot increases. Examples: 1.6.0 to 1.7.0a1, or 1.8.0 to 2.0.0.

  - A *minor* or *bug fix* release is where the number after the second dot
    increases. Example: 1.6.0 to 1.6.1.


Releasing
---------

- First install the required pre-requisites::

    $ pip install setuptools_git twine

- Edit ``CHANGES.txt`` to add a release number and data and then modify
  ``setup.py`` to update the version number as well.

- Run ``python setup.py sdist bdist_wheel``, then verify ``dist/*`` hasn't
  increased dramatically compared to previous versions (for example,
  accidentally including a large file in the release or pyc files).

- Upload the resulting package to PyPi: ``twine upload
  dist/WebOb-<version>*{whl,tar.gz}``

Marketing and communications
----------------------------

- Announce to Twitter::

    WebOb 1.x released.

    PyPI
    https://pypi.python.org/pypi/webob/1.x.y

    Changes
    http://docs.webob.org/en/1.x-branch/

    Issues
    https://github.com/Pylons/webob/issues

- Announce to maillist::

    WebOb 1.x.y has been released.

    Here are the changes:

    <<changes>>

    You can install it via PyPI:

      pip install webob==1.x.y

    Enjoy, and please report any issues you find to the issue tracker at
    https://github.com/Pylons/webob/issues

    Thanks!

    - WebOb developers
