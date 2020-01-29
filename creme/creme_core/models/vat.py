# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2019  Hybird
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

from django.db.models import BooleanField, DecimalField
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from .base import CremeModel
from ..constants import DEFAULT_VAT


class Vat(CremeModel):
    value      = DecimalField(_('VAT'), max_digits=4, decimal_places=2, default=DEFAULT_VAT)
    is_default = BooleanField(_('Is default?'), default=False)
    is_custom  = BooleanField(default=True).set_tags(viewable=False)  # Used by creme_config

    creation_label = _('Create a VAT value')

    def __str__(self):
        return str(self.value)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('VAT')
        verbose_name_plural = _('VAT')
        ordering = ('value',)

    @atomic
    def save(self, *args, **kwargs):
        if self.is_default:
            Vat.objects.update(is_default=False)
        elif not Vat.objects.filter(is_default=True).exclude(pk=self.id).exists():
            self.is_default = True

        super().save(*args, **kwargs)

    @atomic
    def delete(self, *args, **kwargs):
        if self.is_default:
            first_vat = Vat.objects.exclude(id=self.id).first()

            if first_vat:
                first_vat.is_default = True
                first_vat.save()

        super().delete(*args, **kwargs)

    @staticmethod
    def get_default_vat() -> 'Vat':
        return Vat.objects.filter(is_default=True)[0]
