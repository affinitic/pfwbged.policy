# -*- coding: utf-8 -*-
"""Init and utils."""

import os
from zope.i18nmessageid import MessageFactory

_ = MessageFactory('pfwbged.policy')

POOL_SIZE = int(os.environ.get('GED_POOL_SIZE', 1000))


def initialize(context):
    """Initializer called when used as a Zope 2 product."""
