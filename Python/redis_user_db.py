#!/usr/bin/env python
# ------------------------------------------------------------------
# Tool to add or delete a user from redis database for Auto-IT server to user
#
# Copyright (c) 2016 by cisco Systems, Inc.
# All rights reserved.
# ------------------------------------------------------------------

import os
import sys
import argparse
import json
import redis
from passlib.apps import custom_app_context as pwd_context

db = redis.Redis('localhost') #connect to server

class User:

    def hash_password(self, password):
        return pwd_context.encrypt(password)

def new_user(args):
    username = prefix + args.username
    password = args.password
    if username is None or password is None:
        print("Missing arguments")
        sys.exit(0)
    if db.exists(username) is not False:
        print("User with %s already exists" % username)
        sys.exit(0)
    hashed_password = User.hash_password(password)
    token = '';
    user_record = {'password': hashed_password, 'token': token}
    db.hmset(username, user_record)
    print("Created new user : %s" % args.username)

    return


def del_user(args):
    username = prefix + args.username
    if username is None:
        print("Missing arguments")
        sys.exit(0)
    if db.exists(username) is not True:
        print("User with %s does not exist" % username)
        sys.exit(0)

    user_redis_record = db.hgetall(username)
    token = user_redis_record[b'token'].decode('utf-8') if user_redis_record and b'token' in user_redis_record and user_redis_record[b'token'] else None
    db.delete(username, token)

    return

def list_users():
    print("\n".join(db.keys(prefix + '*')))

    return

def parse_args():
    "Parse command line arguments"

    desc = """
    This tool Add's or Delete's a user from the redis database for Auto-IT server to use.
    """
    parser = argparse.ArgumentParser(
        description=desc,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)

    parser.add_argument('-h', '--help',
                     action='help',
                     help='Show this help message and exit')
    parser.add_argument("--func", type=lambda s : s.lower(),
                     help="Use ADD/DEL to add or delete a user, Use LISTALL to list all users in the database")
    parser.add_argument("--username", type=lambda s : s.lower(),
                     help="Username")
    parser.add_argument("--password", type=str,
                     help="Password")

    return parser.parse_args()



if __name__ == '__main__':
    prefix = "usp-auto-it:"
    User = User()
    args = parse_args()

    if args.func == "add":
        new_user(args)
    elif args.func == "del":
        del_user(args)
    elif args.func == "listall":
        list_users()
    else:
        print("Invalid Arguments")
