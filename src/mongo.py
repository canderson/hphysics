"""Implements all the functions needed to interface with a MongoDB back-end."""

import pymongo

# Notes on this module:
# Cursors time-out with OperationFailure. Reads should be wrapped in try-except

_HOST = "localhost"
_PORT = 27017
_DB = 'hphysics'

# If we were running a daemon, the daemon could share one connection between its threads. This is safe.

def mongo_connect():
    """Returns (connection, db) forthe Mongo DB"""
    conn = pymongo.Connection(_HOST, _PORT)
    db = conn[_DB]
    # If we want to do any transformation:
    #    db.add_son_manipulator(Transform())
    return (conn, db)
