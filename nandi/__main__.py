import datetime
import importlib
import re

from typing import Optional, List
from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop, Dispatcher
from telegram.utils.helpers import escape_markdown
from nandi import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, CERT_PATH, PORT, URL, DB_URI, \
    ALLOW_EXCL
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from chatterbot.trainers import ChatterBotCorpusTrainer


from nandi.GroupSet import ALL_SETUP
from nandi.GroupSet.functions.chat_status import is_user_admin
from nandi.GroupSet.functions.misc import paginate_modules

# Create a new chat bot named nandi, with logic adapter bestmatch. and connecting database.
chatbot = ChatBot('Nandi',
    storage_adapter='chatterbot.storage.SQLStorageAdapter',
    logic_adapters=[
        {
            'import_path': 'chatterbot.logic.BestMatch'
        }
    ],
    database_uri=DB_URI)

# Create a new trainer for the chatbot
trainer1 = ChatterBotCorpusTrainer(chatbot)

# Train the chatbot based on the english corpus
trainer1.train(
    'chatterbot.corpus.english.ai',
    'chatterbot.corpus.english.botprofile',
    'chatterbot.corpus.english.computers',
    'chatterbot.corpus.english.conversations',
    'chatterbot.corpus.english.emotion',
    'chatterbot.corpus.english.food',
    'chatterbot.corpus.english.gossip',
    'chatterbot.corpus.english.greetings',
    'chatterbot.corpus.english.health',
    'chatterbot.corpus.english.history'
)

trainer2 = ListTrainer(chatbot)

trainer2.train([
        "Hello",
        "Hi",
        "Hi there!",
        "How  are you doing?",
        "I'm doing great. How are you?",
        "I'm good."
        "How are you?",
        "I'm fine",
        "Are you alright?",
        "Yes, i'm alright",
        "I need help",
        "Can i help you?",
        "Ohh",
        "Ya",
        "ok",
        "ok then",
        "That is good to hear",
        "Where do you live?",
        "I'm a bot, i can't live.",
        "Where you from?",
        "I'm a bot, built with python",
        "What is you name?",
        "I'm nandi",
        "Thank you.",
        "You are welcome.",
        "Tata",
        "Are you going, bye then.",
        "Bye",
        "Bye Bye",
        "What's your name?",
        "I'm nandi.",
        "Who are you?",
        "I'm nandi, an Ai chatbot.",
        "your name please?",
        "I'm Nandi",
        "Who made you?",
        "Sreerag is my creator",
        "Who created you?",
        "Sreerag is my creator"
])


#start text 
START_TEXT = """ Welcome {}, Im Nandi"""
#help text
HELP_STRINGS = """ 
Hey there! My name is *{}*.
I'm a modular group management bot with a few fun extras! Have a look at the following for an idea of some of \
the things I can help you with.
*Main* commands available:
 - /start: start the bot
 - /help: PM's you this message.
 {}
 Group Setting Options:
 """.format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n")

#logs on project on terminal 
print("Welcome Sreerag, Im Nandi")
#variable to store datas
IMPORTED = {}
HELPABLE = {}

#to load all the group setting optinons from the folder GroupSet
for setup_name in ALL_SETUP:
    imported_setup = importlib.import_module("nandi.GroupSet." + setup_name)
    if not hasattr(imported_setup, "__mod_name__"):
        imported_setup.__mod_name__ = imported_setup.__name__
        #loading module name to print on the help in a inlinekeyboard on tg.
    if not imported_setup.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_setup.__mod_name__.lower()] = imported_setup
    else:
        raise Exception("Can't have two modules with the same name! Please change one")
        #help command.
    if hasattr(imported_setup, "__help__") and imported_setup.__help__:
        HELPABLE[imported_setup.__mod_name__.lower()] = imported_setup


# send help to user to access the command on private message.
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard)
# /start command output for the usess. which will load help if the chat type is private.
@run_async
def start(bot: Bot, update: Update, args: List[str]):
    #chat type if only its a private telegram chat. 
    if update.effective_chat.type == "private":
        if update.effective_chat.type == "private":
            if len(args) >= 1:
                if args[0].lower() == "help":
                    send_help(update.effective_chat.id, HELP_STRINGS)
            else:
                #if /start command has less than 1 args then..
                first_name = update.effective_user.first_name
                update.effective_message.reply_text(START_TEXT.format(escape_markdown(first_name)), parse_mode=ParseMode.MARKDOWN)    
            
    else:
        #output message for /start in TG group.
        update.effective_message.reply_text("Hi im nandi!")


#help button pagination and navigation listener to show the preferred output.
@run_async
def help_button(bot: Bot, update: Update):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = "Here is the help for the *{}* module:\n".format(HELPABLE[module].__mod_name__) \
                   + HELPABLE[module].__help__
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="Back", callback_data="help_back")]]))

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, HELPABLE, "help")))

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, HELPABLE, "help")))

        elif back_match:
            query.message.reply_text(text=HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            print("Help button error")


@run_async
def get_help(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:

        update.effective_message.reply_text("Contact me in PM to get the list of possible commands.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="Help",
                                                                       url="t.me/{}?start=help".format(
                                                                           bot.username))]]))
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = "Here is the available help for the *{}* module:\n".format(HELPABLE[module].__mod_name__) \
               + HELPABLE[module].__help__
        send_help(chat.id, text, InlineKeyboardMarkup([[InlineKeyboardButton(text="Back", callback_data="help_back")]]))

    else:
        send_help(chat.id, HELP_STRINGS)


