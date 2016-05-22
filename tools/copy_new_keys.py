"""
Tool to show what keys are missing in a specified locale file.
"""
import sys, os
sys.path.insert(0, os.path.abspath("."))

from navalbot.api.locale import get_locale

lc = get_locale(sys.argv[1])

keys = []

for key in lc._default_data:
    if key not in lc._locale_data:
        keys.append(key)


if len(keys) == 0:
    print("No new keys to add.")
else:
    print("New keys to add to your translation file:\n\n=============================================\n\n")
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