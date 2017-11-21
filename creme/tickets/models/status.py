# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from django.db.models import CharField, BooleanField
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import BasicAutoField


OPEN_PK       = 1
CLOSED_PK     = 2
INVALID_PK    = 3
DUPLICATED_PK = 4
WONTFIX_PK    = 5

BASE_STATUS = (
    (OPEN_PK,        pgettext_lazy('tickets-status', u'Open')),
    (CLOSED_PK,      pgettext_lazy('tickets-status', u'Closed')),
    (INVALID_PK,     pgettext_lazy('tickets-status', u'Invalid')),
    (DUPLICATED_PK,  pgettext_lazy('tickets-status', u'Duplicated')),
    (WONTFIX_PK,     _(u"Won't fix")),
)


class Status(CremeModel):
    "Status of a ticket: open, closed, invalid..."
    name      = CharField(_(u'Name'), max_length=100, blank=False, null=False, unique=True)
    is_custom = BooleanField(default=True).set_tags(viewable=False)  # Used by creme_config
    order     = BasicAutoField(_(u'Order'))  # Used by creme_config

    creation_label = pgettext_lazy('tickets-status', u'Create a status')

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'tickets'
        verbose_name = _(u'Ticket status')
        verbose_name_plural = _(u'Ticket statuses')
        ordering = ('order',)
