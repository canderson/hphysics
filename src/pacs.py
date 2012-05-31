import re
import yaml

PACS_REGEX = re.compile(r"[0-9]{2}\.[0-9]{2}\.[a-zA-Z\-\+][a-zA-Z\-]")

PACS_DATA = "../pacs/pacs.yml"

f = open(PACS_DATA)
PACS_TREE = yaml.load(f.read())
f.close()
PACS_NAMES = {}
for x in PACS_TREE:
    try:
        PACS_NAMES[PACS_TREE[x]['name']] = x
    except KeyError:
        pass

def pacs_get_level(code):
    if code[1] == '0': return 1
    if len(code) == 3: return 2
    assert len(code) == 8
    if code[6] in ('+','-'): return 3
    if code[6].isupper(): return 4
    return 5
