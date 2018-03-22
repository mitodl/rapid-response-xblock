"""Tests for the rapid-response aside logic"""
from ddt import data, ddt, unpack
from mock import Mock, patch

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from opaque_keys.edx.keys import UsageKey
from opaque_keys.edx.locator import BlockUsageLocator
from openedx.core.lib.xblock_utils import get_aside_from_xblock
import pytest
from xmodule.modulestore.django import modulestore

from rapid_response_xblock.block import RapidResponseAside
from rapid_response_xblock.models import (
    RapidResponseBlockStatus,
    RapidResponseSubmission,
)
from tests.utils import (
    make_scope_ids,
    RuntimeEnabledTestCase,
)


@ddt
class RapidResponseAsideTests(RuntimeEnabledTestCase):
    """Tests for RapidResponseAside logic"""
    def setUp(self):
        super(RapidResponseAsideTests, self).setUp()
        self.aside_usage_key = UsageKey.from_string(
            "aside-usage-v2:block-v1$:SGAU+SGA101+2017_SGA+type@problem+block"
            "@2582bbb68672426297e525b49a383eb8::rapid_response_xblock"
        )
        self.scope_ids = make_scope_ids(self.runtime, self.aside_usage_key)
        self.aside_instance = RapidResponseAside(
            scope_ids=self.scope_ids,
            runtime=self.runtime
        )

    @data(*[
        [True, True],
        [False, False],
    ])
    @unpack
    def test_student_view(self, enabled_value, should_render_aside):
        """
        Test that the aside student view returns a fragment if the block is
        rapid-response-enabled
        """
        self.aside_instance.enabled = enabled_value
        fragment = self.aside_instance.student_view_aside(Mock())
        # If the block is enabled for rapid response, it should return a fragment with
        # non-empty content and should specify a JS initialization function
        assert bool(fragment.content) is should_render_aside
        assert (fragment.js_init_fn == 'RapidResponseAsideInit') is should_render_aside

    @data(True, False)
    def test_studio_view(self, enabled_value):
        """
        Test that the aside studio view returns a fragment
        """
        self.aside_instance.enabled = enabled_value
        fragment = self.aside_instance.studio_view_aside(Mock())
        assert 'data-enabled="{}"'.format(enabled_value) in fragment.content
        assert fragment.js_init_fn == 'RapidResponseAsideStudioInit'

    def test_toggle_block_open(self):
        """Test that toggle_block_open_status changes the status of a rapid response block"""
        block_status = RapidResponseBlockStatus.objects.create(
            problem_usage_key=self.aside_instance.wrapped_block_usage_key,
            course_key=self.aside_instance.course_key
        )
        assert block_status.open is False

        self.aside_instance.toggle_block_open_status(Mock())
        block_status.refresh_from_db()
        assert block_status.open is True

        self.aside_instance.toggle_block_open_status(Mock())
        block_status.refresh_from_db()
        assert block_status.open is False

    def test_toggle_block_enabled(self):
        """
        Test that toggle_block_enabled changes 'enabled' field value
        and returns an appropriate response
        """
        # Test that the default value is False
        assert self.aside_instance.enabled is False
        for expected_enabled_value in [True, False]:
            resp = self.aside_instance.toggle_block_enabled(Mock())
            assert self.aside_instance.enabled is expected_enabled_value
            assert resp.json['is_enabled'] == self.aside_instance.enabled

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
        with patch.object(self.aside_instance, 'is_staff', return_value=is_staff), self.patch_modulestore():
            resp = self.aside_instance.responses()
        assert resp.status_code == expected_status

    @data(True, False)
    def test_responses_open(self, is_open):
        """
        Test that the responses API shows whether the problem is open
        """
        RapidResponseBlockStatus.objects.create(
            problem_usage_key=self.aside_instance.wrapped_block_usage_key,
            course_key=self.aside_instance.course_key,
            open=is_open,
        )

        with self.patch_modulestore():
            resp = self.aside_instance.responses()
        assert resp.status_code == 200
        assert resp.json['is_open'] == is_open

    @pytest.mark.usefixtures("example_event")
    def test_responses(self):
        """
        Test that the responses API will show recorded events during the open period
        """
        # The testing modulestore expects deprecated keys for some reason
        course_id = self.aside_instance.course_key.replace(deprecated=True)
        problem_id = self.aside_instance.wrapped_block_usage_key
        # replace(deprecated=True) doesn't work for BlockUsageLocator
        problem_id = BlockUsageLocator(course_id, problem_id.block_type, problem_id.block_id, deprecated=True)

        # This problem is imported into the modulestore in the setup method.
        # It needs to be present there to allow the view function to look up problem data.
        request = RequestFactory().request()
        request.user = self.instructor
        request.session = request.environ
        problem = self.get_problem_by_id(problem_id)
        aside_block = get_aside_from_xblock(problem, self.aside_usage_key.aside_type)

        answer_id_counts = zip(range(3), range(2, 5))
        answer_texts = [
            'an incorrect answer',
            'the correct answer',
            'a different incorrect answer',
        ]
        answer_data = [
            {
                'answer_id': 'choice_{}'.format(i),
                'answer_text': answer_texts[i],
            }
            for i, _ in answer_id_counts
        ]
        counts = {'choice_{}'.format(ans_id): ans_count for ans_id, ans_count in answer_id_counts}

        for item in answer_data:
            for number in range(counts[item['answer_id']]):
                username = 'user_{}_{}'.format(number, item['answer_id'])
                email = 'user{}{}@email.com'.format(number, item['answer_id'])
                user = User.objects.create(
                    username=username,
                    email=email,
                )

                RapidResponseSubmission.objects.create(
                    # For some reason the modulestore looks for a deprecated course key
                    course_key=course_id,
                    problem_usage_key=problem_id,
                    user_id=user.id,
                    answer_id=item['answer_id'],
                    answer_text=item['answer_text'],
                    event={}
                )

        # create another submission which has a different problem id and won't be included in the results
        user = User.objects.create(
            username='user_missing',
            email='user@user.user'
        )
        RapidResponseSubmission.objects.create(
            course_key=course_id,
            problem_usage_key=UsageKey.from_string(unicode(problem_id) + "extra"),
            user_id=user.id,
            answer_id=answer_data[0]['answer_id'],
            answer_text=answer_data[0]['answer_text'],
            event={}
        )

        with self.patch_modulestore():
            resp = aside_block.responses()

        assert resp.status_code == 200
        assert resp.json['is_open'] is False

        assert resp.json['response_data'] == [{
            'count': counts[item['answer_id']],
            'answer_id': item['answer_id'],
            'answer_text': item['answer_text'],
        } for item in answer_data]
