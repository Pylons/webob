Contributing
============

All projects under the Pylons Projects, including this one, follow the
guidelines established at [How to
Contribute](http://www.pylonsproject.org/community/how-to-contribute) and
[Coding Style and
Standards](http://docs.pylonsproject.org/en/latest/community/codestyle.html).

You can contribute to this project in several ways.

* [File an Issue on GitHub](https://github.com/Pylons/webob/issues)
* Fork this project and create a branch with your suggested change. When ready,
  submit a pull request for consideration. [GitHub
  Flow](https://guides.github.com/introduction/flow/index.html) describes the
  workflow process and why it's a good practice.
* Join the IRC channel #pyramid on irc.freenode.net.


Git Branches
------------
Git branches and their purpose and status at the time of this writing are
listed below.

* [main](https://github.com/Pylons/webob/) - The branch on which further
development takes place. The default branch on GitHub.
* [1.6-branch](https://github.com/Pylons/webob/tree/1.6-branch) - The branch
classified as "stable" or "latest". Actively maintained. 
* [1.5-branch](https://github.com/Pylons/webob/tree/1.5-branch) - The oldest
actively maintained and stable branch.

Older branches are not actively maintained. In general, two stable branches and
one or two development branches are actively maintained.


Running Tests
-------------

Run `tox` from within your checkout. This will run the tests across all
supported systems and attempt to build the docs.

For example, to run the test suite with your current Python runtime:

    tox -e py

If you wish to run multiple targets, you can do so by separating them with a
comma:

    tox -e py312,coverage

If you've already run the coverage target and want to see the results in HTML,
you can override `tox.ini` settings with the `commands` option:

    tox -e coverage -x testenv:coverage.commands="coverage html"

To build the docs:

    tox -e docs

List all possible targets:

    tox list # or `tox l`

See `tox.ini` file for details, or <https://tox.wiki/> for general `tox` usage.


Building documentation for a Pylons Project project
---------------------------------------------------

*Note:* These instructions might not work for Windows users. Suggestions to
improve the process for Windows users are welcome by submitting an issue or a
pull request.

1.  Fork the repo on GitHub by clicking the [Fork] button.
2.  Clone your fork into a workspace on your local machine.

         git clone git@github.com:<username>/webob.git

3.  Add a git remote "upstream" for the cloned fork.

         git remote add upstream git@github.com:Pylons/webob.git

4.  Set an environment variable to your virtual environment.

         # Mac and Linux
         $ export VENV=~/hack-on-webob/env

         # Windows
         set VENV=c:\hack-on-webob\env

5.  Try to build the docs in your workspace.

         # Mac and Linux
         $ make clean html SPHINXBUILD=$VENV/bin/sphinx-build

         # Windows
         c:\> make clean html SPHINXBUILD=%VENV%\bin\sphinx-build

     If successful, then you can make changes to the documentation. You can
     load the built documentation in the `/_build/html/` directory in a web
     browser.

6.  From this point forward, follow the typical [git
    workflow](https://help.github.com/articles/what-is-a-good-git-workflow/).
    Start by pulling from the upstream to get the most current changes.

         git pull upstream main

7.  Make a branch, make changes to the docs, and rebuild them as indicated in
    step 5.  To speed up the build process, you can omit `clean` from the above
    command to rebuild only those pages that depend on the files you have
    changed.

8.  Once you are satisfied with your changes and the documentation builds
    successfully without errors or warnings, then git commit and push them to
    your "origin" repository on GitHub.

         git commit -m "commit message"
         git push -u origin --all # first time only, subsequent can be just 'git push'.

9.  Create a [pull request](https://help.github.com/articles/using-pull-requests/).

10.  Repeat the process starting from Step 6.