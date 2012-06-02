"""Implements all the functions needed to interface with a MongoDB back-end."""

import pymongo

# Notes on this module:
# Cursors time-out with OperationFailure. Reads should be wrapped in try-except

_HOST = "localhost"
_PORT = 27017
_DB = 'hphysics'

# If we were running a daemon, the daemon could share one connection between its threads. This is safe.

def mongo_connect(host=_HOST,port=_PORT,dbname=_DB):
    """Returns (connection, db) for the Mongo DB"""
    conn = pymongo.Connection(host, port)
    db = conn[dbname]
    # If we want to do any transformation:
    #    db.add_son_manipulator(Transform())
    return (conn, db)
