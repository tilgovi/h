# -*- coding: utf-8 -*-
"""Classes for validating data passed to the annotations API."""


class Error(Exception):

    """Base exception class for all exceptions raised by this module."""

    pass


class Annotation(object):

    """An annotation validator."""

    def __init__(self, data):
        self.data = data

    def validate(self):
        """Raise h.api.validation.Error if this annotation is invalid."""
        if 'document' in self.data and 'link' in self.data['document']:
            if not isinstance(self.data['document']['link'], list):
                raise Error("document.link must be an array")
