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

from navalbot.api import botcls

# Dict of locale loaders.
locale_loaders = {}

LOCALE_ROOT = os.path.join(os.getcwd(), "localization")
LOCALE_FILE_BUILDER = "locale.{lang}.yml"

logger = logging.getLogger("LocaleLoader")


def get_locale_directory(lang: str) -> str:
    return os.path.join(LOCALE_ROOT, lang)


class LocaleLoader:
    """
    This defines a locale loader, that loads the specified locale key from the file each time.
    """

    def __init__(self, locale: str = None):
        self.lang = locale

        # Get the instance of the bot.
        self.client = botcls.NavalClient.get_navalbot()
        try:
            assert isinstance(self.client, botcls.NavalClient)
        except AssertionError as e:
            raise TypeError("Attempted to load locales before NavalBot has loaded") from e

        self._locale_files = {}

        self._locale_data = {}
        self._default_data = {}

        self._load_locale_files()

    def _load_locale_files(self):
        """
        Automatically load all of the locale files that are specified for loading by plugins.
        """
        for name, mod in self.client.modules.items():
            logger.info("Loading locale data for plugin: {}".format(name))
            # Use `LOCALE_DIR`/locale.<lang>.yml to load the locale data.
            locale_dir = getattr(mod, "LOCALE_DIR", os.path.join(LOCALE_ROOT, name.split(".")[-1]))
            locale_default_fname = os.path.join(locale_dir, "locale.yml")
            locale_fname = os.path.join(locale_dir, "locale.{}.yml".format(self.lang))

            self._locale_files[name] = []

            # Load the file.
            if os.path.exists(locale_fname):
                # Get the stat data.
                mtime = os.stat(locale_fname).st_mtime
                with open(locale_fname) as f:
                    self._locale_data = {**self._locale_data, **yaml.load(f)}
                # Add the filename to self._locale_files.
                self._locale_files[name].append((mtime, locale_fname, False))

            # Load the default data.
            if os.path.exists(locale_default_fname):
                mtime = os.stat(locale_default_fname).st_mtime
                with open(locale_default_fname) as f:
                    self._default_data = {**self._default_data, **yaml.load(f)}
                self._locale_files[name].append((mtime, locale_default_fname, True))
            else:
                logger.warning("Cannot load locale files for {}!".format(name))

    def _reload_locale(self):
        """
        Reloads the locale, if required.
        """
        for val in self._locale_files.values():
            if not val:
                continue
            for mtime, path, default in val:
                # Stat the file again.
                new_mtime = os.stat(path).st_mtime
                if new_mtime > mtime:
                    logger.info("Reloading locale file {}".format(path))
                    with open(path) as f:
                        if default:
                            self._default_data = {**self._default_data, **yaml.load(f)}
                        else:
                            self._locale_data = {**self._locale_data, **yaml.load(f)}

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

    def get(self, key):
        """
        Loads the key from the locale DB, but returns None if the key doesn't exist.
        """
        i = self[key]
        if i == key:
            return None
        else:
            return i


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
