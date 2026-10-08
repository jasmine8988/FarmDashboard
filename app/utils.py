import datetime
import logging
import re

from functools import wraps

from flask import abort, g, redirect, request, session

import config

log = logging.getLogger("\033[1;34mutils\033[0m")

password_patterns = [re.compile(pattern)
                     for pattern in [
                         r'^(?=[^!\"#\$%&\'\(\)\*\+,-\.\/:;<=>\?@\[\\\]\^_`\{\|\}~]*'
                         r'[!\"#\$%&\'\(\)\*\+,-\.\/:;<=>\?@\[\\\]\^_`\{\|\}~])',
                         r'^(?=[^A-Z]*[A-Z])',
                         r'^(?=[^a-z]*[a-z])',
                         r'^(?=[^\d]*[\d])', ]]


def row2dict(row, str_datetime=True):
    """Convert query object by sqlalchemy to dictionary object."""
    if not row:
        return None

    d = {}
    if hasattr(row, '__table__'):
        for column in row.__table__.columns:
            d[column.name] = getattr(row, column.name)
            if str_datetime and isinstance(d[column.name], datetime.datetime):
                d[column.name] = str(d[column.name])
    if hasattr(row, '_fields'):
        for column_name in row._fields:
            d[column_name] = getattr(row, column_name)
            if str_datetime and isinstance(d[column_name], datetime.datetime):
                d[column_name] = str(d[column_name])
    return d


def validate_password_combination(password: str) -> bool:
    counter = 0

    for password_pattern in password_patterns:
        if not password_pattern.match(password):
            continue

        counter = counter + 1

    return counter >= 3


def required_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('username'):
            return f(*args, **kwargs)
        else:
            return redirect(lang_url('/login?next=' + request.path))
    return decorated_function


def required_superuser(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('username'):
            if session.get('is_superuser'):
                return f(*args, **kwargs)
            else:
                abort(403)
        else:
            return redirect(lang_url('/login?next=' + request.path))
    return decorated_function


def security_redirect():
    base_url = lang_url('/dashboard_dropdown')
    next_url = request.args.get('next', base_url)
    if re.search(config.REDIRECT_REGEX, next_url, re.IGNORECASE):
        return redirect(next_url)
    else:
        return redirect(base_url)


def lang_url(url):
    if url.startswith('/'):
        return '/{}{}'.format(g.get('lang_code'), url)
    else:
        return '/{}/{}'.format(g.get('lang_code'), url)
