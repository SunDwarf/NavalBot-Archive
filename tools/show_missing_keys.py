"""
Tool to show what keys are missing in a specified locale file.
"""
import sys
from navalbot.api.locale import get_locale

lc = get_locale(sys.argv[1])

keys = []

for key in lc._default_data:
    if not key in lc._locale_data:
        keys.append(key)

print("Missing keys: ")
for k in keys:
    print(" - {}".format(k))