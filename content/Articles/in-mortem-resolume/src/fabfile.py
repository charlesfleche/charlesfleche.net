from fabric.api import *

p = {
    'g': '-geometry 1280',
    'wwide': '1280',
    'hwide': '640',
    'd': '..',
    'tmp': '/tmp/image.png',
    'q': '-quality 60'
}

def build():
    local('inkscape -z -e {tmp} -w {wwide} -h {hwide} banner.svg'.format(**p))
    local('convert {tmp} {q} {d}/banner.jpg'.format(**p))
    local('convert in-mortem-stage.jpg {q} {g} {d}/stage.jpg'.format(**p))
    local('convert in-mortem-resolume.png {q} {g} {d}/resolume.jpg'.format(**p))
    local('convert in-mortem-outputs.png {q} {g} {d}/outputs.jpg'.format(**p))
    local('convert in-mortem-osc-foh.png {q} {g} {d}/osc-foh.jpg'.format(**p))
    local('convert in-mortem-resolume-osc.png {q} {g} {d}/resolume-osc.jpg'.format(**p))
    local('convert in-mortem-oscwidgets.png {q} {g} {d}/oscwidgets.jpg'.format(**p))
    local('convert in-mortem-osc-stage.jpg {q} {g} {d}/osc-stage.jpg'.format(**p))
