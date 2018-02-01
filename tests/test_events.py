"""Just here to verify tests are running"""
from copy import deepcopy
import os
import shutil
import tempfile

from courseware.module_render import (
    get_module_system_for_user,
    load_single_xblock,
    make_track_function,
)
from courseware.tests.factories import StaffFactory
from ddt import data, ddt, unpack
from django.http.request import HttpRequest
import mock
from opaque_keys.edx.locator import CourseLocator
from opaque_keys.edx.keys import UsageKey
from student.tests.factories import AdminFactory
from xblock.fields import ScopeIds
from xmodule.capa_module import CapaDescriptor
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.xml_importer import import_course_from_xml  # lint-amnesty, pylint: disable=import-error

from rapid_response_xblock.logger import LoggerBackend
from rapid_response_xblock.models import ProblemCheckRapidResponse

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
EXAMPLE_EVENT = {
    'username': 'staff',
    'context': {
        'course_user_tags': {},
        'user_id': 9,
        'org_id': 'ReplaceStatic',
        'asides': {},
        'module': {
            'display_name': 'Multiple Choice',
            'usage_key': 'block-v1:ReplaceStatic+ReplaceStatic+2018_T1+type'
                         '@problem+block@2582bbb68672426297e525b49a383eb8'
        },
        'course_id': 'course-v1:ReplaceStatic+ReplaceStatic+2018_T1',
        'path': '/courses/course-v1:ReplaceStatic+ReplaceStatic+2018_T1/'
                'xblock/block-v1:ReplaceStatic+ReplaceStatic+2018_T1+type'
                '@problem+block@2582bbb68672426297e525b49a383eb8/handler/'
                'xmodule_handler/problem_check'
    },
    'event_source': 'server',
    'event_type': 'problem_check',
    'ip': '172.20.0.1',
    'agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:58.0) Gecko/20100101'
             ' Firefox/58.0',
    'page': 'x_module',
    'host': '5327e6d14aed',
    'referer': 'http://edx.devstack.lms:18000/courses/course-v1'
               ':ReplaceStatic+ReplaceStatic+2018_T1/courseware/'
               'chapter/sequential/1?activate_block_id=block-v1%3A'
               'ReplaceStatic%2BReplaceStatic%2B2018_T1%2Btype%40'
               'vertical%2Bblock%40vertical',
    'accept_language': 'en;q=1.0, en;q=1.0',
    'time': '2018-02-06T17:06:44.228Z',
    'event': {
        'submission': {
            '2582bbb68672426297e525b49a383eb8_2_1': {
                'input_type': 'choicegroup',
                'question': 'Add the question text, or prompt, here. This text is required.',
                'group_label': '',
                'response_type': 'multiplechoiceresponse',
                'answer': 'an incorrect answer',
                'variant': '',
                'correct': False,
            },
        },
        'success': 'incorrect',
        'grade': 0,
        'correct_map': {
            '2582bbb68672426297e525b49a383eb8_2_1': {
                'hint': '',
                'hintmode': None,
                'correctness': 'incorrect',
                'msg': '',
                'answervariable': None,
                'npoints': None,
                'queuestate': None
            }
        },
        'attempts': 20,
        'answers': {
            '2582bbb68672426297e525b49a383eb8_2_1': 'choice_0'
        },
        'state': {
            'correct_map': {
                '2582bbb68672426297e525b49a383eb8_2_1': {
                    'hint': '',
                    'hintmode': None,
                    'correctness': 'incorrect',
                    'msg': '',
                    'answervariable': None,
                    'npoints': None,
                    'queuestate': None}},
            'input_state': {
                '2582bbb68672426297e525b49a383eb8_2_1': {}
            },
            'has_saved_answers': False,
            'seed': 1,
            'done': True,
            'student_answers': {
                '2582bbb68672426297e525b49a383eb8_2_1': 'choice_2'
            }
        },
        'max_grade': 1,
        'problem_id': 'block-v1:ReplaceStatic+ReplaceStatic+2018_T1'
                      '+type@problem+block@2582bbb68672426297e525b49a383eb8'
    }
}


