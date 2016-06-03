"""
Tool to show what keys are missing in a specified locale file.
"""
import sys, os, asyncio

import yaml

sys.path.insert(0, os.path.abspath("."))

import navalbot.api.botcls as b

loop = asyncio.get_event_loop()

# Create a fake client, and load the plugins.
client = b.NavalClient()
loop.run_until_complete(client.load_plugins())

from navalbot.api.locale import get_locale

lc = get_locale(sys.argv[1])

kys = {}

for file, val in lc._locale_files.items():
    if len(val) == 1:
        print("File {} has yet to be translated.".format(file))
        continue
    default, local = sorted(val, key=lambda x: x[2])[::-1]
    d_data, l_data = yaml.load(open(default[1])), yaml.load(open(local[1]))
    kys[local[1]] = []
    for key in d_data:
        if key not in l_data:
            kys[local[1]].append(key)

if len(kys) == 0:
    print("No new keys to add.")
else:
    for name, keys in kys.items():
        print("New keys for {}:\n".format(name))
        for k in keys:
            if k.startswith("help"):
                ks = []
                nkk = lc[k].split('\n')
                for nk in nkk:
                    ks.append((' ' * 8) + nk)
                nk = '\n'.join(ks)
                print("{}: |\n{}\n".format(k, nk))
            else:
                print("{}: \"{}\"".format(k, lc[k]))
        print("")