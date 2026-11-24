import re

KEBAB = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
SNAKE = re.compile(r'^[a-z0-9]+(_[a-z0-9]+)*$')
CAMEL = re.compile(r'^[A-Z][A-Za-z0-9]*$')

def is_kebab(s): return bool(KEBAB.match(s))
def is_snake(s): return bool(SNAKE.match(s))
def is_camel(s): return bool(CAMEL.match(s))

def classify_yaml_key(key):
    if '-' in key:
        return 'kebab' if is_kebab(key) else 'invalid-kebab'
    if '_' in key:
        return 'snake' if is_snake(key) else 'invalid-snake'
    if key.lower() == key:
        return 'flat'
    return 'invalid'
