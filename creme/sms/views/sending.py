# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from django.shortcuts import render, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.views.generic import add_to_entity
from creme.creme_core.utils import get_from_POST_or_404, jsonify

from ..models import SMSCampaign, Sending, Message
from ..forms.message import SendingCreateForm
from ..blocks import messages_block
#from creme.sms.webservice.samoussa import SamoussaBackEnd
#from creme.sms.webservice.backend import WSException


@login_required
@permission_required('sms')
def add(request,campaign_id):
    return add_to_entity(request, campaign_id, SendingCreateForm,
                         _('New sending for <%s>'), entity_class=SMSCampaign,
                        )

@login_required
@permission_required('sms')
def delete(request):
    sending  = get_object_or_404(Sending , pk=get_from_POST_or_404(request.POST, 'id'))
    campaign = sending.campaign

    request.user.has_perm_to_change_or_die(campaign)

    sending.delete() #TODO: try/except ??

    if request.is_ajax():
        return HttpResponse("success", mimetype="text/javascript")

    return HttpResponseRedirect(campaign.get_absolute_url())

@login_required
@permission_required('sms')
def sync_messages(request, id):
    sending = get_object_or_404(Sending, pk=id)
    #sending.campaign.can_view_or_die(request.user)
    request.user.has_perm_to_change_or_die(sending.campaign)

    Message.sync(sending)

    return HttpResponse('', status=200)

@login_required
@permission_required('sms')
def send_messages(request, id):
    sending = get_object_or_404(Sending, pk=id)
    #sending.campaign.can_view_or_die(request.user)
    request.user.has_perm_to_change_or_die(sending.campaign)

    Message.send(sending)

    return HttpResponse('', status=200)

@login_required
@permission_required('sms')
def detailview(request, id):
    sending  = get_object_or_404(Sending, pk=id)
    request.user.has_perm_to_view_or_die(sending.campaign)

    return render(request, 'sms/popup_sending.html', {'object': sending})

@login_required
@permission_required('sms')
def delete_message(request, id):
    message  = get_object_or_404(Message, pk=id)
    campaign = message.sending.campaign

    request.user.has_perm_to_change_or_die(campaign)

    try:
        message.sync_delete()
        message.delete()
    except Exception, err:
        return HttpResponse(err, status=500) #TODO: WTF ?!

    if request.is_ajax():
        return HttpResponse("success", mimetype="text/javascript")

    #TODO: better with a named url.....
    return HttpResponseRedirect('/sms/campaign/sending/%s' % message.sending_id)

#@login_required
#@permission_required('sms')
#def reload_block_messages(request, id):
    #return messages_block.detailview_ajax(request, id)

#Useful method because EmailSending is not a CremeEntity (should be ?)
@jsonify
@login_required
@permission_required('sms')
def reload_block_messages(request, id):
    sending  = get_object_or_404(Sending, pk=id)
    request.user.has_perm_to_view_or_die(sending.campaign)

    context = RequestContext(request)
    context['object'] = sending

    return [(messages_block.id_, messages_block.detailview_display(context))]
