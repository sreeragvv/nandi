import logging
import os
import sys

import telegram.ext as tg

ENV = bool(os.environ.get('ENV', False))

if ENV:
    TOKEN = os.environ.get('TOKEN', None)
    try:
        OWNER_ID = int(os.environ.get('OWNER_ID', None))
    except ValueError:
        raise Exception("Your OWNER_ID env variable is not a valid integer.")

    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", None)

    try:
        SUDO_USERS = set(int(x) for x in os.environ.get("SUDO_USERS", "").split())
    except ValueError:
        raise Exception("Your sudo users list does not contain valid integers.")

    DEL_CMDS = bool(os.environ.get('DEL_CMDS', False))
    
    WEBHOOK = bool(os.environ.get('WEBHOOK', False))
    DB_URI = os.environ.get('DATABASE_URL')
    LOAD = os.environ.get("LOAD", "").split()
    NO_LOAD = os.environ.get("NO_LOAD", "translation").split()
    URL = os.environ.get('URL', "")  # Does not contain token
    PORT = int(os.environ.get('PORT', 5000))
    CERT_PATH = os.environ.get("CERT_PATH")
    WORKERS = int(os.environ.get('WORKERS', 8))
    ALLOW_EXCL = os.environ.get('ALLOW_EXCL', False)
    
else:
    from nandi.config import Development as Config
    TOKEN = Config.API_KEY
    try:
        OWNER_ID = int(Config.OWNER_ID)
    except ValueError:
        raise Exception("Your OWNER_ID variable is not a valid integer.")
   
    OWNER_USERNAME = Config.OWNER_USERNAME

    try:
        SUDO_USERS = set(int(x) for x in Config.SUDO_USERS or [])
    except ValueError:
        raise Exception("Your sudo users list does not contain valid integers.")

    DEL_CMDS = Config.DEL_CMDS
    
    DB_URI = Config.SQLALCHEMY_DATABASE_URI
    LOAD = Config.LOAD
    NO_LOAD = Config.NO_LOAD
    
    WEBHOOK = Config.WEBHOOK
    URL = Config.URL
    PORT = Config.PORT
    CERT_PATH = Config.CERT_PATH 
    WORKERS = Config.WORKERS
    ALLOW_EXCL = Config.ALLOW_EXCL
    

updater = tg.Updater(TOKEN, workers=WORKERS)

dispatcher = updater.dispatcher

SUDO_USERS = list(SUDO_USERS)

# Load at end to ensure all prev variables have been set
from nandi.GroupSet.functions.handlers import CustomCommandHandler, CustomRegexHandler

# make sure the regex handler can take extra kwargs
tg.RegexHandler = CustomRegexHandler

if ALLOW_EXCL:
    tg.CommandHandler = CustomCommandHandler
