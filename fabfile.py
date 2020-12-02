from fabric.api import *
import fabric.contrib.project as project
import http.server
import os
import shutil
import sys
import socketserver

# Local path configuration (can be absolute or relative to fabfile)
env.deploy_path = 'output'
DEPLOY_PATH = env.deploy_path

# Remote server configuration
production = 'root@charlesfleche.net'
dest_path = '/var/www/charlesfleche.net'
nginx_site_path = '/etc/nginx/sites-available/charlesfleche.net'
icons_root = 'themes/charlesfleche/static'
css_root = 'themes/charlesfleche/static/css'

# Rackspace Cloud Files configuration settings
env.cloudfiles_username = 'my_rackspace_username'
env.cloudfiles_api_key = 'my_rackspace_api_key'
env.cloudfiles_container = 'my_cloudfiles_container'

# Github Pages configuration
env.github_pages_branch = "gh-pages"

# Port for `serve`
PORT = 8000

def goaccess():
    """Create goaccess realtime web report"""
    local('''ssh pi@charlesfleche.net 'tail -n +1 -f /var/log/nginx/blog.access.log' | goaccess -o /tmp/report.html --log-format=COMBINED --real-time-html --geoip-database GeoLite2-Country.mmdb -a -'''.format(production))

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

def copy_fonts():
    '''Copy icomoon fonts to theme folder'''
    local('cp icomoon/style.css {}/fonts.css'.format(css_root))
    local('cp -r icomoon/fonts {}'.format(css_root))

def rebuild():
    """`build` with the delete switch"""
    local('pelican -d -s pelicanconf.py')

def regenerate():
    """Automatically regenerate site upon file modification"""
    local('pelican -r -s pelicanconf.py')

def serve():
    """Serve site at http://localhost:8000/"""
    os.chdir(env.deploy_path)

    with http.server.HTTPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        print("Serving at port", PORT)
        httpd.serve_forever()

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
