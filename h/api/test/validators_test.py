# -*- coding: utf-8 -*-
import pytest

from h.api import validators


def test_Annotation_raises_if_document_link_is_None():
    annotation = validators.Annotation(
        data={'document': {'link': None}})  # Invalid link.

    with pytest.raises(validators.Error):
        annotation.validate()
