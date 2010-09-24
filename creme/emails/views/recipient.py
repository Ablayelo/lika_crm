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

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die
from creme_core.views.generic import add_to_entity

from emails.models import MailingList, EmailRecipient
from emails.forms.recipient import MailingListAddRecipientsForm, MailingListAddCSVForm


def add(request, ml_id):
    return add_to_entity(request, ml_id, MailingListAddRecipientsForm,
                         _(u'New recipients for <%s>'), entity_class=MailingList)

def add_from_csv(request, ml_id):
    return add_to_entity(request, ml_id, MailingListAddCSVForm,
                         _(u'New recipients for <%s>'), entity_class=MailingList)

@login_required
@get_view_or_die('emails')
def delete(request):
    recipient = get_object_or_404(EmailRecipient , pk=request.POST.get('id'))
    ml = recipient.ml

    die_status = edit_object_or_die(request, ml)
    if die_status:
        return die_status

    recipient.delete()

    if request.is_ajax():
        return HttpResponse("success", mimetype="text/javascript")

    return HttpResponseRedirect(ml.get_absolute_url())
