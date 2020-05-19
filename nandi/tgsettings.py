if not __name__.endswith("tgsettings"):
    import sys
    print("setup class"
          "values here. Doing that WILL backfire on you.\nBot quitting.", file=sys.stderr)
    quit(1)


#config variable class 
class Config(object):
    LOGGER = False

    # REQUIRED
    API_KEY = "YOUR KEY HERE"
    OWNER_ID = "YOUR ID HERE"  
    OWNER_USERNAME = "YOUR USERNAME HERE"

    # RECOMMENDED
    SQLALCHEMY_DATABASE_URI = 'sqldbtype://username:pw@hostname:port/db_name'  # needed for any database modules
    MESSAGE_DUMP = None 
    LOAD = []
    NO_LOAD = ['translation', 'rss', 'sed']
    WEBHOOK = False
    URL = None

    # OPTIONAL
    SUDO_USERS = []  # List of id's (not usernames) for users which have sudo access to the bot.
    DEL_CMDS = False  # Whether or not you should delete "blue text must click" commands
    CERT_PATH = None
    PORT = 5000
    WORKERS = 8  
    ALLOW_EXCL = False  # Allow ! commands as well as /
    
class Production(Config):
    LOGGER = False


class Development(Config):
    LOGGER = True