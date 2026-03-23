import pytest


def test_create_template():
    """
    Future shape: POST /job-templates creates a template with name, payload (sans signature fields),
    visibility=private; returns id + payload.
    """
    pytest.fail('not implemented')


def test_template_visibility():
    """
    Future shape: private templates are returned only to their creator;
    shared templates appear for all users.
    """
    pytest.fail('not implemented')
