# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Relation
from creme_core.gui.block import QuerysetBlock

from persons.models import Contact
from persons.constants import REL_OBJ_MANAGES, REL_OBJ_EMPLOYED_BY

_contact_ct_id = None


class ManagersBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('persons', 'managers')
    dependencies  = (Relation,) #Contact
    relation_type_deps = (REL_OBJ_MANAGES, )
    verbose_name  = _(u"Organisation managers")
    template_name = 'persons/templatetags/block_managers.html'

    def detailview_display(self, context):
        global _contact_ct_id

        orga = context['object']

        if not _contact_ct_id:
            _contact_ct_id = ContentType.objects.get_for_model(Contact).id

        return self._render(self.get_block_template_context(context,
                                                            orga.get_managers(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, orga.pk),
                                                            predicate_id=REL_OBJ_MANAGES,
                                                            ct_id=_contact_ct_id))


class EmployeesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('persons', 'employees')
    dependencies  = (Relation,) #Contact
    relation_type_deps = (REL_OBJ_EMPLOYED_BY, )
    verbose_name  = _(u"Organisation employees")
    template_name = 'persons/templatetags/block_employees.html'

    def detailview_display(self, context):
        global _contact_ct_id

        orga = context['object']

        if not _contact_ct_id:
            _contact_ct_id = ContentType.objects.get_for_model(Contact).id

        return self._render(self.get_block_template_context(context,
                                                            orga.get_employees(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, orga.pk),
                                                            predicate_id=REL_OBJ_EMPLOYED_BY,
                                                            ct_id=_contact_ct_id))


managers_block  = ManagersBlock()
employees_block = EmployeesBlock()
