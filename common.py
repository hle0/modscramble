import fnmatch
import json
import shutil
import zipfile
import random

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x: x

def _matches(query_parts, subject_parts):
    if len(query_parts) == 0 and len(subject_parts) == 0:
        return True
    elif len(query_parts) > 0 and len(subject_parts) > 0:
        if query_parts[0] == '**':
            for i in range(0, len(subject_parts)):
                if _matches(query_parts[1:], subject_parts[i:]):
                    return True
            return False
        elif isinstance(subject_parts[0], int):
            if query_parts[0] == '*' or str(subject_parts[0]).lower() == str(query_parts[0]).lower():
                return _matches(query_parts[1:], subject_parts[1:])
            return False
        else:
            return fnmatch.fnmatch(subject_parts[0].lower(), query_parts[0].lower()) and _matches(query_parts[1:], subject_parts[1:])
    else:
        return False

def matches(query, subject):
    return _matches(query.split('/'), subject.split('/'))

def json_keys(obj):
    yield []
    if isinstance(obj, dict):
        for (key, val) in obj.items():
            for subkey in json_keys(val):
                yield [key, *subkey]
    elif isinstance(obj, list):
        for (key, val) in enumerate(obj):
            for subkey in json_keys(val):
                yield [key, *subkey]

def json_set(obj, key, value):
    if len(key) == 0:
        return value
    elif len(key) == 1:
        obj[key[0]] = value
    else:
        json_set(obj[key[0]], key[1:], value)
    return obj

def json_get(obj, key):
    if len(key) == 0:
        return obj
    else:
        return json_get(obj[key[0]], key[1:])

def slurp(func):
    def wrapper(*args, **kwargs):
        return list(func(*args, **kwargs))
    return wrapper

def json_to_bytes(func):
    def wrapper(*args, **kwargs):
        return json.dumps(func(*args, **kwargs)).encode('utf-8')
    return wrapper

def no_strings(no_resource_keys=True):
    def func(obj):
        if isinstance(obj, str):
            return False
        elif isinstance(obj, dict):
            if no_resource_keys:
                if any(':' in key for key in obj):
                    return False
            return all(no_strings(val) for val in obj.values())
        elif isinstance(obj, list):
            return all(no_strings(val) for val in obj)
        else:
            return True
    return func

minecraft_only = lambda x: isinstance(x, str) and x.startswith('minecraft:')

@slurp
def json_rules(applied_file_glob, folder, json_extraction_points, filter=lambda x: True):
    @json_to_bytes
    def replace(rule, base_buf, supermod, sanity):
        base = json.loads(base_buf)
        for key in json_keys(base):
            for (i, point) in enumerate(json_extraction_points):
                if _matches(point, key):
                    fn = pick_random(supermod, folder + '/' + str(i))
                    if fn is not None:
                        if random.random() > sanity:
                            obj = None
                            for i in range(10):
                                obj = json.loads(supermod.read(fn))
                                if filter(obj):
                                    break
                            else:
                                continue
                            base = json_set(base, key, obj)
        return base
    
    for (i, point) in enumerate(json_extraction_points):
        @slurp
        def transform(rule, buf):
            obj = json.loads(buf)
            for key in json_keys(obj):
                if _matches(point, key):
                    val = json_get(obj, key)
                    if filter(val):
                        yield json.dumps(val).encode('utf-8')
        
        yield (applied_file_glob, folder + '/' + str(i), (transform, replace))

# TODO: this is a memory leak, and also kind of hacky in general, but should be fine for now.
zip_dir_cache = {}

def get_zip_dir_cache(zip_file):
    if zip_file not in zip_dir_cache.keys():
        zip_dir_cache[zip_file] = zip_file.namelist()
    return zip_dir_cache[zip_file]

def pick_random(zip_file, prefix):
    cache = get_zip_dir_cache(zip_file)
    choices = [fn for fn in cache if fn.startswith(prefix + '/')]
    if len(choices) > 0:
        return random.choice(choices)

def identity_replace(rule, base, supermod, sanity):
    fn = pick_random(supermod, rule[1])
    if (fn is not None) and (random.random() > sanity):
        return supermod.read(fn)
    else:
        return base

identity_transform = lambda rule, x: [x]
ident = (identity_transform, identity_replace)

rule_aliases = {
    'sounds': ['sounds/ogg', 'sounds/wav', 'sounds/mp3'],
    'models': ['models/block', 'models/item'],
    '3d': ['3d/stl', '3d/obj'],
    'lang': ['lang/en_us'],
    'any': ['textures', 'sounds', 'models', '3d', 'lang', 'recipes']
}

def filter_rules(tags):
    total_tag_list = tags.lower().split(',')
    while any(tag in rule_aliases.keys() for tag in total_tag_list):
        tmp = []
        for key in total_tag_list:
            if key in rule_aliases.keys():
                tmp.extend(rule_aliases[key])
            else:
                tmp.append(key)
        total_tag_list = tmp
    total_tag_list = set(total_tag_list)

    rules = {
        'textures': [('**/*.png', 'textures', ident)],
        'sounds/ogg': [('**/*.ogg', 'sounds/ogg', ident)],
        'sounds/wav': [('**/*.wav', 'sounds/wav', ident)],
        'sounds/mp3': [('**/*.mp3', 'sounds/mp3', ident)],
        '3d/stl': [('**/*.stl', '3d/stl', ident)],
        '3d/obj': [('**/*.obj', '3d/obj', ident)],
        'models/block': json_rules('assets/*/models/block/*.json', 'assets/models/block', [
            ['elements', '*', 'from'],
            ['elements', '*', 'to'],
            ['elements', '*', 'rotation'],
        ]),
        'models/item': json_rules('assets/*/models/item/*.json', 'assets/models/item', [
            ['display', '*', 'rotation'],
            ['display', '*', 'translation'],
        ]),
        'lang/en_us': json_rules('assets/*/lang/en_us.json', 'assets/lang/en_us', [
            ['*']
        ]),
        'recipes': json_rules('data/*/recipes/**/*.json', 'data/recipes', [
            ['result', 'item'],
            ['ingredient', 'item'],
            ['key', '*', 'item']
        ], filter=minecraft_only)
        #('assets/*/models/block/*.json', 'assets/models/block', ident),
        #('assets/*/models/item/*.json', 'assets/models/item', ident)
    }

    l = []
    for (key, val) in rules.items():
        if key in total_tag_list:
            l.extend(val)

    return l