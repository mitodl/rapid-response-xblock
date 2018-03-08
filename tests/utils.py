"""Utility functions and classes for the rapid response test suite"""
import os
import shutil
import tempfile
from mock import Mock

from django.http.request import HttpRequest

from courseware.module_render import (
    get_module_system_for_user,
    make_track_function,
)
from courseware.tests.factories import StaffFactory
from student.tests.factories import AdminFactory
from xblock.fields import ScopeIds
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import ItemFactory
from xmodule.modulestore.xml_importer import import_course_from_xml


BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def make_scope_ids(runtime, usage_key):
    """
    Make scope ids

    Args:
        runtime (xblock.runtime.Runtime): A runtime
        usage_key (opaque_keys.edx.keys.UsageKey): A usage key

    Returns:
        xblock.fields.ScopeIds: A ScopeIds object for the block for usage_key
    """
    block_type = 'fake'
    def_id = runtime.id_generator.create_definition(block_type)
    return ScopeIds(
        'user', block_type, def_id, usage_key
    )


def combine_dicts(dictionary, extras):
    """
    Similar to {**dictionary, **extras} in Python 3

    Args:
        dictionary (dict): A dictionary
        extras (dict): Another dictionary

    Returns:
        dict: A new dictionary with both key and value pairs
    """
    ret = dict(dictionary)
    ret.update(extras)
    return ret


class RuntimeEnabledTestCase(ModuleStoreTestCase):
    """
    Test class that sets up a course, instructor, runtime, and other
    commonly-needed objects for testing XBlocks
    """
    def setUp(self):
        super(RuntimeEnabledTestCase, self).setUp()
        self.track_function = make_track_function(HttpRequest())
        self.student_data = Mock()
        self.course = self.import_test_course()
        self.descriptor = ItemFactory(category="pure", parent=self.course)
        self.course_id = self.course.id
        self.instructor = StaffFactory.create(course_key=self.course_id)
        self.runtime = self.make_runtime()
        self.runtime.error_tracker = None
        self.staff = AdminFactory.create()
        self.course.bind_for_student(self.runtime, self.instructor)

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
            xqueue_callback_url_prefix=Mock(),
            request_token=Mock(),
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
        # adapted from edx-platform/cms/djangoapps/contentstore/
        # management/commands/tests/test_cleanup_assets.py
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
