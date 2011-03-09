# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.utils.translation import ugettext as _

from creme_core.models import SearchConfigItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from reports.models import Report


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        hf   = HeaderFilter.create(pk='reports-hf', name=_(u'Report view'), model=Report)
        pref = 'reports-hfi_report_'
        create(HeaderFilterItem, pref + 'name', order=1, name='name',     title=_(u'Name'),               type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ct',   order=2, name='ct__name', title=_(u"Entity type - Name"), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="ct__name__icontains")

        SearchConfigItem.create(Report, ['name', 'ct__name'])
