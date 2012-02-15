# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.auth.models import User

from creme_core import autodiscover as creme_core_autodiscover
from creme_core.models import (RelationType, CremeProperty, CremePropertyType,
                               HeaderFilter, HeaderFilterItem,
                               EntityFilter, EntityFilterCondition,
                               ButtonMenuItem, SearchConfigItem, RelationBlockItem,
                               BlockDetailviewLocation, BlockPortalLocation)
from creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme_core.utils import create_if_needed
from creme_core.blocks import relations_block, properties_block, customfields_block, history_block
from creme_core.buttons import merge_entities_button
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import *
from persons.constants import *
from persons.blocks import *
from persons.buttons import *


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self, *args, **kwargs):
        rt_map = {}
        for rt_info in [((REL_SUB_EMPLOYED_BY,       _(u'is an employee of'),          [Contact]),
                         (REL_OBJ_EMPLOYED_BY,       _(u'employs'),                    [Organisation]),
                        ),
                        ((REL_SUB_CUSTOMER_SUPPLIER, _(u'is a customer of'),           [Contact, Organisation]),
                         (REL_OBJ_CUSTOMER_SUPPLIER, _(u'is a supplier of'),           [Contact, Organisation]),
                        ),
                        ((REL_SUB_MANAGES,           _(u'manages'),                    [Contact]),
                         (REL_OBJ_MANAGES,           _(u'managed by'),                 [Organisation]),
                        ),
                        ((REL_SUB_PROSPECT,          _(u'is a prospect of'),           [Contact, Organisation]),
                         (REL_OBJ_PROSPECT,          _(u'has as prospect'),            [Contact, Organisation]),
                        ),
                        ((REL_SUB_SUSPECT,           _(u'is a suspect of'),            [Contact, Organisation]),
                         (REL_OBJ_SUSPECT,           _(u'has as suspect'),             [Contact, Organisation]),
                        ),
                        ((REL_SUB_PARTNER,           _(u'is a partner of'),            [Contact, Organisation]),
                         (REL_OBJ_PARTNER,           _(u'has as partner'),             [Contact, Organisation]),
                        ),
                        ((REL_SUB_INACTIVE,          _(u'is an inactive customer of'), [Contact, Organisation]),
                         (REL_OBJ_INACTIVE,          _(u'has as inactive customer'),   [Contact, Organisation]),
                        ),
                        ((REL_SUB_SUBSIDIARY,        _(u'has as subsidiary'),          [Organisation]),
                         (REL_OBJ_SUBSIDIARY,        _(u"is a subsidiary of"),         [Organisation]),
                        ),
                       ]:
            rt, sym_rt = RelationType.create(*rt_info)
            rt_map[rt.id] = rt
            rt_map[sym_rt.id] = sym_rt

        create_if_needed(Civility,          {'pk': 1}, title=_(u"Mrs."))
        create_if_needed(Civility,          {'pk': 2}, title=_(u"Miss"))
        mister = create_if_needed(Civility, {'pk': 3}, title=_(u"Mr."))
        create_if_needed(Civility,          {'pk': 4}, title=_(u"Unknown"))

        create_if_needed(Position, {'pk': 1}, title=_(u"CEO"))
        create_if_needed(Position, {'pk': 2}, title=_(u"Secretary"))
        create_if_needed(Position, {'pk': 3}, title=_(u"Technician"))

        create_if_needed(Sector, {'pk': 1}, title=_(u"Food Industry"))
        create_if_needed(Sector, {'pk': 2}, title=_(u"Industry"))
        create_if_needed(Sector, {'pk': 3}, title=_(u"Informatic"))
        create_if_needed(Sector, {'pk': 4}, title=_(u"Telecom"))
        create_if_needed(Sector, {'pk': 5}, title=_(u"Restoration"))

        #TODO: depend on the country no ??
        create_if_needed(LegalForm, {'pk': 1}, title=u"SARL")
        create_if_needed(LegalForm, {'pk': 2}, title=u"Association loi 1901")
        create_if_needed(LegalForm, {'pk': 3}, title=u"SA")
        create_if_needed(LegalForm, {'pk': 4}, title=u"SAS")

        create_if_needed(StaffSize, {'pk': 1}, size="1 - 5")
        create_if_needed(StaffSize, {'pk': 2}, size="6 - 10")
        create_if_needed(StaffSize, {'pk': 3}, size="11 - 50")
        create_if_needed(StaffSize, {'pk': 4}, size="51 - 100")
        create_if_needed(StaffSize, {'pk': 5}, size="100 - 500")
        create_if_needed(StaffSize, {'pk': 6}, size="> 500")

        hf = HeaderFilter.create(pk='persons-hf_contact', name=_(u'Contact view'), model=Contact)
        hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name='last_name'),
                      HeaderFilterItem.build_4_field(model=Contact, name='first_name'),
                      HeaderFilterItem.build_4_field(model=Contact, name='phone'),
                      HeaderFilterItem.build_4_field(model=Contact, name='email'),
                      HeaderFilterItem.build_4_field(model=Contact, name='user__username'),
                      HeaderFilterItem.build_4_relation(rt_map[REL_SUB_EMPLOYED_BY]),
                     ])

        hf = HeaderFilter.create(pk='persons-hf_leadcustomer', name=_(u'Prospect/Suspect view'), model=Organisation)
        hf.set_items([HeaderFilterItem.build_4_field(model=Organisation, name='name'),
                      HeaderFilterItem.build_4_field(model=Organisation, name='sector__title'),
                      HeaderFilterItem.build_4_field(model=Organisation, name='phone'),
                      HeaderFilterItem.build_4_field(model=Organisation, name='email'),
                      HeaderFilterItem.build_4_field(model=Organisation, name='user__username'),
                      HeaderFilterItem.build_4_relation(rt_map[REL_SUB_CUSTOMER_SUPPLIER]),
                      HeaderFilterItem.build_4_relation(rt_map[REL_SUB_PROSPECT]),
                      HeaderFilterItem.build_4_relation(rt_map[REL_SUB_SUSPECT]),
                     ])

        hf = HeaderFilter.create(pk='persons-hf_organisation', name=_(u'Organisation view'), model=Organisation)
        hf.set_items([HeaderFilterItem.build_4_field(model=Organisation, name='name'),
                      HeaderFilterItem.build_4_field(model=Organisation, name='phone'),
                      HeaderFilterItem.build_4_field(model=Organisation, name='user__username'),
                      HeaderFilterItem.build_4_relation(rt_map[REL_OBJ_MANAGES]),
                     ])

        create_bmi = ButtonMenuItem.create_if_needed
        create_bmi(pk='persons-customer_contact_button', model=Contact, button=become_customer_button, order=20)
        create_bmi(pk='persons-prospect_contact_button', model=Contact, button=become_prospect_button, order=21)
        create_bmi(pk='persons-suspect_contact_button',  model=Contact, button=become_suspect_button,  order=22)
        create_bmi(pk='persons-inactive_contact_button', model=Contact, button=become_inactive_button, order=24)
        create_bmi(pk='persons-merge_contacts_button',   model=Contact, button=merge_entities_button,  order=30)

        create_bmi(pk='persons-customer_orga_button',  model=Organisation, button=become_customer_button,    order=20)
        create_bmi(pk='persons-prospect_orga_button',  model=Organisation, button=become_prospect_button,    order=21)
        create_bmi(pk='persons-suspect_orga_button',   model=Organisation, button=become_suspect_button,     order=22)
        create_bmi(pk='persons-inactive_orga_button',  model=Organisation, button=become_inactive_button,    order=23)
        create_bmi(pk='persons-supplier_button',       model=Organisation, button=become_supplier_button,    order=24)
        create_bmi(pk='persons-linked_contact_button', model=Organisation, button=add_linked_contact_button, order=25)
        create_bmi(pk='persons-merge_orgas_button',    model=Organisation, button=merge_entities_button,     order=30)

        managed_by_creme = CremePropertyType.objects.get(pk=PROP_IS_MANAGED_BY_CREME)

        efilter = EntityFilter.create(FILTER_MANAGED_ORGA, name=_(u"Managed by creme"), model=Organisation)
        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=managed_by_creme, has=True)])

        admin = User.objects.get(pk=1)

        if not Contact.objects.filter(is_user=admin).exists():
            Contact.objects.create(first_name='Fulbert', last_name='Creme',
                                   civility_id=mister.pk, description="Creme master",
                                   user=admin, is_user=admin
                                  )

        #TODO: add relation to admin ????
        if not Organisation.objects.exists():
            orga = Organisation.objects.create(user=admin, name=_("ReplaceByYourSociety"))
            CremeProperty.objects.create(type=managed_by_creme, creme_entity=orga)

        SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name', 'phone', 'mobile', 'email'])
        SearchConfigItem.create_if_needed(Organisation, ['name', 'phone', 'email', 'sector__title', 'legal_form__title'])

        #Populate blocks
        rbi_1 = RelationBlockItem.create(REL_SUB_CUSTOMER_SUPPLIER)
        rbi_2 = RelationBlockItem.create(REL_OBJ_CUSTOMER_SUPPLIER)

        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=Organisation)
        BlockDetailviewLocation.create(block_id=orga_coord_block.id_,    order=30,  zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=address_block.id_,       order=50,  zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=other_address_block.id_, order=60,  zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=managers_block.id_,      order=100, zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=employees_block.id_,     order=120, zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=rbi_1.block_id,          order=1,   zone=BlockDetailviewLocation.RIGHT, model=Organisation)
        BlockDetailviewLocation.create(block_id=rbi_2.block_id,          order=2,   zone=BlockDetailviewLocation.RIGHT, model=Organisation)
        BlockDetailviewLocation.create(block_id=history_block.id_,       order=30,  zone=BlockDetailviewLocation.RIGHT, model=Organisation)

        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=Contact)
        BlockDetailviewLocation.create(block_id=contact_coord_block.id_,  order=30,  zone=BlockDetailviewLocation.LEFT,  model=Contact)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,   order=40,  zone=BlockDetailviewLocation.LEFT,  model=Contact)
        BlockDetailviewLocation.create(block_id=address_block.id_,        order=50,  zone=BlockDetailviewLocation.LEFT,  model=Contact)
        BlockDetailviewLocation.create(block_id=other_address_block.id_,  order=60,  zone=BlockDetailviewLocation.LEFT,  model=Contact)
        BlockDetailviewLocation.create(block_id=properties_block.id_,     order=450, zone=BlockDetailviewLocation.LEFT,  model=Contact)
        BlockDetailviewLocation.create(block_id=relations_block.id_,      order=500, zone=BlockDetailviewLocation.LEFT,  model=Contact)
        BlockDetailviewLocation.create(block_id=history_block.id_,        order=20,  zone=BlockDetailviewLocation.RIGHT, model=Contact)

        BlockPortalLocation.create(app_name='persons', block_id=neglected_orgas_block.id_, order=10)
        BlockPortalLocation.create(app_name='persons', block_id=history_block.id_,         order=30)

        if 'assistants' in settings.INSTALLED_APPS:
            info('Assistants app is installed => we use the assistants blocks on detail views and portal')

            from assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=Contact)
            BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=Contact)
            BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=Contact)
            BlockDetailviewLocation.create(block_id=messages_block.id_, order=500, zone=BlockDetailviewLocation.RIGHT, model=Contact)

            BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=Organisation)
            BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=Organisation)
            BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=Organisation)
            BlockDetailviewLocation.create(block_id=messages_block.id_, order=500, zone=BlockDetailviewLocation.RIGHT, model=Organisation)

            BlockPortalLocation.create(app_name='persons', block_id=memos_block.id_,    order=100)
            BlockPortalLocation.create(app_name='persons', block_id=alerts_block.id_,   order=200)
            BlockPortalLocation.create(app_name='persons', block_id=messages_block.id_, order=400)
