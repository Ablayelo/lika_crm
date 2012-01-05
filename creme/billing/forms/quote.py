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

from billing.models import Quote
from base import BaseCreateForm, BaseEditForm

from persons.workflow import transform_target_into_prospect


class QuoteCreateForm(BaseCreateForm):
    class Meta:
        model = Quote
        exclude = BaseCreateForm.Meta.exclude + ('number',)

    def save(self):
        instance = super(QuoteCreateForm, self).save()
        cleaned_data = self.cleaned_data
        transform_target_into_prospect(cleaned_data['source'], cleaned_data['target'], instance.user)

        return instance

class QuoteEditForm(BaseEditForm):
    class Meta:
        model = Quote
        exclude = BaseEditForm.Meta.exclude + ('number',)
