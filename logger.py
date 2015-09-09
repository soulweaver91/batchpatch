#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Soulweaver'

from enum import Enum
import re
import colorama
import time


class LogLevel(Enum):
    debug = (1, 'DEBUG',  colorama.Fore.GREEN + colorama.Style.BRIGHT)
    notice = (2, 'NOTICE', colorama.Fore.WHITE + colorama.Style.NORMAL)
    warning = (3, 'WARN',   colorama.Fore.YELLOW + colorama.Style.BRIGHT)
    error = (4, 'ERROR',  colorama.Fore.RED + colorama.Style.NORMAL)
    silent = (5, '', '')

    def __init__(self, val, log_prefix, log_color):
        self.numval = val
        self.log_prefix = log_prefix
        self.log_color = log_color

    @classmethod
    def max_width(cls):
        return max([len(i.log_prefix) for i in cls])


class Logger:
    log_level = None

    def __init__(self, log_level=LogLevel.notice):
        self.log_level = log_level

    def log(self, msg, level):
        try:
            if level.numval >= self.log_level.numval:
                print(("{}[{}] {:>" + str(LogLevel.max_width()) + "}: {}{}").format(
                    level.log_color,
                    time.strftime('%Y-%m-%d %H:%M:%S'),
                    level.log_prefix,
                    msg,
                    colorama.Style.RESET_ALL
                ))
        except UnicodeEncodeError:
            self.log('A message sent to the logger could not be printed properly due to an encoding problem. '
                     'An ASCII-safe version of the original message follows.', LogLevel.warning)
            self.log(re.sub(r'[^\u0000-\u007f]', '?', msg), level)
