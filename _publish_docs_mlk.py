import sys, site, os, tempfile, shutil, subprocess
from os.path import *

docsenv_dir = join(tempfile.gettempdir(), 'webob-docs')
docs_src = join(dirname(abspath(__file__)), 'docs')
docs_target = join(docsenv_dir, 'docs')

if not exists(docsenv_dir):
    os.makedirs(docsenv_dir)
    from setuptools.command.easy_install import main
    site.USER_SITE = docsenv_dir
    libs = 'sphinx docutils jinja2'.split()
    main(['-x', '-N', '-d', docsenv_dir] + libs)

site.addsitedir(docsenv_dir)

if exists(docs_target):
    shutil.rmtree(docs_target)

from sphinx.cmdline import main
main(['-E', docs_src, docs_target])

if 'up' in sys.argv:
    subprocess.check_call([
        'c:/program files/putty/pscp', '-r', join(docs_target, '*'),
        'maluke@webwareforpython.org:/home/paste/htdocs/webob/'
    ])
