# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from collections import defaultdict

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models import TextField, BooleanField, ForeignKey, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.function_field import FunctionField, FunctionFieldResult, FunctionFieldResultsList
from creme.creme_core.models import CremeModel, CremeEntity
from creme.creme_core.models.fields import CremeUserForeignKey, CreationDateTimeField
from creme.creme_core.utils import ellipsis


class Memo(CremeModel):
    content       = TextField(_(u'Content'))
    on_homepage   = BooleanField(_(u'Displayed on homepage'), blank=True, default=False)
    creation_date = CreationDateTimeField(_(u'Creation date'), editable=False)
    user          = CremeUserForeignKey(verbose_name=_(u'Owner user'))

    # TODO: use a True ForeignKey to CremeEntity (do not forget to remove the signal handlers)
    entity_content_type = ForeignKey(ContentType, related_name="memo_entity_set", editable=False)
    entity_id           = PositiveIntegerField(editable=False).set_tags(viewable=False)
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'Memo')
        verbose_name_plural = _(u'Memos')

    def __unicode__(self):
        # NB: translate for unicode can not take 2 arguments...
        return ellipsis(self.content.strip().replace('\n', ''), 25)

    def get_edit_absolute_url(self):
        return reverse('assistants__edit_memo', args=(self.id,))

    @staticmethod
    def get_memos(entity):
        return Memo.objects.filter(entity_id=entity.id).select_related('user')

    @staticmethod
    def get_memos_for_home(user):
        return Memo.objects.filter(on_homepage=True, user__in=[user] + user.teams) \
                          .select_related('user')

    @staticmethod
    def get_memos_for_ctypes(ct_ids, user):
        return Memo.objects.filter(entity_content_type__in=ct_ids, user__in=[user] + user.teams) \
                           .select_related('user')

    def get_related_entity(self):  # For generic views
        return self.creme_entity


class _GetMemos(FunctionField):
    name         = 'assistants-get_memos'
    verbose_name = _(u'Memos')
    result_type  = FunctionFieldResultsList

    def __call__(self, entity, user):
        cache = getattr(entity, '_memos_cache', None)

        if cache is None:
            cache = entity._memos_cache = list(Memo.objects.filter(entity_id=entity.id)
                                                           .order_by('-creation_date')
                                                           .values_list('content', flat=True)
                                              )

        return FunctionFieldResultsList(FunctionFieldResult(content) for content in cache)

    @classmethod
    def populate_entities(cls, entities, user):
        memos_map = defaultdict(list)

        for content, e_id in Memo.objects.filter(entity_id__in=[e.id for e in entities]) \
                                         .order_by('-creation_date') \
                                         .values_list('content', 'entity_id'):
            memos_map[e_id].append(content)

        for entity in entities:
            entity._memos_cache = memos_map[entity.id]


CremeEntity.function_fields.add(_GetMemos())
