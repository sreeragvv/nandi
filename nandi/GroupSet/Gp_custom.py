import html
import re
from typing import Optional, List

import telegram.ext as tg
from telegram import Message, Chat, Update, Bot, User, ParseMode, User, MessageEntity, InlineKeyboardMarkup
from telegram import TelegramError
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import nandi.GroupSet.sql.welcome_sql as sqlw
import nandi.GroupSet.sql.locks_sql as sqll
import nandi.GroupSet.sql.blacklist_sql as sqlb


from nandi import dispatcher, OWNER_ID
from nandi.GroupSet.functions.chat_status import user_admin, can_delete, is_user_admin, user_not_admin, \
    bot_can_delete, is_bot_admin
#from nandi.GroupSet.functions.extraction import extract_text
from nandi.GroupSet.functions.misc import build_keyboard, revert_buttons, split_message
from nandi.GroupSet.functions.msg_types import get_welcome_type
from nandi.GroupSet.functions.string_handling import markdown_parser, \
    escape_invalid_curly_brackets

from nandi.GroupSet.disable import DisableAbleCommandHandler

from nandi.GroupSet.sql import users_sql

BLACKLIST_GROUP = 11

BASE_BLACKLIST_STRING = "<b>blacklisted</b> words:\n"

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']
LOCK_TYPES = {'sticker': Filters.sticker,
              'audio': Filters.audio,
              'voice': Filters.voice,
              'document': Filters.document & ~Filters.animation,
              'video': Filters.video,
              'videonote': Filters.video_note,
              'contact': Filters.contact,
              'photo': Filters.photo,
              'gif': Filters.animation,
              'url': Filters.entity(MessageEntity.URL) | Filters.caption_entity(MessageEntity.URL),
              'bots': Filters.status_update.new_chat_members,
              'forward': Filters.forwarded,
              'game': Filters.game,
              'location': Filters.location,
              }
GIF = Filters.animation
OTHER = Filters.game | Filters.sticker | GIF
MEDIA = Filters.audio | Filters.document | Filters.video | Filters.video_note | Filters.voice | Filters.photo
MESSAGES = Filters.text | Filters.contact | Filters.location | Filters.venue | Filters.command | MEDIA | OTHER
PREVIEWS = Filters.entity("url")

RESTRICTION_TYPES = {'messages': MESSAGES,
                     'media': MEDIA,
                     'other': OTHER,
                     # 'previews': PREVIEWS, # NOTE: this has been removed cos its useless atm.
                     'all': Filters.all}

PERM_GROUP = 1
REST_GROUP = 2

# do not async
def send(update, message, keyboard, backup_message):
    try:
        msg = update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except IndexError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nNote: the current message was "
                                                                  "invalid due to markdown issues. Could be "
                                                                  "due to the user's name."),
                                                  parse_mode=ParseMode.MARKDOWN)
    except KeyError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nNote: the current message is "
                                                                  "invalid due to an issue with some misplaced "
                                                                  "curly brackets. Please update"),
                                                  parse_mode=ParseMode.MARKDOWN)
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNote: the current message has an invalid url "
                                                                      "in one of its buttons. Please update."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNote: the current message has buttons which "
                                                                      "use url protocols that are unsupported by "
                                                                      "telegram. Please update."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNote: the current message has some bad urls. "
                                                                      "Please update."),
                                                      parse_mode=ParseMode.MARKDOWN)
        else:
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNote: An error occured when sending the "
                                                                      "custom message. Please update."),
                                                      parse_mode=ParseMode.MARKDOWN)
    return msg


@run_async
def new_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    should_welc = sqlw.get_gp_enter_pref(chat.id)
    if should_welc:
        sent = None
        new_members = update.effective_message.new_chat_members
        for new_mem in new_members:
            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text("My Boss is here in the chat!")
                continue

            # Don't welcome yourself
            elif new_mem.id == bot.id:
                continue

            else:
                
                first_name = new_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.

                res = sqlw.DEFAULT_WELCOME.format(first=first_name)
                keyb = []

                keyboard = InlineKeyboardMarkup(keyb)

                sent = send(update, res, keyboard,
                            sqlw.DEFAULT_WELCOME.format(first=first_name))  # type: Optional[Message]

