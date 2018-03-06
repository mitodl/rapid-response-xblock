"""Just here to verify tests are running"""
import json
import os
import mock
import pytest

from ddt import data, ddt, unpack
from django.http.request import HttpRequest

from opaque_keys.edx.keys import UsageKey
from courseware.module_render import load_single_xblock
from xmodule.capa_module import CapaDescriptor
from xmodule.modulestore.django import modulestore

from rapid_response_xblock.logger import SubmissionRecorder
from rapid_response_xblock.models import RapidResponseSubmission
from tests.utils import (
    RuntimeEnabledTestCase,
    make_scope_ids,
)


BASE_DIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="function")
def example_event(request):
    """An example real event captured previously"""
    with open(os.path.join(BASE_DIR, "..", "test_data", "example_event.json")) as f:
        request.cls.example_event = json.load(f)
        yield


# pylint: disable=no-member
@pytest.mark.usefixtures("example_event")
@ddt
class TestEvents(RuntimeEnabledTestCase):
    """Tests for event capturing"""

    def setUp(self):
        super(TestEvents, self).setUp()
        self.scope_ids = make_scope_ids(self.runtime, self.descriptor)

    def get_problem(self):
        """
        Get the problem from the test course
        """
        course = self.course
        store = modulestore()
        problem = [
            item for item in store.get_items(course.course_id)
            if isinstance(item, CapaDescriptor)
        ][0]
        problem.bind_for_student(self.runtime, self.instructor)

        # Workaround handle_ajax binding strangeness
        request = HttpRequest()
        request.META['SERVER_NAME'] = 'mit.edu'
        request.META['SERVER_PORT'] = 1234
        return load_single_xblock(
            request=request,
            course_id=self.course_id.to_deprecated_string(),
            user_id=self.instructor.id,
            usage_key_string=problem.location.to_deprecated_string()
        )

    def test_publish(self):
        """
        Make sure the Logger is installed correctly
        """
        event_type = 'event_name'
        event_object = {'a': 'event'}

        # If this package is installed TRACKING_BACKENDS should
        # be configured to point to SubmissionRecorder. Since self.runtime is
        # an LmsModuleSystem, self.runtime.publish will send the event
        # to all registered loggers.
        block = self.course
        with mock.patch.object(
            SubmissionRecorder, 'send', autospec=True,
        ) as send_patch:
            self.runtime.publish(block, event_type, event_object)
        # If call_count is 0, make sure you installed
        # this package first to allow detection of the logger
        assert send_patch.call_count == 1
        event = send_patch.call_args[0][1]

        assert event['event_type'] == 'event_name'
        assert event['event_source'] == 'server'
        assert event['event'] == event_object
        assert event['context']['course_id'] == "{org}/{course}/{run}".format(
            org=block.location.org,
            course=block.location.course,
            run=block.location.run,
        )

    @data(*[
        ['choice_0', 'an incorrect answer'],
        ['choice_1', 'the correct answer'],
        ['choice_2', 'a different incorrect answer'],
    ])
    @unpack
    def test_problem(self, clicked_answer_id, expected_answer_text):
        """
        A problem should trigger an event which is captured
        """
        problem = self.get_problem()

        problem.handle_ajax('problem_check', {
            "input_i4x-SGAU-SGA101-problem-"
            "2582bbb68672426297e525b49a383eb8_2_1": clicked_answer_id
        })
        assert RapidResponseSubmission.objects.count() == 1
        obj = RapidResponseSubmission.objects.first()
        assert obj.user_id == self.instructor.id
        assert obj.course_id == self.course.course_id
        assert obj.problem_id.map_into_course(
            self.course.course_id
        ) == problem.location
        assert obj.answer_text == expected_answer_text
        assert obj.answer_id == clicked_answer_id

    def test_multiple_submissions(self):
        """
        Only the last submission should get captured
        """
        problem = self.get_problem()

        for answer in ('choice_0', 'choice_1', 'choice_2'):
            problem.handle_ajax('problem_check', {
                "input_i4x-SGAU-SGA101-problem-"
                "2582bbb68672426297e525b49a383eb8_2_1": answer
            })

        assert RapidResponseSubmission.objects.count() == 1
        obj = RapidResponseSubmission.objects.first()
        assert obj.user_id == self.instructor.id
        assert obj.course_id == self.course.course_id
        assert obj.problem_id.map_into_course(
            self.course.course_id
        ) == problem.location
        # Answer is the first one clicked
        assert obj.answer_text == 'a different incorrect answer'
        assert obj.answer_id == 'choice_2'  # the last one picked

    def assert_successful_event_parsing(self, example_event_data):
        """
        Assert what happens when the event is parsed
        """
        assert RapidResponseSubmission.objects.count() == 1
        obj = RapidResponseSubmission.objects.first()
        assert obj.user_id == example_event_data['context']['user_id']
        assert obj.problem_id == UsageKey.from_string(
            example_event_data['event']['problem_id']
        )
        # Answer is the first one clicked
        assert obj.answer_text == 'an incorrect answer'
        assert obj.answer_id == 'choice_0'
        assert obj.event == example_event_data

    def assert_unsuccessful_event_parsing(self):
        """
        Assert that no event was recorded
        """
        assert RapidResponseSubmission.objects.count() == 0

    def test_example_event(self):
        """
        Assert that the example event is a valid one
        """
        SubmissionRecorder().send(self.example_event)
        self.assert_successful_event_parsing(self.example_event)

    def test_missing_user(self):
        """
        If the user is missing no exception should be raised
        and no event should be recorded
        """
        del self.example_event['context']['user_id']
        SubmissionRecorder().send(self.example_event)
        self.assert_unsuccessful_event_parsing()

    def test_missing_problem_id(self):
        """
        If the problem id is missing no event should be recorded
        """
        del self.example_event['event']['problem_id']
        SubmissionRecorder().send(self.example_event)
        self.assert_unsuccessful_event_parsing()

    def test_extra_submission(self):
        """
        If there is more than one submission in the event,
        no event should be recorded
        """
        key = '2582bbb68672426297e525b49a383eb8_2_1'
        submission = self.example_event['event']['submission'][key]
        self.example_event['event']['submission']['second'] = submission
        SubmissionRecorder().send(self.example_event)
        self.assert_unsuccessful_event_parsing()

    def test_no_submission(self):
        """
        If there is more than one submission in the event,
        no event should be recorded
        """
        key = '2582bbb68672426297e525b49a383eb8_2_1'
        self.example_event['event']['submission'][key] = None
        SubmissionRecorder().send(self.example_event)
        self.assert_unsuccessful_event_parsing()

    def test_missing_answer_id(self):
        """
        If the answer id key is missing no event should be recorded
        """
        self.example_event['event']['answers'] = {}
        SubmissionRecorder().send(self.example_event)
        self.assert_unsuccessful_event_parsing()
