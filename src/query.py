import hphys_types as ht

def compatible_name(coll, name):
    """Queries in an Alias collection and returns a tuple ([[List_of_possible_names, Likeliehood_score]], Known_alias?)."""
    known_alias = coll.find_one(name.mongo_dump())
    if known_alias:
        return (mongo_read(known_alias).persons, True)
    else:
    return ([[x._id, 1] for x in map(ht.Name, coll.find({"name.last" : name.last})) with name.compatible(x)], False)
