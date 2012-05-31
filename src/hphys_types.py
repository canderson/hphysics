# These are Python classes that represent the document-types in our database
# They must all implement a mongo_dump method that gives the data of the class in a dictionary of dictionaries, lists, and literals that is suitable for reprentation in JSON, yaml, MongoDB, etc. Their constructor should read-in a similar dictionary. 

# WARNING : An object should not have the same mongo param from multiple sources (such as multiple ancestors)
# WARNING : Tuples cannot be serialized. Do not use them here.

import sys, inspect

#heh, I don't like typing
MTYPES = {}
for name, obj in inspect.getmembers(sys.modules[__name__]):
        if hasattr(obj, "mongo_type"):
            MTYPES[obj.mongo_type] = obj

def mongo_dump(obj):
    if isinstance(obj, dict):
        out = {}
        for (key, val) in obj.items():
            out[key] = mongo_dump(val)
            return out
    elif isinstance(obj, list):
        return map(mongo_dump, obj)
    elif hasattr(obj, "mongo_dump"):
        return obj.mongo_dump()
    return obj

def mongo_read(obj):
    if isinstance(obj, dict):
        ty = obj.get('_type', None)
        if ty:
            return MTYPES[ty](obj)
    if isinstance(obj, list):
        return map(mongo_read, obj)
    return obj

# This dude deals in immutable documents right now. Maybe I'll write a full ORM-layer. Maybe not. Should write a migration tool that operates on the parameter level so that we can migrate easily to new schemas. 

class MongoDocument:
    def __init__(self, d = {}):
        for x in self.mongo_params():
            pname = x[0]
            val = d.get(pname, None)
            if val:
                setattr(self, pname, val)
        val = d.get('_id', None)
        setattr(self, 'id', val)
    def mongo_dump(self):
        out = {'_type': self.mongo_type}
        for x in self.mongo_params():
            out[x[0]] = mongo_read(getattr(self,x[0]))
    def mongo_params(self):
        out = self._mongo_params
        ancestors = list(self.__class__.__bases__)
        while ancestors:
            x = ancestors.pop()
            try:
                out.extend(x._mongo_params)
                ancestors.extend(x.__bases__)
            except AttributeError:
                pass
        return out

# Collections

class Person(MongoDocument):
    mongo_type = 'Person'
    _mongo_params = [('names', 'HistoricalProperty'), 
                      ('honorifics', 'HistoricalProperty'), 
                      ('affiliations', 'HistoricalProperty'), 
                      ('emails', 'HistoricalProperty')]

class Publication(MongoDocument):
    mongo_type = 'Publication'
    _mongo_params = [('publication_type','str'),
                      ('ads_bibcode','str'),
                      ('authors','list'), # Of ids?
                      ('pacs_code','list'),
                      ('keywords','list'),
                      ('title','LatexString'),
                      ('doi','str'),
                      ('arxiv_entry', 'ArxivEntry'),
                      ('published_snapshots','list')]

# Extended collection data

class Snapshot(MongoDocument):
    mongo_type = 'Snapshot'
    _mongo_params = [('date','MonthYear'), #MonthYear ORR datetime.date
                      ('available_versions', 'list')]

class JournalSnapshot(Snapshot):
    mongo_type = 'JournalSnapshot'
    _mongo_params = [('journal','string'),
                      ('volume','string'),
                      ('number','string'),
                      ('pages','string')]
    _bibtex_names = [x[0] for x in _mongo_params]

    def bibtex_names(self):
        return self._bibtex_names

class ArxivEntry(MongoDocument):
    mongo_type = 'ArxivEntry'
    _mongo_params = [('subjects','list'),
                      ('submitter','Person'),
                      ('arxiv_id', 'str'),
                      ('snapshots','list')]

class ArxivSnapshot(Snapshot):
    mongo_type = 'ArxivSnapshot'
    _mongo_params = [('comment','str'),
                      ('version','int')]

# Ancillary data types

class LatexString(MongoDocument):
    mongo_type = 'LatexString'
    _mongo_params = [('contents','str')]

# To transport a human's name

class Name(MongoDocument):
    mongo_type = 'Name'
    _mongo_params = [('names','list'), 
                      ('last','LatexString'),
                      ('lineage', 'str')]

    def permits(self, other):
        pass #TODO

    def __eq__(self, other):
        if self.last != other.last: return False
        if len(self.names) != len(other.names): return False
        for i in range(0, len(self.names)):
            if self.names[i] != other.names[i]: return False
        if self.lineage != other.lineage: return False
        return True

    def __neq__(self, other):
        return not __eq__(self,other)

class MonthYear(MongoDocument):
        mongo_type="MonthYear"
        _mongo_params = [('year','int'),
                          ('month','int')]
        def __init__(self, d = {}):
                assert d['year']
                assert d['month']
                MongoDocument.__init__(self,d)

# TODO this needs more
class HistoricalProperty(MongoDocument):
    mongo_type = 'HistoricalProperty'
    _mongo_params = [('simul','bool'),
                      ('data','list')] #XXX

    def update(self, time, value):
        self.data.append([time, value])
