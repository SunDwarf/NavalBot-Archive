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

# de-reference lc so it doesn't intefere
del lc

if len(keys) == 0:
    print("No new keys to add.")
else:
    print("New keys to add to your translation file:\n\n=============================================\n\n")
    for k in keys:
        if k.startswith("help"):
            print("{}: |\n        Add translation here.\n".format(k))
        else:
            print("{}: \"Add translation here.\"".format(k))