@ddt
class TestEvents(ModuleStoreTestCase):
    """Tests for event capturing"""

    def setUp(self):
        super(TestEvents, self).setUp()
        self.track_function = make_track_function(HttpRequest())
        self.student_data = mock.Mock()
        self.course = self.import_test_course()
        self.descriptor = ItemFactory(category="pure", parent=self.course)
        self.course_id = self.course.id
        self.instructor = StaffFactory.create(course_key=self.course_id)
        self.runtime = self.make_runtime()
        self.runtime.error_tracker = None
        self.scope_ids = self.make_scope_ids(self.runtime)
        self.staff = AdminFactory.create()

        self.course.bind_for_student(self.runtime, self.instructor)

    def make_scope_ids(self, runtime):
        """
        Make scope ids
        """
        block_type = 'fake'
        def_id = runtime.id_generator.create_definition(block_type)
        return ScopeIds(
            'user', block_type, def_id, self.descriptor.location
        )

    def make_runtime(self, **kwargs):
        """
        Make a runtime
        """
        runtime, _ = get_module_system_for_user(
            user=self.instructor,
            student_data=self.student_data,
            descriptor=self.descriptor,
            course_id=self.course.id,
            track_function=self.track_function,
            xqueue_callback_url_prefix=mock.Mock(),
            request_token=mock.Mock(),
            course=self.course,
            wrap_xmodule_display=False,
            **kwargs
        )
        runtime.get_policy = lambda _: {}

        return runtime

    def import_test_course(self):
        """
        Import the test course with the sga unit
        """
        # adapted from edx-platform/cms/djangoapps/contentstore/management/commands/tests/test_cleanup_assets.py
        input_dir = os.path.join(BASE_DIR, "..", "test_data")

        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir))

        xml_dir = os.path.join(temp_dir, "xml")
        shutil.copytree(input_dir, xml_dir)

        store = modulestore()
        courses = import_course_from_xml(
            store,
            'sga_user',
            xml_dir,
        )
        return courses[0]

    def get_problem(self):
        """
        Get the problem from the test course
        """
        course = self.course
        store = modulestore()
        problem = [item for item in store.get_items(course.course_id) if isinstance(item, CapaDescriptor)][0]
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
        # be configured to point to LoggerBackend. Since self.runtime is
        # an LmsModuleSystem, self.runtime.publish will send the event
        # to all registered loggers.
        block = self.course
        with mock.patch.object(
            LoggerBackend, 'send', autospec=True,
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
            "input_i4x-SGAU-SGA101-problem-2582bbb68672426297e525b49a383eb8_2_1": clicked_answer_id
        })
        assert ProblemCheckRapidResponse.objects.count() == 1
        obj = ProblemCheckRapidResponse.objects.first()
        assert obj.user_id == self.instructor.id
        assert obj.course_id == self.course.course_id
        assert obj.problem_id.map_into_course(self.course.course_id) == problem.location
        assert obj.answer_text == expected_answer_text
        assert obj.answer_id == clicked_answer_id

    def test_double_click(self):
        """
        Only the last click should get captured
        """
        problem = self.get_problem()

        for answer in ('choice_0', 'choice_1', 'choice_2'):
            problem.handle_ajax('problem_check', {
                "input_i4x-SGAU-SGA101-problem-2582bbb68672426297e525b49a383eb8_2_1": answer
            })

        assert ProblemCheckRapidResponse.objects.count() == 1
        obj = ProblemCheckRapidResponse.objects.first()
        assert obj.user_id == self.instructor.id
        assert obj.course_id == self.course.course_id
        assert obj.problem_id.map_into_course(self.course.course_id) == problem.location
        # Answer is the first one clicked
        assert obj.answer_text == 'a different incorrect answer'
        assert obj.answer_id == 'choice_2'  # the last one picked

    def assert_event_parsing(self, modification_func, success):
        """
        Assert what happens when the event is parsed
        """
        event_copy = deepcopy(EXAMPLE_EVENT)
        modification_func(event_copy)
        LoggerBackend().send(event_copy)
        if success:
            assert ProblemCheckRapidResponse.objects.count() == 1
            obj = ProblemCheckRapidResponse.objects.first()
            assert obj.user_id == event_copy['context']['user_id']
            assert obj.problem_id == UsageKey.from_string(event_copy['event']['problem_id'])
            # Answer is the first one clicked
            assert obj.answer_text == 'an incorrect answer'
            assert obj.answer_id == 'choice_0'
            assert obj.event == event_copy
        else:
            assert ProblemCheckRapidResponse.objects.count() == 0

    def test_example_event(self):
        """
        Assert that the example event is a valid one
        """
        self.assert_event_parsing(lambda _: None, True)

    def test_missing_user(self):
        """
        If the user is missing no exception should be raised
        and event should be recorded
        """
        def _func(copy):
            del copy['context']['user_id']

        self.assert_event_parsing(_func, False)

    def test_missing_problem_id(self):
        """
        If the problem id is missing no event should be recorded
        """
        def _func(copy):
            del copy['event']['problem_id']

        self.assert_event_parsing(_func, False)

    def test_extra_submission(self):
        """
        If there is more than one submission in the event, no event should be recorded
        """
        def _func(copy):
            key = '2582bbb68672426297e525b49a383eb8_2_1'
            submission = copy['event']['submission'][key]
            copy['event']['submission']['second'] = submission

        self.assert_event_parsing(_func, False)

    def test_no_submission(self):
        """
        If there is more than one submission in the event, no event should be recorded
        """
        def _func(copy):
            key = '2582bbb68672426297e525b49a383eb8_2_1'
            copy['event']['submission'][key] = None

        self.assert_event_parsing(_func, False)

    def test_missing_answer_id(self):
        """
        If the answer id key is missing no event should be recorded
        """
        def _func(copy):
            copy['event']['answers'] = {}

        self.assert_event_parsing(_func, False)