@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    should_goodbye = sqlw.get_gp_exit_pref(chat.id)
    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        if left_mem:
            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("Bye Sreerag. I will be here.")
                return
            else:
                first_name = left_mem.first_name or "PersonWithNoName"  # edge case of empty name - occurs for some bugs.
                res = sqlw.DEFAULT_GOODBYE
                keyb = []

                keyboard = InlineKeyboardMarkup(keyb)

                send(update, res, keyboard, sqlw.DEFAULT_GOODBYE)


@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    # if no args, show current replies.
    if len(args) == 0 or args[0].lower() == "noformat":
        noformat = args and args[0].lower() == "noformat"
        pref = sqlw.get_gp_enter_pref(chat.id)
        update.effective_message.reply_text(
            "This chat has it's welcome setting set to: `{}`.\n*The welcome message "
            "(not filling the {{}}) is:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)
        keyb = build_keyboard(buttons)
        keyboard = InlineKeyboardMarkup(keyb)
        send(update, welcome_m, keyboard, sqlw.DEFAULT_WELCOME)
    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sqlw.set_gp_enter_preference(str(chat.id), True)
            update.effective_message.reply_text("The Welcome message has been Set!")

        elif args[0].lower() in ("off", "no"):
            sqlw.set_gp_enter_preference(str(chat.id), False)
            update.effective_message.reply_text("The Welcome message has been Unset!")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("Use arguments 'on/yes' or 'off/no' only!")


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]

    if len(args) == 0 or args[0] == "noformat":
        noformat = args and args[0] == "noformat"
        pref = sqlw.get_gp_exit_pref(chat.id)
        update.effective_message.reply_text(
            "This chat has it's goodbye setting set to: `{}`.\n*The goodbye  message "
            "(not filling the {{}}) is:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)       
        keyb = build_keyboard(buttons)
        keyboard = InlineKeyboardMarkup(keyb)
        send(update, goodbye_m, keyboard, sqlw.DEFAULT_GOODBYE)
    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sqlw.set_gp_exit_preference(str(chat.id), True)
            update.effective_message.reply_text("The GoodBye message has been Set!")

        elif args[0].lower() in ("off", "no"):
            sqlw.set_gp_exit_preference(str(chat.id), False)
            update.effective_message.reply_text("The GoodBye message has been Unset!")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("Use arguments 'on/yes' or 'off/no' only!!")




#method to extract messages
def extract_text(message) -> str:
    return message.text or message.caption or (message.sticker.emoji if message.sticker else None)

@run_async
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]

    all_blacklisted = sqlb.get_chat_blacklist(chat.id)

    filter_list = BASE_BLACKLIST_STRING

    if len(args) > 0 and args[0].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if text == BASE_BLACKLIST_STRING:
            msg.reply_text("There are no blacklisted messages here!")
            return
        msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blacklist(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        for trigger in to_blacklist:
            sqlb.add_to_blacklist(chat.id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text("Added <code>{}</code> to the blacklist!".format(html.escape(to_blacklist[0])),
                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "Added <code>{}</code> triggers to the blacklist.".format(len(to_blacklist)), parse_mode=ParseMode.HTML)

    else:
        msg.reply_text("Tell me which words you would like to add to the blacklist.")


@run_async
@user_admin
def unblacklist(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        successful = 0
        for trigger in to_unblacklist:
            success = sqlb.rm_from_blacklist(chat.id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text("Removed <code>{}</code> from the blacklist!".format(html.escape(to_unblacklist[0])),
                               parse_mode=ParseMode.HTML)
            else:
                msg.reply_text("This isn't a blacklisted trigger...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(
                "Removed <code>{}</code> triggers from the blacklist.".format(
                    successful), parse_mode=ParseMode.HTML)

        elif not successful:
            msg.reply_text(
                "None of these triggers exist, so they weren't removed.".format(
                    successful, len(to_unblacklist) - successful), parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "Removed <code>{}</code> triggers from the blacklist. {} did not exist, "
                "so were not removed.".format(successful, len(to_unblacklist) - successful),
                parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Tell me which words you would like to remove from the blacklist.")


@run_async
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sqlb.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error while deleting blacklist message.")
            break



class CustomCommandHandler(tg.CommandHandler):
    def __init__(self, command, callback, **kwargs):
        super().__init__(command, callback, **kwargs)

    def check_update(self, update):
        return super().check_update(update) and not (
                sqll.is_restr_locked(update.effective_chat.id, 'messages') and not is_user_admin(update.effective_chat,
                                                                                                update.effective_user.id))


tg.CommandHandler = CustomCommandHandler


# NOT ASYNC
def restr_members(bot, chat_id, members, messages=False, media=False, other=False, previews=False):
    for mem in members:
        if mem.user in SUDO_USERS:
            pass
        try:
            bot.restrict_chat_member(chat_id, mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


# NOT ASYNC
def unrestr_members(bot, chat_id, members, messages=True, media=True, other=True, previews=True):
    for mem in members:
        try:
            bot.restrict_chat_member(chat_id, mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


@run_async
def locktypes(bot: Bot, update: Update):
    update.effective_message.reply_text("\n - ".join(["Locks: "] + list(LOCK_TYPES) + list(RESTRICTION_TYPES)))


@user_admin
@bot_can_delete
def lock(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    if can_delete(chat, bot.id):
        if len(args) >= 1:
            if args[0] in LOCK_TYPES:
                sqll.update_lock(chat.id, args[0], locked=True)
                message.reply_text("Locked {} messages for all non-admins!".format(args[0]))

                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[0])

            elif args[0] in RESTRICTION_TYPES:
                sqll.update_restriction(chat.id, args[0], locked=True)
                if args[0] == "previews":
                    members = users_sqll.get_chat_members(str(chat.id))
                    restr_members(bot, chat.id, members, messages=True, media=True, other=True)

                message.reply_text("Locked {} for all non-admins!".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[0])

            else:
                message.reply_text("What are you trying to lock...? Try /locktypes for the list of lockables")

    else:
        message.reply_text("I'm not an administrator, or haven't got delete rights.")

    return ""


@run_async
@user_admin
def unlock(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    if is_user_admin(chat, message.from_user.id):
        if len(args) >= 1:
            if args[0] in LOCK_TYPES:
                sqll.update_lock(chat.id, args[0], locked=False)
                message.reply_text("Unlocked {} for everyone!".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[0])

            elif args[0] in RESTRICTION_TYPES:
                sqll.update_restriction(chat.id, args[0], locked=False)
                message.reply_text("Unlocked {} for everyone!".format(args[0]))

                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[0])
            else:
                message.reply_text("What are you trying to unlock...? Try /locktypes for the list of lockables")

        else:
            bot.sendMessage(chat.id, "What are you trying to unlock...?")

    return ""


@run_async
@user_not_admin
def del_lockables(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    for lockable, filter in LOCK_TYPES.items():
        if filter(message) and sqll.is_locked(chat.id, lockable) and can_delete(chat, bot.id):
            if lockable == "bots":
                new_members = update.effective_message.new_chat_members
                for new_mem in new_members:
                    if new_mem.is_bot:
                        if not is_bot_admin(chat, bot.id):
                            message.reply_text("I see a bot, and I've been told to stop them joining... "
                                               "but I'm not admin!")
                            return

                        chat.kick_member(new_mem.id)
                        message.reply_text("Only admins are allowed to add bots to this chat! Get outta here.")
            else:
                try:
                    message.delete()
                except BadRequest as excp:
                    if excp.message == "Message to delete not found":
                        pass
                    else:
                        LOGGER.exception("ERROR in lockables")

            break


@run_async
@user_not_admin
def rest_handler(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    for restriction, filter in RESTRICTION_TYPES.items():
        if filter(msg) and sqll.is_restr_locked(chat.id, restriction) and can_delete(chat, bot.id):
            try:
                msg.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("ERROR in restrictions")
            break


def build_lock_message(chat_id):
    locks = sqll.get_locks(chat_id)
    restr = sqll.get_restr(chat_id)
    if not (locks or restr):
        res = "There are no current locks in this chat."
    else:
        res = "These are the locks in this chat:"
        if locks:
            res += "\n - sticker = `{}`" \
                   "\n - audio = `{}`" \
                   "\n - voice = `{}`" \
                   "\n - document = `{}`" \
                   "\n - video = `{}`" \
                   "\n - videonote = `{}`" \
                   "\n - contact = `{}`" \
                   "\n - photo = `{}`" \
                   "\n - gif = `{}`" \
                   "\n - url = `{}`" \
                   "\n - bots = `{}`" \
                   "\n - forward = `{}`" \
                   "\n - game = `{}`" \
                   "\n - location = `{}`".format(locks.sticker, locks.audio, locks.voice, locks.document,
                                                 locks.video, locks.videonote, locks.contact, locks.photo, locks.gif, locks.url,
                                                 locks.bots, locks.forward, locks.game, locks.location)
        if restr:
            res += "\n - messages = `{}`" \
                   "\n - media = `{}`" \
                   "\n - other = `{}`" \
                   "\n - previews = `{}`" \
                   "\n - all = `{}`".format(restr.messages, restr.media, restr.other, restr.preview,
                                            all([restr.messages, restr.media, restr.other, restr.preview]))
    return res


@run_async
@user_admin
def list_locks(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    res = build_lock_message(chat.id)

    update.effective_message.reply_text(res, parse_mode=ParseMode.MARKDOWN)


__help__ = """
- /locktypes: a list of possible locktypes
- /blacklist: View the current blacklisted words.

*Group Admin Commands:*
 - /welcome <on/off>: enable/disable welcome messages.
 - /goodbye <on/off>: enable/disable good bye messages.
 - /lock <type>: lock items of a certain type (not available in private)
 - /unlock <type>: unlock items of a certain type (not available in private)
 - /locks: the current list of locks in this chat.
 - /addblacklist <triggers>: Add a trigger to the blacklist. Each line is considered one trigger, so using different \
lines will allow you to add multiple triggers.
 - /unblacklist <triggers>: Remove triggers from the blacklist. Same newline logic applies here, so you can remove \
multiple triggers at once.
 - /rmblacklist <triggers>: Same as above.
 
"""

__mod_name__ = "Group Settings"

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, pass_args=True, filters=Filters.group)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, pass_args=True, filters=Filters.group)
LOCKTYPES_HANDLER = DisableAbleCommandHandler("locktypes", locktypes)
LOCK_HANDLER = CommandHandler("lock", lock, pass_args=True, filters=Filters.group)
UNLOCK_HANDLER = CommandHandler("unlock", unlock, pass_args=True, filters=Filters.group)
LOCKED_HANDLER = CommandHandler("locks", list_locks, filters=Filters.group)
BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist", blacklist, filters=Filters.group, pass_args=True, admin_ok=True)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist, filters=Filters.group)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"], unblacklist, filters=Filters.group)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group, del_blacklist, edited_updates=True)



dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)

dispatcher.add_handler(LOCK_HANDLER)
dispatcher.add_handler(UNLOCK_HANDLER)
dispatcher.add_handler(LOCKTYPES_HANDLER)
dispatcher.add_handler(LOCKED_HANDLER)
dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)

dispatcher.add_handler(MessageHandler(Filters.all & Filters.group, del_lockables), PERM_GROUP)
dispatcher.add_handler(MessageHandler(Filters.all & Filters.group, rest_handler), REST_GROUP)
