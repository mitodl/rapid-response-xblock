"""Tests for the rapid-response aside logic"""
from collections import defaultdict
from ddt import data, ddt, unpack
from mock import Mock, patch

from django.contrib.auth.models import User
from opaque_keys.edx.keys import UsageKey
from opaque_keys.edx.locator import BlockUsageLocator
from openedx.core.lib.xblock_utils import get_aside_from_xblock
import pytest

from rapid_response_xblock.block import (
    get_choices_from_problem,
    get_counts_for_problem,
    get_runs,
    RapidResponseAside,
)
from rapid_response_xblock.models import (
    RapidResponseRun,
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
        usage_key = self.aside_instance.wrapped_block_usage_key
        course_key = self.aside_instance.course_key
        run = RapidResponseRun.objects.create(
            problem_usage_key=usage_key,
            course_key=course_key,
        )
        assert run.open is False

        self.aside_instance.toggle_block_open_status(Mock())
        assert RapidResponseRun.objects.count() == 2
        assert RapidResponseRun.objects.filter(
            problem_usage_key=usage_key,
            course_key=course_key,
            open=True
        ).exists() is True

        self.aside_instance.toggle_block_open_status(Mock())
        assert RapidResponseRun.objects.count() == 2
        assert RapidResponseRun.objects.filter(
            problem_usage_key=usage_key,
            course_key=course_key,
            open=True
        ).exists() is False

        self.aside_instance.toggle_block_open_status(Mock())
        assert RapidResponseRun.objects.count() == 3
        assert RapidResponseRun.objects.filter(
            problem_usage_key=usage_key,
            course_key=course_key,
            open=True
        ).exists() is True

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
        RapidResponseRun.objects.create(
            problem_usage_key=self.aside_instance.wrapped_block_usage_key,
            course_key=self.aside_instance.course_key,
            open=is_open,
        )

        with self.patch_modulestore():
            resp = self.aside_instance.responses()
        assert resp.status_code == 200
        assert resp.json['is_open'] == is_open

    @data(True, False)
    def test_responses(self, has_runs):
        """
        Test that the responses API will show recorded events during the open period
        """
        runs = [
            {
                'open': True
            }, {
                'open': False
            },
        ] if has_runs else []
        counts = 'counts'
        choices = 'choices'

        course_id = self.aside_instance.course_key
        problem_id = self.aside_instance.wrapped_block_usage_key

        with patch(
            'rapid_response_xblock.block.get_counts_for_problem', return_value=counts,
        ) as get_counts_mock, patch(
            'rapid_response_xblock.block.get_runs', return_value=runs
        ) as get_runs_mock, patch(
            'rapid_response_xblock.block.get_choices_from_problem', return_value=choices
        ) as get_choices_mock:
            resp = self.aside_instance.responses()

        assert resp.status_code == 200
        assert resp.json['is_open'] is has_runs

        assert resp.json['choices'] == choices
        assert resp.json['runs'] == runs
        assert resp.json['counts'] == counts

        get_runs_mock.assert_called_once_with(course_id, problem_id)
        get_choices_mock.assert_called_once_with(problem_id)
        get_counts_mock.assert_called_once_with(course_id, problem_id, runs, choices)

    def test_zero_runs(self):
        """
        If there are no runs there should still be valid answers
        """
        problem_id = self.aside_instance.wrapped_block_usage_key
        problem = self.get_problem_by_id(problem_id)
        aside_block = get_aside_from_xblock(problem, self.aside_usage_key.aside_type)

        with self.patch_modulestore():
            resp = aside_block.responses()

        assert resp.status_code == 200
        assert resp.json['is_open'] is False

        answers = [
            ('choice_0', 'an incorrect answer'),
            ('choice_1', 'the correct answer'),
            ('choice_2', 'a different incorrect answer'),
        ]

        assert resp.json['choices'] == [
            {
                'answer_id': answer_id,
                'answer_text': answer_text,
            } for answer_id, answer_text in answers
        ]
        assert resp.json['runs'] == []
        assert resp.json['counts'] == {
            answer_id: {} for answer_id, _ in answers
        }

    def test_get_choices_from_problem(self):
        """
        get_choices_from_problem should return a serialized representation of choices from a problem OLX
        """
        # The testing modulestore expects deprecated keys for some reason
        course_id = self.aside_instance.course_key.replace(deprecated=True)
        problem_id = self.aside_instance.wrapped_block_usage_key
        # replace(deprecated=True) doesn't work for BlockUsageLocator
        problem_id = BlockUsageLocator(course_id, problem_id.block_type, problem_id.block_id, deprecated=True)
        with self.patch_modulestore():
            assert get_choices_from_problem(problem_id) == [
                {'answer_id': 'choice_0', 'answer_text': 'an incorrect answer'},
                {'answer_id': 'choice_1', 'answer_text': 'the correct answer'},
                {'answer_id': 'choice_2', 'answer_text': 'a different incorrect answer'},
            ]

    def test_get_counts_for_problem(self):
        """
        get_counts_for_problem should return histogram count data for a problem
        """
        course_id = self.aside_instance.course_key
        problem_id = self.aside_instance.wrapped_block_usage_key

        run1 = RapidResponseRun.objects.create(
            course_key=course_id,
            problem_usage_key=problem_id,
            open=False
        )
        run2 = RapidResponseRun.objects.create(
            course_key=course_id,
            problem_usage_key=problem_id,
            open=True
        )
        choices = [
            {'answer_id': 'choice_0', 'answer_text': 'an incorrect answer'},
            {'answer_id': 'choice_1', 'answer_text': 'the correct answer'},
            {'answer_id': 'choice_2', 'answer_text': 'a different incorrect answer'},
        ]
        choices_lookup = {choice['answer_id']: choice['answer_text'] for choice in choices}
        counts = list(zip(
            [choices[i]['answer_id'] for i in range(3)],
            range(2, 5),
            [run1.id for _ in range(3)],
        )) + list(zip(
            [choices[i]['answer_id'] for i in range(3)],
            [3, 0, 7],
            [run2.id for _ in range(3)],
        ))

        counts_dict = defaultdict(dict)
        for answer_id, count, run_id in counts:
            counts_dict[answer_id][run_id] = count

        for answer_id, num_submissions, run_id in counts:
            answer_text = choices_lookup[answer_id]
            for number in range(num_submissions):
                username = 'user_{}_{}'.format(number, answer_id)
                email = 'user{}{}@email.com'.format(number, answer_id)
                user, _ = User.objects.get_or_create(
                    username=username,
                    email=email,
                )

                RapidResponseSubmission.objects.create(
                    # For some reason the modulestore looks for a deprecated course key
                    run=RapidResponseRun.objects.get(id=run_id),
                    user_id=user.id,
                    answer_id=answer_id,
                    answer_text=answer_text,
                    event={}
                )

        runs = get_runs(course_id, problem_id)

        assert get_counts_for_problem(course_id, problem_id, runs, choices) == counts_dict

    def test_get_runs(self):
        """
        get_runs should return a serialized representation of runs for a problem
        """
        course_id = self.aside_instance.course_key
        problem_id = self.aside_instance.wrapped_block_usage_key

        run1 = RapidResponseRun.objects.create(
            course_key=course_id,
            problem_usage_key=problem_id,
            open=False
        )
        run2 = RapidResponseRun.objects.create(
            course_key=course_id,
            problem_usage_key=problem_id,
            open=True
        )

        assert get_runs(course_id, problem_id) == [{
            'id': run.id,
            'created': run.created.isoformat(),
            'open': run.open,
        } for run in [run2, run1]]
