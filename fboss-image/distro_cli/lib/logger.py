# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Logging utilities for fboss-image CLI."""

import logging
import time


class ElapsedTimeFormatter(logging.Formatter):
    """Formatter that shows elapsed time since CLI start."""

    def __init__(self, fmt="[%(current_time)s] [%(elapsed).2fs] [%(levelname)s] %(message)s"):
        super().__init__(fmt)
        self.start_time = time.time()

    def format(self, record):
        record.elapsed = time.time() - self.start_time
        record.current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        return super().format(record)


def setup_logging(verbose=False):
    """Setup logging with elapsed time formatter.

<<<<<<< HEAD
    Configures the root logger so all child loggers inherit the configuration.
    """
    # Configure the root logger so all loggers inherit this configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    root_logger.handlers = []
||||||| c17655f139
    """Setup logging with elapsed time formatter."""
    logger = logging.getLogger("fboss-image")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers = []
=======
    Configures the 'distro_cli' logger, which is the parent of all module
    loggers created via logging.getLogger(__name__) throughout the package.
    """
    logger = logging.getLogger("distro_cli")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers = []
>>>>>>> 84406ca706433e04c579c49376acbd3a257dfc4b

    handler = logging.StreamHandler()
    formatter = ElapsedTimeFormatter()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Also return a named logger for backward compatibility
    return logging.getLogger("fboss-image")
