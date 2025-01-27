from functools import wraps
from flask import request, Response
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

def check_auth(username, password):
    """Check if username/password combination is valid"""
    if username not in Config.USERS:
        return False
    return check_password_hash(Config.USERS[username], password)

def authenticate():
    """Send 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated