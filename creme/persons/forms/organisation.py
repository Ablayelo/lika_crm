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

from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeEntityField, CremeDateTimeField

from media_managers.models import Image
from media_managers.forms.widgets import ImageM2MWidget

from persons.models import Organisation
from persons.forms.base import _BasePersonForm


class OrganisationForm(_BasePersonForm):
    creation_date = CremeDateTimeField(label=_(u"Creation date"), required=False)
    image         = CremeEntityField(label=_(u"Logo"), required=False, model=Image, widget=ImageM2MWidget())

    class Meta(_BasePersonForm.Meta):
        model = Organisation
