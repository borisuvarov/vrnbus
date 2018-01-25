from telegram import ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, Filters, MessageHandler, Updater

from helpers import parse_routes, natural_sort_key, grouper


class BusBot:
    def __init__(self, cds, user_settings, logger, debug):
        """Start the bot."""
        self.cds = cds
        self.user_settings = user_settings
        self.logger = logger
        # Create the EventHandler and pass it your bot's token.
        DEBUG_TOKEN = "524433920:AAFA-Qz4-ioogQ2WRviG_mD1lRzvrz7IPUc"
        VRNBUSBOT_TOKEN = "548203169:AAE68R3o9ghnoe2LMnOkiqoU5R-OdGY4YCQ"
        self.updater = Updater(DEBUG_TOKEN if debug else VRNBUSBOT_TOKEN)

        # Get the dispatcher to register handlers
        self.dp = self.updater.dispatcher

        # on different commands - answer in Telegram
        self.updater.dispatcher.add_handler(CommandHandler('settings', self.settings, pass_args=True))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.settings_button))
        self.dp.add_handler(CommandHandler("start", self.start))

        self.dp.add_handler(CommandHandler("help", self.helpcmd))
        self.dp.add_handler(CommandHandler("last", self.last_buses, pass_args=True))
        self.dp.add_handler(CommandHandler("nextbus", self.next_bus_handler, pass_args=True))
        #
        self.dp.add_handler(CommandHandler("stats", self.stats))
        #
        # # on noncommand i.e message - echo the message on Telegram
        self.dp.add_handler(MessageHandler(Filters.text, self.echo))
        self.dp.add_handler(MessageHandler(Filters.location, self.location))
        #
        # # log all errors
        self.dp.add_error_handler(self.error)

        # Start the Bot
        self.updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        # updater.idle()

    def error(self, bot, update, error):
        """Log Errors caused by Updates."""
        self.logger.warning('Update "%s" caused error "%s"', update, error)

    def start(self, bot, update):
        """Send a message when the command /help is issued."""
        user = update.message.from_user
        self.logger.info(f"start. User: {user};")

        location_keyboard = KeyboardButton(text="Местоположение", request_location=True)
        cancel_button = KeyboardButton(text="Отмена")
        custom_keyboard = [[location_keyboard, cancel_button]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)
        update.message.reply_text("/last номера маршрутов через пробел - последние остановки\n"
                                  "/nextbus имя остановки - ожидаемое время прибытия", reply_markup=reply_markup)

    def helpcmd(self, bot, update):
        """Send a message when the command /help is issued."""
        user = update.message.from_user
        self.logger.info(user)
        update.message.reply_text("""/last номера маршрутов через пробел - последние остановки
    /nextbus имя остановки - ожидаемое время прибытия""", reply_markup=ReplyKeyboardRemove())

    def last_buses(self, bot, update, args):
        """Send a message when the command /last is issued."""
        user = update.message.from_user
        self.logger.info(f"last_buses. User: {user}; {args}")
        (full_info, routes, filter) = parse_routes(args)
        response = self.cds.bus_request(full_info, routes, filter)
        self.logger.info(f"last_buses. User: {user}; Response {response}")
        update.message.reply_text(response)

    def get_buttons_routes(self, user_routes):
        # TODO: too many buttons
        routes_list = sorted(list(self.cds.routes_base.keys()), key=natural_sort_key)
        routes_groups = list(grouper(8, routes_list))
        route_btns = [[InlineKeyboardButton('Hide', callback_data='hide')],
                      [InlineKeyboardButton('All', callback_data='all'),
                       InlineKeyboardButton('None', callback_data='none')]
                      ] + [
                         [InlineKeyboardButton(f"{x}{'+' if x in user_routes else ''}", callback_data=x)
                          for x in group if x]
                         for group in routes_groups]
        keyboard = route_btns + [
        ]
        return keyboard

    def settings(self, bot, update, args):
        user_id = user = update.message.from_user.id
        settings = self.user_settings.get(user_id, [])
        settings_routes = parse_routes(args)
        if settings_routes:
            cmd = settings_routes[0]
            items = settings_routes[1:]
            if len(settings_routes) == 1 and cmd in ('all', 'none'):
                settings = []
            elif cmd == 'del':
                settings = [x for x in settings if x not in items]
            elif cmd == 'add':
                settings += [x for x in items if x in self.cds.routes_base.keys() and x not in settings]
            else:
                settings = [x for x in settings_routes if x in self.cds.routes_base.keys()]
            self.user_settings[user_id] = settings
            update.message.reply_text(f"Текущие маршруты для вывода: {' '.join(settings)}")
            return

        keyboard = self.get_buttons_routes(settings)
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Укажите маршруты для вывода:', reply_markup=reply_markup)

    def settings_button(self, bot, update):
        query = update.callback_query
        self.logger.info(query)
        user_id = query.message.chat_id
        settings = self.user_settings.get(user_id, [])
        key = query.data

        if key == 'all':
            settings = list(self.cds.routes_base.keys())
        elif key == 'none':
            settings = []
        elif key == 'hide':
            bot.edit_message_text(text=f"Текущие маршруты для вывода: {' '.join(settings) if settings else 'все доступные'}",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
            return
        else:
            if key in settings:
                settings.remove(key)
            else:
                settings.append(key)

        self.user_settings[user_id] = settings
        keyboard = self.get_buttons_routes(settings)
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.edit_message_text(text=f"Текущие маршруты для вывода: {' '.join(settings) if settings else 'все доступные'}",
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              reply_markup=reply_markup)

    def next_bus_handler(self, bot, update, args):
        """Send a message when the command /start is issued."""
        user = update.message.from_user
        self.logger.info(f"next_bus_handler. User: {user}; {args}")
        if not args:
            location_btn = KeyboardButton(text="Местоположение", request_location=True)
            cancel_btn = KeyboardButton(text="Отмена")
            custom_keyboard = [[location_btn, cancel_btn]]
            reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)
            update.message.reply_text("""Не указана остановка, попробуйте указать местоположение""",
                                      reply_markup=reply_markup)
            return

        settings = self.user_settings.get(user.id, [])
        response = self.cds.next_bus(tuple(args), tuple(settings))
        update.message.reply_text(response)

    def stats(self, bot, update):
        """Send a message when the command /stats is issued."""
        user = update.message.from_user
        self.logger.info(f"Stats. User: {user}")
        response = self.cds.get_all_buses()
        update.message.reply_text(response)


    def echo(self, bot, update):
        """Echo the user message."""
        update.message.reply_text(update.message.text, reply_markup=ReplyKeyboardRemove())


    def location(self, bot, update):
        user = update.message.from_user
        user_location = update.message.location
        self.logger.info("Location of %s: %f / %f", user.first_name, user_location.latitude,
                    user_location.longitude)
        matches = self.cds.matches_bus_stops(user_location.latitude, user_location.longitude)

        settings = self.user_settings.get(user.id, [])
        result = self.cds.next_bus_for_matches(matches, settings)
        self.logger.info(f"next_bus_for_matches {user} {result}")
        update.message.reply_text(result, reply_markup=ReplyKeyboardRemove())