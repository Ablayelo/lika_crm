# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

import logging
# import warnings

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import (PositiveIntegerField, PositiveSmallIntegerField,
        CharField, TextField, DateTimeField, ForeignKey, ManyToManyField)
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models import CremeModel, CremeEntity
from creme.creme_core.models.fields import UnsafeHTMLField

from ..constants import MAIL_STATUS_NOTSENT, MAIL_STATUS
from ..utils import generate_id, EMailSender
from .signature import EmailSignature


logger = logging.getLogger(__name__)
ID_LENGTH = 32


class _Email(CremeModel):
    reads          = PositiveIntegerField(_(u'Number of reads'), blank=True, null=True,
                                          default=0, editable=False,
                                         )
    status         = PositiveSmallIntegerField(_(u'Status'), editable=False,
                                               default=MAIL_STATUS_NOTSENT,
                                               choices=MAIL_STATUS.items(),
                                              )

    sender         = CharField(_(u'Sender'), max_length=100)
    recipient      = CharField(_(u'Recipient'), max_length=100)
    subject        = CharField(_(u'Subject'), max_length=100, blank=True, null=True)
    body           = TextField(_(u'Body'))
    sending_date   = DateTimeField(_(u"Sending date"), blank=True, null=True, editable=False)
    reception_date = DateTimeField(_(u"Reception date"), blank=True, null=True, editable=False)

    class Meta:
        abstract = True
        app_label = "emails"

    def __unicode__(self):
        return u"Mail<from: %s> <to: %s> <sent: %s> <id: %s>" % (self.sender, self.recipient, self.sending_date, self.id)

    # def get_status_str(self):
    #     warnings.warn("_Email.get_status_str() method is deprecated ; use get_status_display() instead.",
    #                   DeprecationWarning
    #                  )
    #     return MAIL_STATUS[self.status]

    # def get_body(self):
    #     warnings.warn("_Email.get_body() method is deprecated.", DeprecationWarning)
    #
    #     return self.body


class AbstractEntityEmail(_Email, CremeEntity):
    identifier  = CharField(_(u'Email ID'), unique=True, max_length=ID_LENGTH,
                            null=False, blank=False, editable=False,
                            default=generate_id,  # TODO: lambda for this
                           )
    body_html   = UnsafeHTMLField(_(u'Body (HTML)'))
    signature   = ForeignKey(EmailSignature, verbose_name=_(u'Signature'), blank=True, null=True) ##merge with body ????
    attachments = ManyToManyField(settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name=_(u'Attachments'))

    creation_label = _('Add an email')

    class Meta:
        abstract = True
        app_label = "emails"
        verbose_name = _(u'Email')
        verbose_name_plural = _(u'Emails')
        ordering = ('-sending_date',)

    def genid_n_save(self):
        while True:  # TODO: xrange(10000) to avoid infinite loop ??
            self.identifier = generate_id()

            try:
                with atomic():
                    self.save(force_insert=True)
            except IntegrityError:  # A mail with this id already exists
                logger.debug('Mail id already exists: %s', self.identifier)
                self.pk = None
            else:
                return

    def __unicode__(self):
        return ugettext('EMail <from: %(from)s> <to: %(to)s> <status: %(status)s>') % {
                                'from':   self.sender,
                                'to':     self.recipient,
                                'status': self.get_status_display(),
                            }

    def get_absolute_url(self):
        return reverse('emails__view_email', args=(self.pk,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('emails__list_emails')

    # TODO: in a manager ?
    @classmethod
    def create_n_send_mail(cls, sender, recipient, subject, user, body, body_html=u"", signature=None, attachments=None):
        email = cls(sender=sender,
                            recipient=recipient,
                            subject=subject,
                            body=body,
                            body_html=body_html,
                            signature=signature,
                            user=user,
                           )
        email.genid_n_save()

        if attachments:
            email.attachments = attachments

        email.send()

        return email

    def _pre_save_clone(self, source):
        self.genid_n_save()

    # def get_body(self):
    #     warnings.warn("AbstractEntityEmail.get_body() method is deprecated.",
    #                   DeprecationWarning
    #                  )
    #
    #     from django.template.defaultfilters import removetags
    #     from django.utils.safestring import mark_safe
    #
    #     if self.body_html:
    #         return mark_safe(removetags(self.body_html, 'script'))
    #     else:
    #         return mark_safe(removetags(self.body.replace('\n', '</br>'), 'script'))

    def send(self):
        sender = EntityEmailSender(body=self.body,
                                   body_html=self.body_html,
                                   signature=self.signature,
                                   attachments=self.attachments.all(),
                                  )

        if sender.send(self):
            logger.debug("Mail sent to %s", self.recipient)


class EntityEmail(AbstractEntityEmail):
    class Meta(AbstractEntityEmail.Meta):
        swappable = 'EMAILS_EMAIL_MODEL'


class EntityEmailSender(EMailSender):
    def get_subject(self, mail):
        return mail.subject

