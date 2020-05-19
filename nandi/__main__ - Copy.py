import nltk
import datetime
import importlib
import re
from typing import Optional, List
from nltk.stem.lancaster import LancasterStemmer
from telegram import Message, Chat, Update, Bot, User
from telegram.ext import CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop, Dispatcher

from nandi import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID
stemmer = LancasterStemmer()

import numpy
import random
import json 
import requests
import time




URL = "https://api.telegram.org/bot{}/".format(TOKEN)

START_TEXT = """ Welcome, Im Nandi"""
print("Welcome, Im Nandi")


def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = get_json_from_url(url)
    return js

def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def send_message(text, chat_id):
    url = URL + "sendMessage?text={}&chat_id={}".format(text, chat_id)
    get_url(url)  

def echo_all(updates):
    for update in updates["result"]:
        try:
            text = update["message"]["text"]
            chat = update["message"]["chat"]["id"]
            send_message(text, chat)
        except Exception as e:
            print(e)

@run_async
def start(bot: Bot, update: Update, args: List[str]):
    update.effective_message.reply_text("Yo, whadup?")

def main():
    start_handler = CommandHandler("start", start, pass_args=True)
    dispatcher.add_handler(start_handler)

    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            echo_all(updates)
        time.sleep(0.5)

        
       if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="127.0.0.1",
                              port=PORT,
                              url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN,
                                    certificate=open(CERT_PATH, 'rb'))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Using long polling.")
        updater.start_polling(timeout=15, read_latency=4)

    updater.idle()

if __name__ == '__main__':
    main()