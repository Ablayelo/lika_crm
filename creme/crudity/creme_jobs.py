# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _, ugettext, ungettext

from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import JobResult


CremeUser = get_user_model()


class _CruditySynchronizeType(JobType):
    id           = JobType.generate_id('crudity', 'synchronization')
    verbose_name = _(u'Synchronize externals data sent to Creme')
    periodic     = JobType.PERIODIC

    def _execute(self, job):
        try:
            user = CremeUser.objects.get(pk=job.data['user'])
        except CremeUser.DoesNotExist:
            JobResult.objects.create(job=job,
                                     messages=[ugettext(u"The configured default user is invalid. "
                                                        u"Edit the job's configuration to fix it."
                                                       ),
                                              ],
                                    )

            user = CremeUser.objects.get_admin()

        from . import registry

        count = len(registry.crudity_registry.fetch(user))
        JobResult.objects.create(job=job,
                                 messages=[ungettext(u'There is {count} change',
                                                     u'There are {count} changes',
                                                     count
                                                    ).format(count=count),
                                          ]
                                )

    def get_config_form_class(self, job):
        from .forms import CruditySynchronizeJobForm
        return CruditySynchronizeJobForm

    @property
    def results_bricks(self):
        from creme.creme_core.bricks import JobResultsBrick
        return [JobResultsBrick()]


crudity_synchronize_type = _CruditySynchronizeType()
jobs = (crudity_synchronize_type,)
