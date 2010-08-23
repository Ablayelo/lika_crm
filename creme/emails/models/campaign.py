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

from django.db.models import CharField, ManyToManyField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity

from persons.models import Contact, Organisation

from mailing_list import MailingList
from recipient import EmailRecipient

class EmailCampaign(CremeEntity):
    name          = CharField(_(u'Nom de la campagne'), max_length=100, blank=False, null=False)
    mailing_lists = ManyToManyField(MailingList, verbose_name=_(u'Listes de diffusion associées'))

    class Meta:
        app_label = "emails"
        verbose_name = _(u"Campagne d'emailing")
        verbose_name_plural = _(u"Campagnes d'emailing")

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/emails/campaign/%s" % self.id

    def get_edit_absolute_url(self):
        return "/emails/campaign/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/emails/campaigns"

    def get_delete_absolute_url(self):
        return "/emails/campaign/delete/%s" % self.id

    def delete(self):
        for sending in self.sendings_set.all():
            sending.mails_set.all().delete() #use CremeModel delete() ??
            sending.delete()

        super(EmailCampaign, self).delete()

    def all_recipients(self):
        #merge all the mailing_lists and their children
        lists = dict(pk_ml for ml in self.mailing_lists.all() for pk_ml in ml.get_family().iteritems()).values()

        get_ct = ContentType.objects.get_for_model

        #manual recipients
        recipients = dict((addr, None) for addr in EmailRecipient.objects.filter(ml__id__in=[ml.id for ml in lists]).values_list('address', flat=True))

        #contacts recipients
        ct = get_ct(Contact)
        recipients.update((contact.email, (ct, contact)) for ml in lists for contact in ml.contacts.all() if contact.email)

        #organisations recipients
        ct = get_ct(Organisation)
        recipients.update((orga.email, (ct, orga)) for ml in lists for orga in ml.organisations.all() if orga.email)

        return recipients.iteritems()