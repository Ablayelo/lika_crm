# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from datetime import datetime, time

from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeModelWithUserForm, CremeDateTimeField, CremeTimeField
from creme.creme_core.utils.dates import make_aware_dt

from ..models import Alert


#TODO: alright, we need a real date time widget that this shit !
class AlertForm(CremeModelWithUserForm):
    trigger_date = CremeDateTimeField(label=_(u'Trigger date'))
    trigger_time = CremeTimeField(label=_(u'Hour'), required=False)

    class Meta(CremeModelWithUserForm.Meta):
        model = Alert

    def __init__(self, entity, *args, **kwargs):
        super(AlertForm, self).__init__(*args, **kwargs)
        instance  =self.instance
        instance.creme_entity = entity

        trigger_date = instance.trigger_date

        if trigger_date:
            local_trigger_date = localtime(trigger_date)
            self.fields['trigger_time'].initial = time(hour=local_trigger_date.hour,
                                                       minute=local_trigger_date.minute,
                                                      )

    def clean(self):
        cleaned_data = super(AlertForm, self).clean()

        if not self._errors:
            #trigger_date = cleaned_data.get('trigger_date')
            #trigger_time = cleaned_data.get('trigger_time') or time()
            #cleaned_data['trigger_date'] = trigger_date.replace(hour=trigger_time.hour, minute=trigger_time.minute)

            trigger_time = cleaned_data.get('trigger_time')
            if trigger_time:
                cleaned_data['trigger_date'] = make_aware_dt(datetime.combine(cleaned_data['trigger_date'], trigger_time))

        return cleaned_data
