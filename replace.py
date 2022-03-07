import argparse
import shutil
import zipfile
from hashlib import md5
import random

from common import filter_rules, matches, tqdm

def replace_mod(mod_in, mod_out, supermod, sanity, rules):
    for member in tqdm(mod_in.namelist()):
        for rule in rules:
            (fro, to, (_, replace)) = rule
            if 'colormap' in member:
                continue
            if matches(fro, member):
                h = mod_in.read(member)
                with mod_out.open(member, 'w') as f:
                    f.write(replace(rule, h, supermod, sanity))
                break
        else:
            with mod_in.open(member, 'r') as f:
                with mod_out.open(member, 'w') as g:
                    shutil.copyfileobj(f, g)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mod_in')
    parser.add_argument('mod_out')
    parser.add_argument('supermod_file')
    parser.add_argument('-s', '--sanity', nargs='?', type=float, default=0, help='from 0 to 1, represents the fraction of the mod to remain unchanged')
    parser.add_argument('-f', '--filter-only', nargs='?', type=str, default='any', help='only allow replacement rules with these tags (comma-separated)')
    args = parser.parse_args()
    if args.sanity > 1 or args.sanity < 0:
        raise ValueError('--sanity must be between 0 and 1')
    with zipfile.ZipFile(args.supermod_file, 'r') as supermod:
        with zipfile.ZipFile(args.mod_in, 'r') as mod_in:
            with zipfile.ZipFile(args.mod_out, 'w') as mod_out:
                replace_mod(mod_in, mod_out, supermod, args.sanity, filter_rules(args.filter_only))