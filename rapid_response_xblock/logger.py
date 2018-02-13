"""
Capture events
"""
from __future__ import absolute_import
import logging

from django.db import transaction
from opaque_keys.edx.keys import UsageKey
from opaque_keys.edx.locator import CourseLocator
from track.backends import BaseBackend

from rapid_response_xblock.models import RapidResponseSubmission


log = logging.getLogger(__name__)


class SubmissionRecorder(BaseBackend):
    """
    Record events emitted by blocks.
    See TRACKING_BACKENDS for the configuration for this logger.
    For more information about events see:

    http://edx.readthedocs.io/projects/devdata/en/stable/
    internal_data_formats/tracking_logs.html
    """

    def send(self, event):
        # TODO: feature flag whitelisting valid problems
        # TODO: only capture when problem is open
        if event['event_type'] == 'problem_check':
            try:
                user_id = event['context']['user_id']
                problem_id = UsageKey.from_string(
                    event['event']['problem_id']
                )
                # usage_key.course_id may have a missing run
                # so we need to grab the course key separately
                course_key = CourseLocator.from_string(
                    event['context']['course_id']
                )

                # This is assuming the event only includes information
                # for one answer at a time
                submission = event['event']['submission']
                keys = list(submission.keys())
                if len(keys) != 1:
                    # Not sure if this case is possible
                    raise Exception(
                        "Expected only one answer in problem_check event"
                    )

                submission_key = keys[0]

                answer_text = submission[submission_key]['answer']
                answer_id = event['event']['answers'][submission_key]

                # Delete any older responses for the user
                with transaction.atomic():
                    ProblemCheckRapidResponse.objects.filter(
                        user_id=user_id,
                        course_id=course_key,
                        problem_id=problem_id,
                    ).delete()

                    ProblemCheckRapidResponse.objects.create(
                        user_id=user_id,
                        course_id=course_key,
                        problem_id=problem_id,
                        event=event,
                        answer_id=answer_id,
                        answer_text=answer_text,
                    )
            except:  # pylint: disable=bare-except
                log.exception("Unable to parse data for event: %s", event)
