# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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
from django.shortcuts import get_object_or_404
from django.template import Template, Context
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import RelationType
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.html import sanitize_html
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import jsonify
from creme.creme_core.views.generic.base import EntityRelatedMixin
from creme.creme_core.views.relation import RelationsAdding

from .. import get_entityemail_model, bricks, constants
from ..forms import mail as mail_forms
from ..forms.template import TEMPLATES_VARS
from ..models import LightWeightEmail

EntityEmail = get_entityemail_model()


# Function views --------------------------------------------------------------

@login_required
@permission_required('emails')
def get_lightweight_mail_body(request, mail_id):
    """Used to show an html document in an iframe."""
    email = get_object_or_404(LightWeightEmail, pk=mail_id)
    request.user.has_perm_to_view_or_die(email.sending.campaign)

    return HttpResponse(sanitize_html(email.rendered_body_html,
                                      # TODO: ? allow_external_img=request.GET.get('external_img', False),
                                      allow_external_img=True,
                                     )
                       )


@login_required
@permission_required('emails')
@jsonify
def resend_mails(request):
    ids = get_from_POST_or_404(request.POST, 'ids').split(',')

    for email in EntityEmail.objects.filter(pk__in=ids):
        email.send()

    return {}


# Class-based views  ----------------------------------------------------------

class EntityEmailCreation(generic.AddingInstanceToEntityPopup):
    model = EntityEmail
    form_class = mail_forms.EntityEmailForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    permissions = ['emails', cperm(EntityEmail)]
    title = _('Sending an email to «{entity}»')
    submit_label = EntityEmail.sending_label

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)


class EntityEmailWizard(EntityRelatedMixin, generic.EntityCreationWizardPopup):
    model = EntityEmail
    form_list = [
        mail_forms.TemplateSelectionFormStep,
        mail_forms.EntityEmailForm,
    ]
    title = _('Sending an email to «{entity}»')
    submit_label = _('Send the email')

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)
        user.has_perm_to_link_or_die(entity)

    def done_save(self, form_list):
        for form in form_list:
            form.save()

    def get_form_initial(self, step):
        initial = super().get_form_initial(step=step)

        if step == '1':
            email_template = self.get_cleaned_data_for_step('0')['template']
            ctx = {
                var_name: getattr(self.get_related_entity(), var_name, '')
                    for var_name in TEMPLATES_VARS
            }
            initial['subject'] = email_template.subject
            initial['body'] = Template(email_template.body).render(Context(ctx))
            initial['body_html'] = Template(email_template.body_html).render(Context(ctx))
            initial['signature'] = email_template.signature_id
            initial['attachments'] = [
                *email_template.attachments.values_list('id', flat=True)
            ]  # TODO: test

        return initial

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        entity = self.get_related_entity()

        if step == '1':
            kwargs['entity'] = entity

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['entity'] = self.get_related_entity()

        return data


class EntityEmailDetail(generic.EntityDetail):
    model = EntityEmail
    template_name = 'emails/view_entity_mail.html'
    pk_url_kwarg = 'mail_id'


class EntityEmailPopup(generic.EntityDetailPopup):
    model = EntityEmail
    pk_url_kwarg = 'mail_id'
    title = _('Details of the email')

    def get_brick_ids(self):
        return (
            bricks.MailPopupBrick.id_,
        )


class EntityEmailsList(generic.EntitiesList):
    model = EntityEmail
    default_headerfilter_id = constants.DEFAULT_HFILTER_EMAIL


class EntityEmailLinking(RelationsAdding):
    title = _('Link «{entity}» to emails')

    def get_relation_types(self):
        subject = self.get_related_entity()
        subject_ctype = subject.entity_type
        rtypes = []
        subjects_prop_ids = None  # TODO: lazy object

        for rtype in RelationType.objects.filter(id__in=bricks.MailsHistoryBrick
                                                              .relation_type_deps):
            if not rtype.is_compatible(subject_ctype):
                continue

            # TODO: unit test
            # TODO: factorise with RelationsAdding
            needed_property_types = [*rtype.subject_properties.all()]
            if needed_property_types:
                if subjects_prop_ids is None:
                    subjects_prop_ids = {*subject.properties.values_list('type', flat=True)}

                if any(needed_ptype.id not in subjects_prop_ids
                           for needed_ptype in needed_property_types
                      ):
                    continue

            rtypes.append(rtype.id)

        # TODO: unit test
        if not rtypes:
            raise ConflictError(gettext('No type of relationship is compatible.'))

        return rtypes


# TODO: disable the link in the template if view is not allowed
class LightWeightEmailPopup(generic.RelatedToEntityDetailPopup):
    model = LightWeightEmail
    pk_url_kwarg = 'mail_id'
    permissions = 'emails'
    title = _('Details of the email')

    def get_brick_ids(self):
        return (
            bricks.LwMailPopupBrick.id_,
        )
