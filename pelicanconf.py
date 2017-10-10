#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Charles Flèche'
SITENAME = 'Charles Flèche'
SITEURL = ''

THEME = 'charlesfleche'

TWITTER_USERNAME = 'charlesfleche'

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
LINKS = (('From Cambrai, France to Cambrai, Australia. On bicycles.', 'http://cambrai-cambrai.net'),
         ('My current project: Previz', 'https://previz.co'))

# Social widget
SOCIAL = (('LinkedIn', 'https://www.linkedin.com/in/charlesfleche/'),
          ('Twitter', 'https://twitter.com/charlesfleche'),
          ('GitHub', 'https://github.com/charlesfleche'),)

DEFAULT_PAGINATION = False

DEFAULT_METADATA = {
    'status': 'draft',
}

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
