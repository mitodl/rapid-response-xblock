"""Tests for the rapid-response aside logic"""
from ddt import data, ddt, unpack
from mock import Mock, patch

from opaque_keys.edx.keys import UsageKey
from opaque_keys.edx.locator import CourseLocator
import pytest

from rapid_response_xblock.block import RapidResponseAside
from rapid_response_xblock.logger import SubmissionRecorder
from rapid_response_xblock.models import (
    RapidResponseBlockStatus,
    RapidResponseSubmission,
)
from tests.utils import (
    dict_with,
    make_scope_ids,
    RuntimeEnabledTestCase,
)


# pylint: disable=no-member
@ddt
class RapidResponseAsideTests(RuntimeEnabledTestCase):
    """Tests for RapidResponseAside logic"""
    def setUp(self):
        super(RapidResponseAsideTests, self).setUp()
        self.aside_usage_key = UsageKey.from_string(
            "aside-usage-v2:block-v1$:ReplaceStatic+ReplaceStatic+2018_T1+type@problem+block"
            "@2582bbb68672426297e525b49a383eb8::rapid_response_xblock"
        )
        self.scope_ids = make_scope_ids(self.runtime, self.aside_usage_key)
        self.aside_instance = RapidResponseAside(
            scope_ids=self.scope_ids,
            runtime=self.runtime
        )

    @data(*[
        ['[RAPID]', True],
        ['block without rapid response', False],
    ])
    @unpack
    def test_student_view(self, display_name, should_render_aside):
        """
        Test that the aside student view returns a fragment if the block is
        rapid-response-enabled
        """
        mock_xblock = Mock(display_name=display_name)
        fragment = self.aside_instance.student_view_aside(mock_xblock)
        # If the block is enabled for rapid response, it should return a fragment with
        # non-empty content and should specify a JS initialization function
        assert bool(fragment.content) is should_render_aside
        assert (fragment.js_init_fn == 'RapidResponseAsideInit') is should_render_aside

    def test_toggle_block_open(self):
        """Test that toggle_block_open_status changes the status of a rapid response block"""
        block_status = RapidResponseBlockStatus.objects.create(
            usage_key=self.aside_instance.wrapped_block_usage_key,
            course_key=self.aside_instance.course_key
        )
        assert block_status.open is False

        self.aside_instance.toggle_block_open_status(Mock())
        block_status.refresh_from_db()
        assert block_status.open is True

        self.aside_instance.toggle_block_open_status(Mock())
        block_status.refresh_from_db()
        assert block_status.open is False

    @data(*[
        [True, 200],
        [False, 403]
    ])
    @unpack
    def test_toggle_block_open_staff_only(self, is_staff, expected_status):
        """Test that toggle_block_open_status is only enabled for staff"""
        with patch.object(self.aside_instance, 'is_staff', return_value=is_staff):
            resp = self.aside_instance.toggle_block_open_status()
        assert resp.status_code == expected_status

    @data(*[
        [True, 200],
        [False, 403]
    ])
    @unpack
    def test_responses_staff_only(self, is_staff, expected_status):
        """
        Test that only staff users should access the API
        """
        with patch.object(self.aside_instance, 'is_staff', return_value=is_staff):
            resp = self.aside_instance.responses()
        assert resp.status_code == expected_status

    @data(True, False)
    def test_responses_open(self, is_open):
        """
        Test that the responses API shows whether the problem is open
        """
        RapidResponseBlockStatus.objects.create(
            usage_key=self.aside_instance.wrapped_block_usage_key,
            course_key=self.aside_instance.course_key,
            open=is_open,
        )

        resp = self.aside_instance.responses()
        assert resp.status_code == 200
        assert resp.json['is_open'] == is_open

    @pytest.mark.usefixtures("example_event")
    def test_responses(self):
        """
        Test that the responses API will show recorded events during the open period
        """
        event = self.example_event
        event_before = dict_with(event, {'test_data': 'before'})
        event_during = dict_with(event, {'test_data': 'during'})
        event_after = dict_with(event, {'test_data': 'after'})

        problem_id = UsageKey.from_string(event['event']['problem_id'])
        course_id = CourseLocator.from_string(event['context']['course_id'])

        recorder = SubmissionRecorder()
        recorder.send(event_before)
        block_status = RapidResponseBlockStatus.objects.create(
            usage_key=problem_id,
            course_key=course_id,
            open=True,
        )
        recorder.send(event_during)
        block_status.open = False
        block_status.save()
        recorder.send(event_after)

        assert RapidResponseSubmission.objects.count() == 1
        submission = RapidResponseSubmission.objects.first()
        assert submission.event['test_data'] == event_during['test_data']

        resp = self.aside_instance.responses()
        assert resp.status_code == 200
        assert resp.json['is_open'] is False
        assert resp.json['responses'] == [{
            'id': submission.id,
            'answer_id': submission.answer_id,
            'answer_text': submission.answer_text,
        }]
