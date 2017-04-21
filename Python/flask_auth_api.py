#!/usr/bin/env python

import os
from flask import Flask, abort, request, jsonify, g, url_for
import flask
import redis
import json
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
from flask import Response, stream_with_context

# initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'

db = redis.Redis('localhost') #connect to server

EXPIRATION_TOKEN_TIMESTAMP = 10000000000

class User:

    def hash_password(self, password):
        return pwd_context.encrypt(password)

    def authenticate_user(self, username, password):
        redis_user = prefix + username
        user_redis_record = db.hgetall(redis_user)
        if user_redis_record and b'password' in user_redis_record and user_redis_record[b'password'] != None:
            return pwd_context.verify(password, user_redis_record[b'password'])

        return False

    def generate_auth_token(self, expiration, username):
        s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
        token = s.dumps({'username': username})
        db.hmset(token, {'username': username})
        return token

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None    # valid token, but expired
        except BadSignature:
            return None    # invalid token

        data_token = db.hgetall(token)
        username = data_token[b'username'] if data_token and b'username' in data_token and data_token[b'username'] else None
        return username or None



def login_required(f):
    
    def authentication(*args, **kwargs):
        username_or_token = request.authorization['username']
        password = request.authorization['password']
        # first try to authenticate by token
        username = User.verify_auth_token(username_or_token)
        if not username:

            # try to authenticate with username/password
            is_user_authenticated = User.authenticate_user(username_or_token, password)

            if not is_user_authenticated:
                return jsonify({'error': 'Sorry! The user credentials Invalid'})

            return f(*args, **kwargs)

        return f(*args, **kwargs)
    return authentication

def verify_user(username, password):

    # try to authenticate with username/password
    if not User.authenticate_user(username, password):
        return False

    return True

@app.route('/api/token')
def get_auth_token():
    username = request.authorization["username"]
    user_npr = prefix + username
    password = request.authorization["password"]

    user_redis_record = verify_user(username, password)
    token = '';

    if user_redis_record:
        # Update the redis key for the token after creating a new token
        # token = User.generate_auth_token(EXPIRATION_TOKEN_TIMESTAMP, username)
        # token = user_redis_record[b'token'].decode('utf-8') if user_redis_record and b'token' in user_redis_record and user_redis_record[b'token'] else None
        user_redis_record = db.hgetall(user_npr)
        token = user_redis_record['token'] if user_redis_record and 'token' in user_redis_record and user_redis_record['token'] else None
        new_token = User.generate_auth_token(EXPIRATION_TOKEN_TIMESTAMP, username)
        user_redis_record['token'] = new_token
        token_user_record = {'username': username}
        db.delete(user_npr, token)
        db.hmset(new_token, token_user_record)
        db.hmset(user_npr, user_redis_record)

        return jsonify({'token': new_token, 'duration': EXPIRATION_TOKEN_TIMESTAMP})

    return jsonify({'error': 'Sorry! The token cannot be generated because the user credentials not found'})

@app.route('/api/resource')
@login_required
def get_resource():
    """
    username = login_required()
    if username:
        return jsonify({'data': 'Hello!', 'username': username})
    else:
        return jsonify({'sorry': 'does not exist'})
    """
    return jsonify({'data': 'Hello!'})

if __name__ == '__main__':
    prefix = "user:"
    User = User()
    app.run(debug=True)
