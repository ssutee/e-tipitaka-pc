# -*- coding: utf-8 -*-
 
import os, sys, constants
import locale
import gettext
import wx
 
# Change this variable to your app name!
#  The translation files will be under
#  @LOCALE_DIR@/@LANGUAGE@/LC_MESSAGES/@APP_NAME@.mo
 
# This is ok for maemo. Not sure in a regular desktop:
LOCALE_DIR = os.path.join(constants.RESOURCES_DIR, 'locale') # .mo files will then be located in /locale/LANGUAGECODE/LC_MESSAGES/

# Now we need to choose the language. We will provide a list, and gettext
# will use the first translation available in the list
#
#  In maemo it is in the LANG environment variable
#  (on desktop is usually LANGUAGES)
DEFAULT_LANGUAGES = os.environ.get('LANG', '').split(':')
DEFAULT_LANGUAGES += ['th']
 
lc, encoding = locale.getdefaultlocale()

languages = []
if lc:
    languages += [lc]
 
# Concat all languages (env + default locale),
#  and here we have the languages and location of the translations
languages += DEFAULT_LANGUAGES

mo_location = LOCALE_DIR
 
# Lets tell those details to gettext
#  (nothing to change here for you)
gettext.install(True, localedir=None, unicode=1)
 
gettext.find(constants.APP_NAME, mo_location)
 
gettext.textdomain (constants.APP_NAME)
 
gettext.bind_textdomain_codeset(constants.APP_NAME, "UTF-8")

language = gettext.translation(constants.APP_NAME, mo_location, languages=['th'], fallback=True)
