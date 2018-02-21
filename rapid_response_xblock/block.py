"""Rapid-response functionality"""

import logging
from functools import wraps
from collections import namedtuple
import pkg_resources
from django.db import transaction
from django.template import Context, Template
from web_fragments.fragment import Fragment
from webob.response import Response

from xblock.core import XBlock, XBlockAside

from rapid_response_xblock.models import (
    RapidResponseBlockStatus,
    RapidResponseSubmission,
)

log = logging.getLogger(__name__)


def get_resource_bytes(path):
    """
    Helper method to get the unicode contents of a resource in this repo.

    Args:
        path (str): The path of the resource

    Returns:
        unicode: The unicode contents of the resource at the given path
    """
    resource_contents = pkg_resources.resource_string(__name__, path)
    return unicode(resource_contents)


def render_template(template_path, context=None):
    """
    Evaluate a template by resource path, applying the provided context.
    """
    context = context or {}
    template_str = get_resource_bytes(template_path)
    template = Template(template_str)
    return template.render(Context(context))


# TODO: Decide on how we're going to enable specific blocks for rapid response
def is_block_rapid_enabled(block):
    """
    Returns True if the given block is enabled for rapid response
    """
    return '[RAPID]' in block.display_name


def staff_only_handler_method(handler_method):
    """
    Wrapper that ensures a handler method is enabled for staff users only
    """
    @wraps(handler_method)
    def wrapper(aside_instance, *args, **kwargs):  # pylint: disable=missing-docstring
        if not aside_instance.is_staff():
            return Response(
                status=403,
                json_body="Unauthorized (staff only)"
            )
        return handler_method(aside_instance, *args, **kwargs)
    return wrapper


TemplateContext = namedtuple('TemplateContext', ['is_staff', 'is_open'])


class RapidResponseAside(XBlockAside):
    """
    XBlock aside that enables rapid-response functionality for an XBlock
    """
    @XBlockAside.aside_for('student_view')
    def student_view_aside(self, block, context=None):  # pylint: disable=unused-argument
        """
        Renders the aside contents for the student view
        """
        fragment = Fragment(u'')
        if not is_block_rapid_enabled(block):
            return fragment
        fragment.add_content(
            render_template(
                "static/html/rapid.html",
                self.get_initial_template_context()
            )
        )
        fragment.add_css(get_resource_bytes("static/css/rapid.css"))
        fragment.add_javascript(get_resource_bytes("static/js/src/rapid.js"))
        fragment.initialize_js("RapidResponseAsideInit")
        return fragment

    @XBlock.handler
    @staff_only_handler_method
    def toggle_block_open_status(self, request=None, suffix=None):  # pylint: disable=unused-argument
        """
        Toggles the open/closed status for the rapid-response-enabled block
        """
        with transaction.atomic():
            status, _ = RapidResponseBlockStatus.objects.get_or_create(
                usage_key=self.wrapped_block_usage_key,
                course_key=self.course_key
            )
            status.open = not bool(status.open)
            status.save()
        return Response(
            json_body=TemplateContext(
                is_open=status.open,
                is_staff=self.is_staff()
            )._asdict()
        )

    @property
    def wrapped_block_usage_key(self):
        """The usage_key for the block that is being wrapped by this aside"""
        return self.scope_ids.usage_id.usage_key

    @property
    def course_key(self):
        """The course_key for this aside"""
        return self.scope_ids.usage_id.course_key

    def is_staff(self):
        """Returns True if the user has staff permissions"""
        return getattr(self.runtime, 'user_is_staff', False)

    def get_initial_template_context(self):
        """
        Gets the template context object for the aside when it's first loaded
        """
        status = RapidResponseBlockStatus.objects.filter(
            usage_key=self.wrapped_block_usage_key,
            course_key=self.course_key
        ).first()
        is_open = False if not status else status.open
        return TemplateContext(
            is_open=is_open,
            is_staff=self.is_staff()
        )._asdict()

    @XBlock.handler
    @staff_only_handler_method
    def responses(self, request=None, suffix=None):  # pylint: disable=unused-argument
        """
        REST API for response information
        """
        status = RapidResponseBlockStatus.objects.filter(
            usage_key=self.wrapped_block_usage_key,
            course_key=self.course_key
        ).first()
        is_open = False if not status else status.open
        responses = list(
            RapidResponseSubmission.objects.filter(
                problem_id=self.wrapped_block_usage_key,
                course_id=self.course_key,
            ).values('id', 'answer_id', 'answer_text')
        )
        return Response(json_body={
            'is_open': is_open,
            'responses': responses,
        })
