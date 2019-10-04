#!/usr/bin/env python
# coding=utf-8
# Filename: chatbot.py
# Author: Tamas Gal <tgal@km3net.de>
"""
The monitoring chatbot.

Usage:
    chatbot.py
    chatbot.py (-h | --help)

Options:
    -h --help   Show this screen.

"""
import re
import subprocess
import toml
from rocketchat_API.rocketchat import RocketChat
from RocketChatBot import RocketChatBot

URL = "https://chat.km3net.de"
CONFIG = "pipeline.toml"

with open(CONFIG, 'r') as fobj:
    config = toml.load(fobj)
    BOTNAME = config['Alerts']['botname']
    PASSWORD = config['Alerts']['password']
    CHANNEL = config['Alerts']['channel']


def get_channel_id(channel):
    rocket = RocketChat(BOTNAME, PASSWORD, server_url=URL)

    channels = rocket.channels_list().json()['channels']
    for c in channels:
        if c['name'] == channel:
            return c['_id']


CHANNEL_ID = get_channel_id(CHANNEL)


def run():
    bot = spawn_bot()
    register_handlers(bot)
    bot.run()


def spawn_bot():
    return RocketChatBot(BOTNAME, PASSWORD, URL)


def is_shifter(user):
    with open(CONFIG, 'r') as fobj:
        config = toml.load(fobj)
        return user in config['Alerts']['shifters']


def is_operator(user):
    with open(CONFIG, 'r') as fobj:
        config = toml.load(fobj)
        return user in config['Alerts']['operators']


def register_handlers(bot):
    def greet(msg, user, channel_id):
        if channel_id != CHANNEL_ID:
            print("skipping")
            return
        bot.send_message('hello @' + user, channel_id)

    def status(msg, user, channel_id):
        if channel_id != CHANNEL_ID:
            print("skipping")
            return
        if not is_shifter(user) and not is_operator(user):
            bot.send_message(
                "Sorry @{}, only operators and shifters are allowed to mess "
                "with me, sorry...".format(user), channel_id)
            return
        status = "```\n" + subprocess.check_output(
            ['supervisorctl', 'status']).decode('ascii') + "\n```"
        bot.send_message(status, channel_id)

    def supervisorctl(msg, user, channel_id):
        if channel_id != CHANNEL_ID:
            print("skipping")
            return
        if not is_shifter(user) and not is_operator(user):
            bot.send_message(
                "Sorry @{}, only operators and shifters are allowed to mess "
                "with me, sorry...".format(user), channel_id)
            return
        try:
            output = subprocess.check_output(
                ['supervisorctl'] + msg.split(),
                stderr=subprocess.STDOUT).decode('ascii')
        except subprocess.CalledProcessError as e:
            output = e.output.decode('ascii')
        print("supervisorctl output, called by {}:\n{}".format(user, output))
        bot.send_message(output, channel_id)

    def shifters(msg, user, channel_id):
        if channel_id != CHANNEL_ID:
            print("skipping")
            return
        if not is_operator(user):
            bot.send_message(
                "Sorry @{}, only operators are allowed to set shifters!".
                format(user), channel_id)
            return
        try:
            with open(CONFIG, 'r') as fobj:
                config = toml.load(fobj)
            shifters = msg[3:].strip()
            config['Alerts']['shifters'] = shifters
            with open(CONFIG, 'w') as fobj:
                toml.dump(config, fobj)
            msg = f'Alright, the new shifters are {shifters}, welcome!'
            print(msg)
            bot.send_message(msg, channel_id)
        except Exception as e:
            bot.send_message(f'something went horribly wrong... {e}',
                             channel_id)

    def help(msg, user, channel_id):
        if channel_id != CHANNEL_ID:
            print("skipping", channel_id)
            return
        help_str = f"""
        Hi @{user} I was built to take care of the monitoring alerts.
        Here is how you can use me:
        - `@{BOTNAME} shifters are cnorris and bspencer`
          -> set the new shifters who I may annoy with chat messages and
          emails.
        - `@{BOTNAME} status` -> show the status of the monitoring system
        - `@{BOTNAME} supervisorctl` -> take control over the monitoring system
        - `@{BOTNAME} help` -> show this message
        """

        bot.send_message(help_str, channel_id)

    handlers = [(['hello', 'hey', 'hi', 'ciao'], greet), (['status'], status),
                (['help'], help), (['shifters'], shifters),
                (['supervisorctl'], supervisorctl)]
    for trigger, handler in handlers:
        bot.add_dm_handler(trigger, handler)


def main():
    from docopt import docopt
    args = docopt(__doc__)

    run()


if __name__ == '__main__':
    main()
