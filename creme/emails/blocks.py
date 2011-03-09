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

from django.http import HttpResponse
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.constants import REL_SUB_RELATED_TO, REL_OBJ_RELATED_TO
from creme_core.models import Relation, CremeEntity
from creme_core.gui.block import QuerysetBlock#, list4url
from creme_core.utils import jsonify

from persons.models import Contact, Organisation

from documents.models import Document

from emails.constants import *
from emails.models import *
from emails.models.mail import MAIL_STATUS_SYNCHRONIZED_SPAM, MAIL_STATUS_SYNCHRONIZED_WAITING, MAIL_STATUS, MAIL_STATUS_SENT


#TODO: move populate_credentials() code to a Block class in creme_core ???
class _RelatedEntitesBlock(QuerysetBlock):
    #id_           = 'SET ME'
    #dependencies  = 'SET ME'
    #verbose_name  = 'SET ME'
    #template_name = 'SET ME'

    def _get_queryset(self, entity): #OVERLOAD ME
        raise NotImplementedError

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context, self._get_queryset(entity),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                             )

        CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class MailingListsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mailing_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Mailing lists')
    template_name = 'emails/templatetags/block_mailing_lists.html'

    def _get_queryset(self, entity): #entity=campaign
        return entity.mailing_lists.all()


class EmailRecipientsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'recipients')
    dependencies  = (EmailRecipient,)
    verbose_name  = _(u'Unlinked recipients')
    template_name = 'emails/templatetags/block_recipients.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, EmailRecipient.objects.filter(ml=mailing_list.id), #get_recipients() ???
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, mailing_list.pk),
                                                            ct_id=ContentType.objects.get_for_model(EmailRecipient).id,
                                                           ))


class ContactsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'contacts')
    dependencies  = (Contact,)
    verbose_name  = _(u'Contacts recipients')
    template_name = 'emails/templatetags/block_contacts.html'

    def _get_queryset(self, entity): #entity=mailing_list
        return entity.contacts.select_related('civility')


class OrganisationsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'organisations')
    dependencies  = (Organisation,)
    verbose_name  = _(u'Organisations recipients')
    template_name = 'emails/templatetags/block_organisations.html'

    def _get_queryset(self, entity): #entity=mailing_list
        return entity.organisations.all()


class ChildListsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'child_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Child mailing lists')
    template_name = 'emails/templatetags/block_child_lists.html'

    def _get_queryset(self, entity): #entity=mailing_list
        return entity.children.all()


class ParentListsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'parent_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Parent mailing lists')
    template_name = 'emails/templatetags/block_parent_lists.html'

    def _get_queryset(self, entity): #entity=mailing_list
        return entity.parents_set.all()


class AttachmentsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'attachments')
    dependencies  = (Document,)
    verbose_name  = _(u'Attachments')
    template_name = 'emails/templatetags/block_attachments.html'

    def _get_queryset(self, entity): #entity=mailtemplate
        return entity.attachments.all()


class SendingsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'sendings')
    dependencies  = (EmailSending,)
    order_by      = '-sending_date'
    verbose_name  = _(u'Sendings')
    template_name = 'emails/templatetags/block_sendings.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, EmailSending.objects.filter(campaign=campaign.id), #TODO: use related_name
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, campaign.pk),
                                                            ct_id=ContentType.objects.get_for_model(EmailSending).id,
                                                           ))


class MailsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mails')
    dependencies  = (LightWeightEmail,)
    page_size     = 12
    verbose_name  = _(u"Emails of a sending")
    template_name = 'emails/templatetags/block_mails.html'

    def detailview_display(self, context):
        sending = context['object']
        btc = self.get_block_template_context(context, sending.get_mails().select_related('recipient_entity'),
                                              update_url='/emails/campaign/sending/%s/mails/reload/' % sending.pk,
                                              ct_id=ContentType.objects.get_for_model(LightWeightEmail).id,
                                             )

        CremeEntity.populate_credentials([mail.recipient_entity for mail in btc['page'].object_list if mail.recipient_entity],
                                         context['user']
                                        )

        return self._render(btc)

    #Useful method because EmailSending is not a CremeEntity (should be ?) --> generic view in creme_core (problems with credemtials ?) ??
    @jsonify
    def detailview_ajax(self, request, entity_id):
        context = RequestContext(request)
        context.update({
                'object': EmailSending.objects.get(id=entity_id),
            })

        return [(self.id_, self.detailview_display(context))]


class MailsHistoryBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mails_history')
    dependencies  = (EntityEmail, Relation)
    order_by      = '-sending_date'
    verbose_name  = _(u"Emails history")
    template_name = 'emails/templatetags/block_mails_history.html'
    configurable  = True

    def detailview_display(self, context):
        object = context['object']
        pk = object.pk

        rtypes = [REL_OBJ_MAIL_SENDED, REL_OBJ_MAIL_RECEIVED, REL_OBJ_RELATED_TO]

        entityemail_pk = Relation.objects.filter(type__pk__in=[REL_SUB_MAIL_SENDED, REL_SUB_MAIL_RECEIVED, REL_SUB_RELATED_TO], object_entity=pk).values_list('subject_entity', flat=True).distinct()

        return self._render(self.get_block_template_context(context,
                                                            EntityEmail.objects.filter(pk__in=entityemail_pk),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                                                            sent_status=MAIL_STATUS_SENT,
                                                            rtypes=','.join(rtypes),
                                                            entity_email_ct_id=ContentType.objects.get_for_model(object).id
                                                            ))

class LwMailsHistoryBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'lw_mails_history')
    dependencies  = (LightWeightEmail,)
    order_by      = '-sending_date'
    verbose_name  = _(u"Campaings emails history")
    template_name = 'emails/templatetags/block_lw_mails_history.html'
    configurable  = True

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context,
                                                            LightWeightEmail.objects.filter(recipient_entity=pk).select_related('sending'),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                                                           ))


class _SynchronizationMailsBlock(QuerysetBlock):
    dependencies  = (EntityEmail,)
    order_by      = '-reception_date'

    #def __init__(self, *args, **kwargs):
        #super(_SynchronizationMailsBlock, self).__init__()

    @jsonify
    def detailview_ajax(self, request):
        context = RequestContext(request)
        context.update({ #TODO: useless (already in detailview_display)
            'MAIL_STATUS': MAIL_STATUS,
            'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id,
        })

        return [(self.id_, self.detailview_display(context))]


class WaitingSynchronizationMailsBlock(_SynchronizationMailsBlock):
    id_           = QuerysetBlock.generate_id('emails', 'waiting_synchronisation')
    verbose_name  = _(u'Incoming Emails to sync')
    template_name = 'emails/templatetags/block_synchronization.html'

    def detailview_display(self, context):
        context.update({'MAIL_STATUS': MAIL_STATUS, 'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id, 'rtypes': ','.join([REL_SUB_MAIL_SENDED, REL_SUB_MAIL_RECEIVED, REL_SUB_RELATED_TO])})
        return self._render(self.get_block_template_context(context, EntityEmail.objects.filter(status=MAIL_STATUS_SYNCHRONIZED_WAITING),
#                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_
                                                            update_url='/emails/sync_blocks/reload'
                                                            #MAIL_STATUS=MAIL_STATUS #TODO
                                                            ))


class SpamSynchronizationMailsBlock(_SynchronizationMailsBlock):
    id_           = QuerysetBlock.generate_id('emails', 'synchronised_as_spam')
    verbose_name  = _(u'Spam emails')
    template_name = 'emails/templatetags/block_synchronization_spam.html'

    def detailview_display(self, context):
        context.update({'MAIL_STATUS': MAIL_STATUS, 'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id})
        return self._render(self.get_block_template_context(context, EntityEmail.objects.filter(status=MAIL_STATUS_SYNCHRONIZED_SPAM),
#                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_
                                                            update_url='/emails/sync_blocks/reload'
                                                            ))


class SignaturesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'signatures')
    dependencies  = (EmailSignature,)
    order_by      = 'name'
    verbose_name  = u'Email signatures'
    template_name = 'emails/templatetags/block_signatures.html'

    def detailview_display(self, context): #NB: indeed, it is displayed on portal of persons
        return self._render(self.get_block_template_context(context, EmailSignature.objects.filter(user=context['user']),
                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_
                                                           ))


mails_block = MailsBlock()
#mail_waiting_sync_block = WaitingSynchronizationMailsBlock()
#mail_spam_sync_block    = SpamSynchronizationMailsBlock()

blocks_list = (
        MailingListsBlock(),
        EmailRecipientsBlock(),
        ContactsBlock(),
        OrganisationsBlock(),
        ChildListsBlock(),
        ParentListsBlock(),
        AttachmentsBlock(),
        SendingsBlock(),
        mails_block,
        MailsHistoryBlock(),
        LwMailsHistoryBlock(),
        WaitingSynchronizationMailsBlock(), #mail_waiting_sync_block
        SpamSynchronizationMailsBlock(), #mail_spam_sync_bloc
        SignaturesBlock(),
    )
