# -*- coding: utf-8 -*-
from h.accounts import models


class Error(Exception):

    """Base class for this package's custom exception classes."""

    pass


class NoSuchUserError(Error):

    """Exception raised when asking for a user that doesn't exist."""

    pass


def make_admin(username):
    """Make the given user an admin."""
    user = models.User.get_by_username(username)
    if user:
        user.admin = True
    else:
        raise NoSuchUserError


def make_staff(username):
    """Make the given user a staff member."""
    user = models.User.get_by_username(username)
    if user:
        user.staff = True
    else:
        raise NoSuchUserError


def includeme(config):
    """A local identity provider."""
    config.include('.schemas')
    config.include('.subscribers')
    config.include('.views')
