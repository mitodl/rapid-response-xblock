"""Rapid-response functionality"""
import logging
from functools import wraps
from collections import namedtuple
import pkg_resources

from django.db import transaction
from django.db.models import Count
from django.template import Context, Template
from django.utils.translation import ugettext_lazy as _
from web_fragments.fragment import Fragment
from webob.response import Response
from xblock.core import XBlock, XBlockAside
from xblock.fields import Scope, Boolean
from xmodule.modulestore.django import modulestore

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
    return resource_contents.decode('utf-8')


def render_template(template_path, context=None):
    """
    Evaluate a template by resource path, applying the provided context.
    """
    context = context or {}
    template_str = get_resource_bytes(template_path)
    template = Template(template_str)
    return template.render(Context(context))


def staff_only(handler_method):
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


def is_block_rapid_compatible(block):
    return (
        len(block.problem_types) == 1 and
        'multiplechoiceresponse' in block.problem_types
    )


LmsTemplateContext = namedtuple('LmsTemplateContext', ['is_staff', 'is_open'])


class RapidResponseAside(XBlockAside):
    """
    XBlock aside that enables rapid-response functionality for an XBlock
    """
    enabled = Boolean(
        display_name=_("Rapid response enabled status"),
        default=False,
        scope=Scope.settings,
        help=_("Indicates whether or not a problem is enabled for rapid response")
    )

    @XBlockAside.aside_for('student_view')
    def student_view_aside(self, block, context=None):  # pylint: disable=unused-argument
        """
        Renders the aside contents for the student view
        """
        fragment = Fragment(u'')
        if not self.is_staff() or not self.enabled:
            return fragment
        fragment.add_content(
            render_template(
                "static/html/rapid.html",
                self.get_lms_template_context()
            )
        )
        fragment.add_css(get_resource_bytes("static/css/rapid.css"))
        fragment.add_javascript(get_resource_bytes("static/js/src/rapid.js"))
        fragment.add_javascript(get_resource_bytes("static/js/lib/d3.v4.min.js"))
        fragment.initialize_js("RapidResponseAsideInit")
        return fragment

    @XBlockAside.aside_for('studio_view')
    def studio_view_aside(self, block, context=None):  # pylint: disable=unused-argument
        """
        Renders the aside contents for the studio view
        """
        fragment = Fragment(u'')
        fragment.add_content(
            render_template(
                "static/html/rapid_studio.html",
                {'is_enabled': self.enabled}
            )
        )
        fragment.add_css(get_resource_bytes("static/css/rapid.css"))
        fragment.add_javascript(get_resource_bytes("static/js/src/rapid_studio.js"))
        fragment.initialize_js("RapidResponseAsideStudioInit")
        return fragment

    @XBlock.handler
    @staff_only
    def toggle_block_open_status(self, request=None, suffix=None):  # pylint: disable=unused-argument
        """
        Toggles the open/closed status for the rapid-response-enabled block
        """
        with transaction.atomic():
            status, _ = RapidResponseBlockStatus.objects.get_or_create(
                problem_usage_key=self.wrapped_block_usage_key,
                course_key=self.course_key
            )
            status.open = not bool(status.open)
            status.save()
        return Response(
            json_body=LmsTemplateContext(
                is_open=status.open,
                is_staff=self.is_staff()
            )._asdict()
        )

    @XBlock.handler
    def toggle_block_enabled(self, request=None, suffix=None):  # pylint: disable=unused-argument
        """
        Toggles the enabled status for the rapid-response-enabled block
        """
        self.enabled = not self.enabled
        return Response(json_body={'is_enabled': self.enabled})

    @XBlock.handler
    @staff_only
    def responses(self, request=None, suffix=None):  # pylint: disable=unused-argument
        """
        Returns student responses for rapid-response-enabled block
        """
        status = RapidResponseBlockStatus.objects.filter(
            problem_usage_key=self.wrapped_block_usage_key,
            course_key=self.course_key
        ).first()
        is_open = False if not status else status.open
        response_data = RapidResponseSubmission.objects.filter(
            problem_usage_key=self.wrapped_block_usage_key,
            course_key=self.course_key,
        ).values('answer_id').annotate(count=Count('answer_id'))
        response_counts = {item['answer_id']: item['count'] for item in response_data}

        problem = modulestore().get_item(self.wrapped_block_usage_key)
        tree = problem.lcp.tree
        choice_elements = tree.xpath('//choicegroup/choice')
        choices = [
            {
                'answer_id': choice.get("name"),
                'answer_text': choice.text,
                'count': response_counts.get(choice.get("name"), 0)
            } for choice in choice_elements
        ]

        return Response(json_body={
            'is_open': is_open,
            'response_data': choices,
        })

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

    def get_lms_template_context(self):
        """
        Gets the template context object for the aside when it's first loaded
        """
        status = RapidResponseBlockStatus.objects.filter(
            problem_usage_key=self.wrapped_block_usage_key,
            course_key=self.course_key
        ).first()
        is_open = False if not status else status.open
        return LmsTemplateContext(
            is_open=is_open,
            is_staff=self.is_staff()
        )._asdict()
