# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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

from django.urls.base import reverse
from django.utils.translation import ugettext_lazy as _

from creme import persons
from creme.creme_core.gui.actions import ActionEntry


class GenerateVcfActionEntry(ActionEntry):
    action_id = 'vfs-export'
    action = 'redirect'

    model = persons.get_contact_model()
    label = _('Generate a VCF')
    icon = 'download'

    @property
    def url(self):
        return reverse('vcfs__export', args=(self.instance.id,))

    @property
    def is_enabled(self):
        return self.user.has_perm_to_view(self.instance)

    # TODO ?
    # @property
    # def help_text(self):
    #     return _('Download as a VCF file ....')