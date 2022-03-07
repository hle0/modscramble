import argparse
from json import JSONDecodeError
import traceback
import zipfile
from hashlib import md5

from common import matches, filter_rules, tqdm

rules = filter_rules('any')

def translate(fro, to, subject, zip_file):
    if not matches(fro, subject):
        return None
    with zip_file.open(subject, 'r') as f:
        return to + '/' + md5(f.read()).hexdigest() + subject[subject.rindex('.'):]

def append_assets(mod, supermod):
    for member in mod.namelist():
        for rule in rules:
            (fro, to, (transformer, _))  = rule
            if matches(fro, member):
                g = mod.read(member)
                try:
                    for output in transformer(rule, g):
                        where = to + '/' + md5(output).hexdigest() + member[member.rindex('.'):]
                        try:
                            supermod.getinfo(where)
                        except KeyError:
                            with supermod.open(where, 'w') as f:
                                f.write(output)
                except JSONDecodeError:
                    print('got an exception while decoding some json, skipping')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('supermod_file')
    parser.add_argument('mod_file', nargs='+')
    args = parser.parse_args()
    with zipfile.ZipFile(args.supermod_file, 'a') as supermod:
        for mod_file in tqdm(args.mod_file):
            with zipfile.ZipFile(mod_file, 'r') as mod:
                append_assets(mod, supermod)