"""
Models for storing rapid response grades
"""
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from jsonfield import JSONField
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import (
    CourseKeyField,
    UsageKeyField,
)


@python_2_unicode_compatible
class RapidResponseSubmission(TimeStampedModel):
    """
    Stores the student submissions for a problem that is
    configured with rapid response
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        db_index=True,
    )
    problem_id = UsageKeyField(db_index=True, max_length=255)
    course_id = CourseKeyField(db_index=True, max_length=255)
    answer_id = models.CharField(null=True, max_length=255)
    answer_text = models.CharField(null=True, max_length=4096)
    event = JSONField()

    def __str__(self):
        return (
            "user={user} problem_id={problem_id} "
            "answer_id={answer_id}".format(
                user=self.user,
                problem_id=self.qualified_problem_id,
                answer_id=self.answer_id,
            )
        )
