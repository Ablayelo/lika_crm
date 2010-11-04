# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import SearchConfigItem, RelationType
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Contact

from events.models import EventType, Event
from events.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_IS_INVITED_TO,       _(u'is invited to the event'),              [Contact]),
                            (REL_OBJ_IS_INVITED_TO,       _(u'has invited'),                          [Event]))
        RelationType.create((REL_SUB_ACCEPTED_INVITATION, _(u'accepted the invitation to the event'), [Contact]),
                            (REL_OBJ_ACCEPTED_INVITATION, _(u'prepares to receive'),                  [Event]))
        RelationType.create((REL_SUB_REFUSED_INVITATION,  _(u'refused the invitation to the event'),  [Contact]),
                            (REL_OBJ_REFUSED_INVITATION,  _(u'do not prepare to receive any more'),   [Event]))
        RelationType.create((REL_SUB_CAME_EVENT,          _(u'came to the event'),                    [Contact]),
                            (REL_OBJ_CAME_EVENT,          _(u'received'),                             [Event]))
        RelationType.create((REL_SUB_NOT_CAME_EVENT,      _(u'did not come to the event'),            [Contact]),
                            (REL_OBJ_NOT_CAME_EVENT,      _(u'did not receive'),                      [Event]))


        #TODO: use 'start' arg with python 2.6.....
        for i, name in enumerate((_('Show'), _('Conference'), _('Breakfast'), _('Brunch'))):
            create(EventType, i + 1, name=name)

        hf_id = create(HeaderFilter, 'events-hf', name=_(u'Event view'), entity_type_id=ContentType.objects.get_for_model(Event).id, is_custom=False).id
        pref = 'events-hfi_'
        create(HeaderFilterItem, pref + 'name',       order=1, name='name',       title=_(u'Name'),       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'type',       order=2, name='type',       title=_(u'Type'),       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="type__name__icontains")
        create(HeaderFilterItem, pref + 'start_date', order=3, name='start_date', title=_(u'Start date'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="start_date__range")
        create(HeaderFilterItem, pref + 'end_date',   order=4, name='end_date',   title=_(u'End date'),   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="end_date__range")

        SearchConfigItem.create(Event, ['name', 'description', 'type__name'])
