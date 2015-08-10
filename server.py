# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta

from clastic import Application, render_basic, Middleware
from clastic.meta import MetaApplication
from clastic.render import AshesRenderFactory
from clastic.static import StaticApplication

from boltons.strutils import find_hashtags
from boltons.tbutils import ExceptionInfo

from dal import HashtagDatabaseConnection
from common import PAGINATION


Database = HashtagDatabaseConnection()

TEMPLATES_PATH = 'templates'
STATIC_PATH = 'static'
_CUR_PATH = os.path.dirname(__file__)


def format_timestamp(timestamp):
    _timestamp_pattern = '%Y%m%d%H%M%S'
    timestamp = datetime.strptime(timestamp, _timestamp_pattern)
    return timestamp.strftime('%d %b %Y %H:%M:%S')


def format_revs(rev):
    url_str = 'https://%s.wikipedia.org/wiki/?diff=%s&oldid=%s'
    rev['spaced_title'] = rev.get('rc_title', '').replace('_', ' ')
    rev['diff_size'] = rev['rc_new_len'] - rev['rc_old_len']
    rev['date'] = format_timestamp(rev['rc_timestamp'])
    rev['diff_url'] = url_str % (rev['htrc_lang'],
                                 rev['rc_this_oldid'],
                                 rev['rc_last_oldid'])
    rev['tags'] = find_hashtags(rev['rc_comment'])
    for tag in rev['tags']:
        # TODO: Turn @mentions into links
        link = '<a href="/hashtags/search/%s">#%s</a>' % (tag, tag)
        new_comment = rev['rc_comment'].replace('#%s' % tag, link)
        rev['rc_comment'] = new_comment
    return rev


def calculate_pages(offset, total, pagination):
    # Check if there is a previous page
    if offset == 0:
        prev = -1
    elif (offset - pagination) < 0:
        prev = 0
    else:
        prev = offset - pagination
    # Check if there is a next page
    if (offset + pagination) >= total:
        next = -1
    else:
        next = offset + pagination
    return prev, next


def format_stats(stats):
    stats['bytes'] = '{:,}'.format(int(stats['bytes']))
    stats['revisions'] = '{:,}'.format(stats['revisions'])
    stats['pages'] = '{:,}'.format(stats['pages'])
    stats['users'] = '{:,}'.format(stats['users'])
    stats['newest'] = format_timestamp(stats['newest'])
    stats['oldest'] = format_timestamp(stats['oldest'])
    return stats


def home():
    top_tags = Database.get_top_hashtags()
    return {'top_tags': top_tags}


def generate_report(request, tag=None, offset=0):
    offset = int(offset)
    if tag:
        tag = tag.lower()
    revs = Database.get_hashtags(tag, offset)
    stats = Database.get_hashtag_stats(tag)
    stats = format_stats(stats[0])
    ret = [format_revs(rev) for rev in revs]
    prev, next = calculate_pages(offset, 
                                 int(stats['revisions'].replace(',', '')),
                                 PAGINATION)
    page = {'start': offset, 
            'end': offset + len(revs),
            'prev': prev,
            'next': next}
    return {'revisions': ret, 
            'tag': tag, 
            'stats': stats,
            'page': page}


def create_app():
    _template_dir = os.path.join(_CUR_PATH, TEMPLATES_PATH)
    _static_dir = os.path.join(_CUR_PATH, STATIC_PATH)
    templater = AshesRenderFactory(_template_dir)
    # TODO: Add support for @mentions
    routes = [('/', home, 'index.html'),
              ('/search/', generate_report, 'report.html'),
              ('/search/all', generate_report, 'report.html'),
              ('/search/all/<offset>', generate_report, 'report.html'),
              ('/search/<tag>', generate_report, 'report.html'),
              ('/search/<tag>/<offset>', generate_report, 'report.html'),
              ('/static', StaticApplication(_static_dir)),
              ('/meta/', MetaApplication())]
    return Application(routes, 
                       middlewares=[],
                       render_factory=templater)


if __name__ == '__main__':
    app = create_app()
    app.serve()
