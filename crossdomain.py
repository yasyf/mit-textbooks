# http://flask.pocoo.org/snippets/56/

from flask import make_response, request, current_app
from functools import update_wrapper


def crossdomain(origin=None, methods=None):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
