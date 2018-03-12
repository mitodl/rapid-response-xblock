"""
Rapid Response block models
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
    problem_usage_key = UsageKeyField(db_index=True, max_length=255)
    course_key = CourseKeyField(db_index=True, max_length=255)
    answer_id = models.CharField(null=True, max_length=255)
    answer_text = models.CharField(null=True, max_length=4096)
    event = JSONField()

    def __str__(self):
        return (
            "user={user} problem_usage_key={problem_usage_key} course_key={course_key} "
            "answer_id={answer_id}".format(
                user=self.user,
                problem_usage_key=self.problem_usage_key,
                course_key=self.course_key,
                answer_id=self.answer_id,
            )
        )


@python_2_unicode_compatible
class RapidResponseBlockStatus(models.Model):
    """
    Indicates whether a rapid-response-enabled XBlock for a given course is "open" or not
    ("open" = set to collect student responses for the block in real time)
    """
    problem_usage_key = UsageKeyField(max_length=255, db_index=True)
    course_key = CourseKeyField(max_length=255, db_index=True)
    open = models.BooleanField(default=False, null=False)

    def __str__(self):
        return (
            "open={open} problem_usage_key={problem_usage_key} course_key={course_key}".format(
                open=self.open,
                problem_usage_key=self.problem_usage_key,
                course_key=self.course_key
            )
        )
