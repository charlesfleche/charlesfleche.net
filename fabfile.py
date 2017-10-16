from fabric.api import *
import fabric.contrib.project as project
import os
import shutil
import sys
import socketserver

from pelican.server import ComplexHTTPRequestHandler

# Local path configuration (can be absolute or relative to fabfile)
env.deploy_path = 'output'
DEPLOY_PATH = env.deploy_path

# Remote server configuration
production = 'pi@charlesfleche.net:22'
dest_path = '/srv/www/blog'
nginx_site_path = '/etc/nginx/sites-available/blog'
icons_root = 'themes/charlesfleche/static'

# Rackspace Cloud Files configuration settings
env.cloudfiles_username = 'my_rackspace_username'
env.cloudfiles_api_key = 'my_rackspace_api_key'
env.cloudfiles_container = 'my_cloudfiles_container'

# Github Pages configuration
env.github_pages_branch = "gh-pages"

# Port for `serve`
PORT = 8000

def clean():
    """Remove generated files"""
    if os.path.isdir(DEPLOY_PATH):
        shutil.rmtree(DEPLOY_PATH)
        os.makedirs(DEPLOY_PATH)

def build():
    """Build local version of site"""
    local('pelican -s pelicanconf.py')

def build_icons():
    """Build icons"""
    local('inkscape -z -e /tmp/favicon.png -w 64 -h 64 logo.svg')
    local('cp logo.svg {}'.format(icons_root))
    local('convert /tmp/favicon.png {}/favicon.ico'.format(icons_root))
    local('inkscape -z -e {}/icon.png -w 192 -h 192 logo.svg'.format(icons_root))
    local('inkscape -z -e {}/tile.png -w 558 -h 558 logo.svg'.format(icons_root))
    local('inkscape -z -e {}/tile-wide.png -w 558 -h 270 --export-area=-5:0:15:10 logo.svg'.format(icons_root))

def rebuild():
    """`build` with the delete switch"""
    local('pelican -d -s pelicanconf.py')

def regenerate():
    """Automatically regenerate site upon file modification"""
    local('pelican -r -s pelicanconf.py')

def serve():
    """Serve site at http://localhost:8000/"""
    os.chdir(env.deploy_path)

    class AddressReuseTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    server = AddressReuseTCPServer(('', PORT), ComplexHTTPRequestHandler)

    sys.stderr.write('Serving on port {0} ...\n'.format(PORT))
    server.serve_forever()

def reserve():
    """`build`, then `serve`"""
    build()
    serve()

def preview():
    """Build production version of site"""
    local('pelican -s publishconf.py')

def cf_upload():
    """Publish to Rackspace Cloud Files"""
    rebuild()
    with lcd(DEPLOY_PATH):
        local('swift -v -A https://auth.api.rackspacecloud.com/v1.0 '
              '-U {cloudfiles_username} '
              '-K {cloudfiles_api_key} '
              'upload -c {cloudfiles_container} .'.format(**env))

@hosts(production)
def publish():
    """Publish to production via rsync"""
    local('pelican -s publishconf.py')
    project.rsync_project(
        remote_dir=dest_path,
        exclude=['.DS_Store', 'Articles', '.webassets-cache'],
        local_dir=DEPLOY_PATH.rstrip('/') + '/',
        delete=True,
        extra_opts='-c',
    )

@hosts(production)
def publish_nginx():
    put('nginx.site', nginx_site_path, use_sudo=True)

@hosts(production)
def reload_nginx():
    sudo('sudo systemctl reload nginx')

def gh_pages():
    """Publish to GitHub Pages"""
    rebuild()
    local("ghp-import -b {github_pages_branch} {deploy_path} -p".format(**env))
