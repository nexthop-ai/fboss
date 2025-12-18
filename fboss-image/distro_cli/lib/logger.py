<<<<<<< HEAD
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
    def __init__(self, fmt='[%(elapsed).2fs] %(message)s'):
        super().__init__(fmt)
        self.start_time = time.time()

    def format(self, record):
        record.elapsed = time.time() - self.start_time
        return super().format(record)


def setup_logging(verbose=False):
    """Setup logging with elapsed time formatter."""
    logger = logging.getLogger('fboss-image')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers = []

    handler = logging.StreamHandler()
    formatter = ElapsedTimeFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
||||||| 449479b9e7
=======
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

    def __init__(self, fmt="[%(elapsed).2fs] %(message)s"):
        super().__init__(fmt)
        self.start_time = time.time()

    def format(self, record):
        record.elapsed = time.time() - self.start_time
        return super().format(record)


def setup_logging(verbose=False):
    """Setup logging with elapsed time formatter."""
    logger = logging.getLogger("fboss-image")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers = []

    handler = logging.StreamHandler()
    formatter = ElapsedTimeFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
>>>>>>> 2e3f5259e0e7fb4791864e3939bdd38a408f7699
