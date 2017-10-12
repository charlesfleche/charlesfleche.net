#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals
import os

PLUGIN_PATHS = ['../pelican-plugins']
PLUGINS = ['assets']

AUTHOR = 'Charles Flèche'
SITENAME = 'Charles Flèche'
SITEURL = ''

THEME = 'charlesfleche'
THEME_STATIC_DIR = '.'

LINKEDIN_USERNAME = 'charlesfleche'
TWITTER_USERNAME = 'charlesfleche'

FACEBOOK_USERNAME = 'charlesfleche'
FACEBOOK_APPID = os.environ.get('FACEBOOK_APPID', '')

PATH = 'content'

TIMEZONE = 'Europe/Paris'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

STATIC_PATHS = ['.']

DIRECT_TEMPLATES = ['index']
AUTHOR_SAVE_AS = ''
CATEGORY_SAVE_AS = ''
TAG_SAVE_AS = ''

# Blogroll
# HACK Add extra FontAwesome
LINKS = (
    ('From Cambrai, France to Cambrai, Australia. On bicycles.', 'http://cambrai-cambrai.net', 'bicycle'),
)

# Social widget
SOCIAL = (
    ('Twitter', 'https://twitter.com/charlesfleche'),
    ('GitHub', 'https://github.com/charlesfleche'),
    ('LinkedIn', 'https://www.linkedin.com/in/charlesfleche/'),
)

DEFAULT_PAGINATION = False

DEFAULT_METADATA = {
    'status': 'draft',
}

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
