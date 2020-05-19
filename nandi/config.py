from nandi.tgsettings import Config


class Development(Config):
    OWNER_ID = 413824145  # my telegram ID
    OWNER_USERNAME = "sreeragvv"  # my telegram username
    API_KEY = "1104228815:AAF7amQm-sqDJZZWSfPNzxSY3xMD5-tTfMg"  # my api key, as provided by the botfather
    SQLALCHEMY_DATABASE_URI = 'postgresql://sree:0406@localhost:5432/nandi'  # sample db credentials
    MESSAGE_DUMP = '-1234567890' # some group chat that your bot is a member of
    USE_MESSAGE_DUMP = True
    SUDO_USERS = [413824145, 413824145]  # List of id's for users which have sudo access to the bot.
    LOAD = []
    NO_LOAD = ['translation']