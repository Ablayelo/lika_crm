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

import logging

from django.apps import apps
from django.utils.translation import gettext as _

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (SearchConfigItem, RelationType, HeaderFilter,
        BrickDetailviewLocation)
from creme.creme_core.utils import create_if_needed

from creme.persons import get_contact_model

from creme.opportunities import get_opportunity_model

from . import get_event_model, constants, bricks
from .models import EventType


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_IS_INVITED_TO).exists()

        Event = get_event_model()
        Contact = get_contact_model()
        Opportunity = get_opportunity_model()

        create_rtype = RelationType.create
        create_rtype((constants.REL_SUB_IS_INVITED_TO,       _('is invited to the event'),               [Contact]),
                     (constants.REL_OBJ_IS_INVITED_TO,       _('has invited'),                           [Event]),
                     is_internal=True,
                    )
        create_rtype((constants.REL_SUB_ACCEPTED_INVITATION, _('accepted the invitation to the event'),  [Contact]),
                     (constants.REL_OBJ_ACCEPTED_INVITATION, _('prepares to receive'),                   [Event]),
                     is_internal=True,
                     )
        create_rtype((constants.REL_SUB_REFUSED_INVITATION,  _('refused the invitation to the event'),   [Contact]),
                     (constants.REL_OBJ_REFUSED_INVITATION,  _('do not prepare to receive any more'),    [Event]),
                     is_internal=True,
                    )
        create_rtype((constants.REL_SUB_CAME_EVENT,          _('came to the event'),                     [Contact]),
                     (constants.REL_OBJ_CAME_EVENT,          _('received'),                              [Event]),
                     is_internal=True,
                    )
        create_rtype((constants.REL_SUB_NOT_CAME_EVENT,      _('did not come to the event'),             [Contact]),
                     (constants.REL_OBJ_NOT_CAME_EVENT,      _('did not receive'),                       [Event]),
                     is_internal=True,
                    )
        create_rtype((constants.REL_SUB_GEN_BY_EVENT,        _('generated by the event'),                [Opportunity]),
                     (constants.REL_OBJ_GEN_BY_EVENT,        _('(event) has generated the opportunity'), [Event]),
                     is_internal=True,
                    )

        # ---------------------------
        HeaderFilter.create(pk=constants.DEFAULT_HFILTER_EVENT, name=_('Event view'), model=Event,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': 'type'}),
                                        (EntityCellRegularField, {'name': 'start_date'}),
                                        (EntityCellRegularField, {'name': 'end_date'}),
                                       ],
                           )

        # ---------------------------
        SearchConfigItem.create_if_needed(Event, ['name', 'description', 'type__name'])

        # ---------------------------
        if not already_populated:
            for i, name in enumerate([_('Show'), _('Conference'), _('Breakfast'), _('Brunch')], start=1):
                create_if_needed(EventType, {'pk': i}, name=name)

            create_bdl = BrickDetailviewLocation.create_if_needed
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.create_4_model_brick(          order=5,   zone=LEFT,  model=Event)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=Event)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=Event)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=Event)
            create_bdl(brick_id=bricks.ResutsBrick.id_,            order=2,   zone=RIGHT, model=Event)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=Event)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants import bricks as a_bricks

                create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=Event)
                create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=Event)
                create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=Event)
                create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=400, zone=RIGHT, model=Event)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the Documents blocks on detail view')

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=Event)
