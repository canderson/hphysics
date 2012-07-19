# These are Python classes that represent the document-types in our database
# They must all implement a mongo_dump method that gives the data of the class in a dictionary of dictionaries, lists, and literals that is suitable for reprentation in JSON, yaml, MongoDB, etc. Their constructor should read-in a similar dictionary. 

# WARNING : An object should not have the same mongo param from multiple sources (such as multiple ancestors)
# WARNING : Each class must declare its own mongo params. Even if this is just an empty list. 

# Allowed native types: dictionaries with string keys and valid items, lists with valid items, strings, ints, floats, datetime.datetime, re.compile, pymongo.objectid.ObjectId

import sys, inspect
import copy

# A dictionary of constructors for all of the MongoDocument descendents. For use in mongo_read
MTYPES = {}
# A smart-alecky way to populate MTYPES by finding all the descendents of MongoDocument in the loaded module
for name, obj in inspect.getmembers(sys.modules[__name__]):
        if hasattr(obj, "mongo_type"):
            MTYPES[obj.mongo_type] = obj
            
def mongo_dump(obj):
    """Take an allowed native type or a MongoDocument object and output a form that is suitable to be .insert()ed into a Mongo collection."""
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
    """Take an object extracted from a Mongo collection and expand any MongoDocuments that are nested inside of it."""
    if isinstance(obj, dict):
        for (key, val) in obj.items():
            out[key] = mongo_dump(val)
            return out
        ty = obj.get('_type', None)
        if ty:
            return MTYPES[ty](obj)
    if isinstance(obj, list):
        return map(mongo_read, obj)
    return obj

# This dude deals in immutable document schemes right now. Maybe I'll write a full ORM-layer. Maybe not. Should write a migration tool that operates on the parameter level so that we can migrate easily to new schemas. 

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
        return out
    def mongo_params(self):
        out = copy.copy(self._mongo_params)
        ancestors = list(self.__class__.__bases__)
        while ancestors:
            x = ancestors.pop()
            try:
                out.extend(x._mongo_params)
                ancestors.extend(x.__bases__)
            except AttributeError: pass
        return out

# Collections

class Person(MongoDocument):
    mongo_type = 'Person'
    _mongo_params = [('display_name', 'str'),
                     ('names', 'HistoricalProperty'), # The way we deal with people is that we have a table of People and a table of Aliases. An Alias is any name that we saw used in the wild for that person. Of course, an alias might be associated with many people. 
                     ('honorifics', 'HistoricalProperty'), 
                     ('affiliations', 'HistoricalProperty'), 
                     ('emails', 'HistoricalProperty')]

class Alias(MongoDocument):
    mongo_type = 'Alias'
    _mongo_params = [('name', 'Name'),
                     ('persons', 'list')] # List of [ids, likelihood scores] for the persons. A liklihood score gives intuition for: "Given that I encountered this alias in the wild, how likely is to correspond to this person?

class Publication(MongoDocument):
    mongo_type = 'Publication'
    _mongo_params = [('publication_type','str'),
                     ('ads_bibcode','str'),
                     ('authors','list'), # List of [id, alias]
                     ('pacs_codes','list'),
                     ('keywords','list'),
                     ('title','LatexString'),
                     ('abstract','HTMLString'),
                     ('doi','str'),
                     ('arxiv_entry', 'ArxivEntry'),
                     ('published_snapshots','list')]

# Extended collection data

class Snapshot(MongoDocument):
    mongo_type = 'Snapshot'
    _mongo_params = [('date','MonthYear'), #MonthYear ORR datetime.datetime
                      ('versions', 'list')]

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
    _mongo_params = [('primary_category','str'),
                     ('categories', 'list'), # Non-primary categories
                     ('submitter','Person'),
                     ('arxiv_id', 'str'),
                     ('snapshots','list')]

class ArxivSnapshot(Snapshot):
    mongo_type = 'ArxivSnapshot'
    _mongo_params = [('comment','str'),
                      ('version','int')]

# Ancillary data types

# TODO we need to deal with comparisons of these typed strings. Ideally, we can slice into them and do other stringy stuff.
# TODO I want these both to support to_unicode methods so that I don't have to deal with them any more. Things like names that we will be searching on in the database definitely need unicode.
# TODO I also need a universal string representation for math. 

class TypedString(MongoDocument):
    _mongo_params = [('contents','str')]
    def mongo_dump(self):
            try: 
                return self.contents
            except AttributeError:
                return ''

class LatexString(TypedString):
    mongo_type = 'LatexString'
    _mongo_params = []

class HTMLString(TypedString):
    mongo_type = 'HTMLString'
    _mongo_params = []

# To transport a human's name

class Name(MongoDocument):
    mongo_type = 'Name'
    # A last name _must_ always be specified. Names may be an empty list. 
    _mongo_params = [('names','list'), 
                      ('last','LatexString'), # ORR HTML TODO switch to unicode
                      ('lineage', 'str')]
    def full_name():
            return ' '.join(map(lambda x: x.contents, self.names)) + ' ' + self.last.contents
    
    def _compatible(self, a, b):
        """A version of self.compatible that looks only at single strings."""
        # Once we're doing things properly with unicode then we will want to split this into two _permits and do accent stripping.
        if a == b: return 1
        try:  # We might get index errors, but only if they are incompatible
            if a[-1] == '.':
                if a[:-1] == b[0:len(a) - 1]:
                    return 3
            if b[-1] == '.':
                if b[:-1] == a[0:len(b) - 1]:
                    return 2
        finally:
            return 0

    def compatible(self, other):
        """This function compares two names and returns a numeric code indicating the result. The codes are given below where the call was one.two:
        0 : The names are incompatible. Any other code means that they are compatible.
        1 : The names are identical.
        2 : one contains more data than two.
        3 : two contains more data than one.
        4 : both 2 and 3 hold."""
        # TODO. Once this is standardized to my liking it can be used to implement __cmp__
        # Right now, we assume that we don't have to have any names except the last. So A. B. Foo and C. D. Foo are the same people (and they both contain more data than the other). 
        if other.last != self.last: return 0
        if other.lineage != self.lineage: return 0
        data = [self.permits(other), other.permits(self)]
        if data[0] and data[1]: return 4
        if data[0]: return 2
        if data[1]: return 3
        assert()

    def permits(self, other):
        """Asks if self.names carries more data or the same amount of data as other.names"""
        i = 0
        onl = len(other.names)
        for n in self.names:
            for j in range(i, onl):
                res = self._permits(n, other.names[j])
                if res in [0,3]: continue # I didn't fit inside it
                else:
                    i = j + 1
            else: return False
        return True

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
                MongoDocument.__init__(self,d)

# TODO this needs more
class HistoricalProperty(MongoDocument):
    mongo_type = 'HistoricalProperty'
    _mongo_params = [('simul','bool'),
                      ('data','list')] #XXX

    def update(self, time, value):
        self.data.append([time, value])
