from fabric.api import *

p = {
    'g': '-geometry 1280',
    'wwide': '1280',
    'hwide': '640',
    'd': '..',
    'tmp': '/tmp/image.png',
    'q': '-quality 60',
    'o': '-strip -interlace plane'
}

def build():
    local('inkscape -z -e {tmp} -w {wwide} -h {hwide} banner.svg'.format(**p))
    local('convert {o} {tmp} {q} {d}/banner.jpg'.format(**p))
    local('convert in-mortem-stage.jpg {o} {q} {g} {d}/stage.jpg'.format(**p))
    local('convert in-mortem-resolume.png {o} {q} {g} {d}/resolume.jpg'.format(**p))
    local('convert in-mortem-outputs.png {o} {q} {g} {d}/outputs.jpg'.format(**p))
    local('convert in-mortem-osc-foh.png {o} {q} {g} {d}/osc-foh.jpg'.format(**p))
    local('convert in-mortem-resolume-osc.png {o} {q} {g} {d}/resolume-osc.jpg'.format(**p))
    local('convert in-mortem-oscwidgets.png {o} {q} {g} {d}/oscwidgets.jpg'.format(**p))
    local('convert in-mortem-osc-stage.jpg {o} {q} {g} {d}/osc-stage.jpg'.format(**p))
