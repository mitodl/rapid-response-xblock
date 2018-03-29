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
    RapidResponseRun,
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
    """
    Returns true if rapid response can support this block
    """
    return (
        len(block.problem_types) == 1 and
        'multiplechoiceresponse' in block.problem_types
    )


def get_choices_from_problem(problem_key):
    """
    Look up choices from the problem XML

    Args:
        problem_key (UsageKey): The problem id

    Returns:
        list of dict: A list of answer id/answer text dicts, in the order the choices are listed in the XML
    """
    problem = modulestore().get_item(problem_key)
    tree = problem.lcp.tree
    choice_elements = tree.xpath('//choicegroup/choice')
    return [
        {
            'answer_id': choice.get('name'),
            'answer_text': choice.text,
        } for choice in choice_elements
    ]


def serialize_runs(runs):
    """
    Look up rapid response runs for a problem and return a serialized representation

    Args:
        runs (iterable of RapidResponseRun): A queryset of RapidResponseRun

    Returns:
        list of dict: a list of serialized runs
    """
    return [
        {
            'id': run.id,
            'created': run.created.isoformat(),
            'open': run.open,
        } for run in runs
    ]


def get_counts_for_problem(run_ids, choices):
    """
    Produce histogram count data for a given problem

    Args:
        run_ids (list of int): Serialized run id for the problem
        choices (list of dict): Serialized choices

    Returns:
        dict:
            A mapping of answer id => run id => count for that run
    """
    response_data = RapidResponseSubmission.objects.filter(
        run__id__in=run_ids
    ).values('answer_id', 'run').annotate(count=Count('answer_id'))
    # Make sure every answer has a count and convert to JSON serializable format
    response_counts = {(item['answer_id'], item['run']): item['count'] for item in response_data}

    return {
        choice['answer_id']: {
            run_id: response_counts.get((choice['answer_id'], run_id), 0)
            for run_id in run_ids
        } for choice in choices
    }


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
            run, is_new = RapidResponseRun.objects.get_or_create(
                problem_usage_key=self.wrapped_block_usage_key,
                course_key=self.course_key,
                open=True
            )
            if not is_new:
                run.open = False
                run.save()
        return Response(
            json_body=LmsTemplateContext(
                is_open=run.open,
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
        run_querysets = RapidResponseRun.objects.filter(
            problem_usage_key=self.wrapped_block_usage_key,
            course_key=self.course_key,
        ).order_by('-created')
        runs = serialize_runs(run_querysets)
        # Only the most recent run should possibly be open
        is_open = runs[0]['open'] if runs else False
        choices = get_choices_from_problem(self.wrapped_block_usage_key)
        counts = get_counts_for_problem([run['id'] for run in runs], choices)

        return Response(json_body={
            'is_open': is_open,
            'runs': runs,
            'choices': choices,
            'counts': counts,
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
        is_open = RapidResponseRun.objects.filter(
            problem_usage_key=self.wrapped_block_usage_key,
            course_key=self.course_key,
            open=True
        ).exists()
        return LmsTemplateContext(
            is_open=is_open,
            is_staff=self.is_staff()
        )._asdict()