# text message handler 
def text_messages(bot: Bot, update: Update):
    try:        
        if update.effective_chat.type == "private":
            # Get current date and time
            currenttime = datetime.datetime.now()
     
            # Format datetime string
            ctime = currenttime.strftime("%H:%M:%S")
            # Get the text the user sent
            gettext = str(update.message.text)
            # this variable stores result of arithmatic  
            arthans = 0
            #to find whether it is the user used arithmatic operations.
            isarth = False
            #converting strings to the array.
            arrayinput = gettext.split(' ')
            #finding whether the array length is greater than 2
            if len(arrayinput) >= 2:
                leninput = len(arrayinput) #storing len to variable
                i = 0
                while (i + 2) < leninput:
                    if arrayinput[i].isnumeric(): #check first value is numeric then.
                        if arrayinput[i + 1] == '+' or arrayinput[i + 1] == '-' or arrayinput[i + 1] == '*' or arrayinput[i + 1] == '/':
                            arth = arrayinput[i + 1]
                            if arrayinput[i + 2].isnumeric():#check second value is arithmatic operation.
                                if arth == '+':
                                    isarth = True
                                    arthans = float(arrayinput[i]) + float(arrayinput [i + 2])
                                    bot_msg = "{} + {} = {}".format(arrayinput[i], arrayinput [i + 2], arthans)
                                elif arth == '-':
                                    isarth = True
                                    arthans = float(arrayinput[i]) - float(arrayinput [i + 2])
                                    bot_msg = "{} - {} = {}".format(arrayinput[i], arrayinput [i + 2], arthans)
                                elif arth == '*':
                                    isarth = True
                                    arthans = float(arrayinput[i]) * float(arrayinput [i + 2])
                                    bot_msg = "{} * {} = {}".format(arrayinput[i], arrayinput [i + 2], arthans)
                                elif arth == '/':
                                    isarth = True
                                    if int(arrayinput[i]) > 0: # checking the value is 0 or not.
                                        arthans = float(arrayinput[i]) / float(arrayinput [i + 2])
                                        bot_msg = "{} / {} = {}".format(arrayinput[i], arrayinput [i + 2], arthans)
                                    else:
                                        bot_msg = "oops, divide by number less than 1 is not possible for me"
                    else:
                        i = i + 1
                    i = i + 1 # incrementing
            if isarth == True:
                isarth = False
                print("true")
            #Greetings reply according to the time from the server.
            elif "good morning" in gettext.lower() or "good evening" in gettext.lower() or "good afternoon" in gettext.lower():
                if datetime.datetime.now().time() > datetime.time(0, 0, 0, 0) and datetime.datetime.now().time() < datetime.time(12, 30, 0, 0):
                    if "good morning" not in gettext.lower():
                        #checking whether the user giving correct greeting according to the time for the bot.
                        bot_msg = "My time is {}. it's Good morning".format(ctime)
                    else:
                        #reply greetings
                        bot_msg = str("Good morning") 
                elif datetime.datetime.now().time() > datetime.time(12, 30, 0, 0) and datetime.datetime.now().time() < datetime.time(17, 0, 0, 0):
                    if "good afternoon" not in gettext.lower():
                        #checking whether the user giving correct greeting according to the time for the bot.
                        bot_msg = "My time is {}. it's Good Afternoon".format(ctime)
                    else:
                        #reply greetings
                        bot_msg = str("Good Afternoon")
                else:
                    if "good evening" not in gettext.lower():
                        #checking whether the user giving correct greeting according to the time for the bot.
                        bot_msg = "My time is {}. it's Good Evening".format(ctime)
                    else:
                        #reply greetings
                        bot_msg = str("Good Evening")
            #if the greetings was good night then..
            elif "good night" in gettext.lower():
                if datetime.datetime.now().time() > datetime.time(20, 0, 0, 0) and datetime.datetime.now().time() < datetime.time(23, 58, 0, 0):
                    bot_msg = str("Good Night")
                else:
                    bot_msg = str("Are you going to sleep at this time?")
            else:
                #if all the above condition is wrong then the normal deep learning chat continues.
                bot_msg = str(chatbot.get_response(gettext))
            #reply message for last received messages.
            bot.sendMessage(chat_id=update.message.chat_id, 
            text=bot_msg)
            # logs of chat on the terminals
            print("YOU :", gettext)
            print("NANDI: ", bot_msg)
    #exceptional handling.
    except UnicodeEncodeError:
        bot.sendMessage(chat_id=update.message.chat_id, 
        text="Sorry, I can't get you.")
    except (KeyboardInterrupt, EOFError, SystemExit):
        bot.sendMessage(chat_id=update.message.chat_id, 
        text="Thank you. Im going to sleep now")

def main():

    #intializing all the handlers. with the functions
    start_handler = CommandHandler("start", start, pass_args=True)
    text_handler = MessageHandler(Filters.text, text_messages)
    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")

    #setting handler to the bot 
    #/start handler in telegram
    dispatcher.add_handler(start_handler)
    #/help handler in telegram bot
    dispatcher.add_handler(help_handler)
    #handler to listen all the message except command handlers
    dispatcher.add_handler(text_handler)
    #help module selection handler 
    dispatcher.add_handler(help_callback_handler)

    if WEBHOOK:
        #getting result in wwebhook if its enabled..
        updater.start_webhook(listen="127.0.0.1",
                              port=PORT,
                              url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN,
                                    certificate=open(CERT_PATH, 'rb'))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)
            #link to set default webhook..

    else:
        #delay in getting reply from bot
        updater.start_polling(timeout=15, read_latency=4)
    #to keep the bot active in listening to user. 
    updater.idle()

#main method calling.
if __name__ == '__main__':
    main()