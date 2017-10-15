#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals
import os

LOAD_CONTENT_CACHE = False

PLUGIN_PATHS = ['../pelican-plugins']
PLUGINS = ['assets']

AUTHOR = 'Charles Flèche'
SITENAME = 'Charles Flèche'
DESCRIPTION = 'The personnal blog of Charles Flèche'
KEYWORDS = 'software development, blog, live shows'
SITEURL = ''

THEME = 'charlesfleche'
THEME_STATIC_DIR = '.'

DATE_FORMATS = {
    'en': ('en_US','%d %B %Y'),
    'fr': ('fr_FR','%d %B %Y'),
}

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

FAVICON_PNG = 'icon.png'

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

ARTICLE_URL = '{lang}/{slug}'
ARTICLE_SAVE_AS = ARTICLE_URL + '/index.html'
ARTICLE_LANG_URL = ARTICLE_URL
ARTICLE_LANG_SAVE_AS = ARTICLE_SAVE_AS
DRAFT_URL = 'drafts/' + ARTICLE_URL
DRAFT_SAVE_AS = DRAFT_URL + '/index.html'
DRAFT_LANG_URL = DRAFT_URL
DRAFT_LANG_SAVE_AS = DRAFT_SAVE_AS
PAGE_URL = ARTICLE_URL
PAGE_SAVE_AS = ARTICLE_SAVE_AS
PAGE_LANG_URL = ARTICLE_LANG_URL
PAGE_LANG_SAVE_AS = ARTICLE_LANG_SAVE_AS

FORMATTED_FIELDS = ['summary', 'headerimage']

TYPOGRIFY = True

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
