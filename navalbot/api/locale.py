"""
=================================

This file is part of NavalBot.
Copyright (C) 2016 Isaac Dickinson

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>

=================================
"""

# Locale support.
import logging
import os

import yaml

# Dict of locale loaders.
locale_loaders = {}

LOCALE_ROOT = os.path.join(os.getcwd(), "localization")
LOCALE_FILE_BUILDER = "locale.{lang}.yml"

logger = logging.getLogger("LocaleLoader")


class LocaleLoader:
    """
    This defines a locale loader, that loads the specified locale key from the file each time.
    """

    def __init__(self, locale: str = None):
        self.lang = locale

        # Load the files.
        if self.lang is None:
            # Set the last loaded time to well in the future.
            self.lang = ""
            self._last_load = 2147483647
            self._locale_data = {}
            self.path = ""
        else:
            self.path = os.path.join(LOCALE_ROOT, LOCALE_FILE_BUILDER.format(self.lang))
            if not os.path.exists(self.path):
                logger.warning("No such locale: `{}`".format(self.lang))
                self._last_load = 2147483647
                self._locale_data = {}
            # Load the data from the file.
            else:
                self._last_load = os.stat(self.path).st_mtime
                with open(self.path) as f:
                    self._locale_data = yaml.load(f)

        # Load the default data.
        self._default_path = os.path.join(LOCALE_ROOT, "locale.yml")
        with open(self._default_path) as f:
            self._default_last_load = os.stat(self._default_path).st_mtime
            self._default_data = yaml.load(f)

    def _reload_locale(self):
        """
        Reloads the locale, if required.
        """
        if os.path.exists(self.path):
            mtime = os.stat(self.path).st_mtime
            if mtime > self._last_load:
                # Reload the file.
                with open(self.path) as f:
                    self._locale_data = yaml.load(f)
        # Do the same for default locale.
        mtime = os.stat(self._default_path)
        if mtime > self._default_last_load:
            # Reload the file
            with open(self._default_path) as f:
                self._default_data = yaml.load(f)

    def __getitem__(self, key) -> str:
        """
        Load the key from the locale DB
        """
        self._reload_locale()
        if key in self._locale_data:
            return self._locale_data[key]
        elif key in self._default_data:
            return self._default_data[key]
        else:
            return key


def get_locale(lang: str) -> LocaleLoader:
    """
    Sanitize the language string, and load it from disk.
    """
    if lang:
        safe_lang = "".join(x for x in lang if x.isalnum())
    else:
        safe_lang = None
    if safe_lang not in locale_loaders:
        locale_loaders[safe_lang] = LocaleLoader(safe_lang)

    return locale_loaders[safe_lang]
