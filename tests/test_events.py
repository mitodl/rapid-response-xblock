"""Just here to verify tests are running"""

import mock

from courseware import module_render as render
from courseware.tests.factories import StaffFactory
from django.http.request import HttpRequest
from student.tests.factories import AdminFactory
from xblock.fields import ScopeIds
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory

from rapid_response_xblock.logger import LoggerBackend


class TestEvents(ModuleStoreTestCase):
    """Tests for event capturing"""

    def setUp(self):
        super(TestEvents, self).setUp()
        self.track_function = render.make_track_function(HttpRequest())
        self.course = CourseFactory.create(
            org='foo', number='bar', display_name='baz',
        )
        self.descriptor = ItemFactory(category="pure", parent=self.course)
        self.course_id = self.course.id
        self.instructor = StaffFactory.create(course_key=self.course_id)
        self.student_data = mock.Mock()
        self.runtime = self.make_runtime()
        self.scope_ids = self.make_scope_ids(self.runtime)
        self.staff = AdminFactory.create()

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
        runtime, _ = render.get_module_system_for_user(
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

    def make_block(self):
        """Make a block so we can capture events for it"""
        location = self.runtime.parse_xml_string('<problem />')
        modulestore().create_item(
            self.staff.username,
            location.course_key,
            location.block_type,
            location.block_id,
        )
        return self.runtime.get_block(location)

    def test_publish(self):
        """
        Make sure the Logger is installed correctly
        """
        event_type = 'event_name'
        event_object = {'a': 'event'}
        block = self.make_block()
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
