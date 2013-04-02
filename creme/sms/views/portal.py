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

from django.utils.translation import ugettext as _

from creme.creme_core.views.generic import app_portal

from ..models import SMSCampaign, MessagingList, Sending, SMSAccount


def portal(request):
    stats = ((_('Number of campaigns'),       SMSCampaign.objects.count()),
             (_('Number of messaging lists'), MessagingList.objects.count()),
             (_("Number of sendings"),        Sending.objects.count()),
            )

    account, created =  SMSAccount.objects.get_or_create(pk=1)
    account.sync()

    return app_portal(request, 'sms', 'sms/portal.html', (SMSCampaign, MessagingList), stats, 
                      extra_template_dict={'account': account},
                     )
