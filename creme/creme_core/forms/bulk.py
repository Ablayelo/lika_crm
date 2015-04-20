# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from functools import partial
import re

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields.related import ForeignKey, RelatedField, ManyToManyField
from django.forms.fields import ChoiceField
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.models import ModelMultipleChoiceField #model_to_dict
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_config.forms.fields import CreatorModelChoiceField

from ..gui.bulk_update import bulk_update_registry
from ..models import fields, CremeEntity
from ..models.custom_field import CustomField, CustomFieldValue

from .base import CremeForm
from .fields import CreatorEntityField, MultiCreatorEntityField
from .widgets import DateTimeWidget, CalendarWidget, UnorderedMultipleChoiceWidget


# TODO : should remove this list and use some hooks in model fields or in bulk registry to retrieve bulk widgets
_BULK_FIELD_WIDGETS = {
    models.DateField:                 CalendarWidget(),
    models.DateTimeField:             DateTimeWidget(),
    fields.CreationDateTimeField:     DateTimeWidget(),
    fields.ModificationDateTimeField: DateTimeWidget(),
}

_CUSTOMFIELD_PATTERN = re.compile('^customfield-(?P<id>[0-9]+)')
_CUSTOMFIELD_FORMAT = 'customfield-%d'

#todo : staticmethod ??
#todo: remove this when whe have a EntityForeignKey with the right model field that does the job.
# def _get_choices(model_field, user):
#     form_field = model_field.formfield()
#     choices = ()
#     if isinstance(model_field, (models.ForeignKey, models.ManyToManyField)) and issubclass(model_field.rel.to, CremeEntity):
#         fk_entities = model_field.rel.to._default_manager \
#                                         .filter(pk__in=[id_ for id_, text in form_field.choices if id_])
#         choices = ((e.id, e) for e in EntityCredentials.filter(user, fk_entities))
# 
#         if model_field.null and isinstance(model_field, models.ForeignKey):
#             choices = chain([(u"", ugettext(u"None"))], choices)
#     elif hasattr(form_field, 'choices'):
#         choices = form_field.choices
#     return choices


# class _EntitiesEditForm(CremeForm):
#     entities_lbl = CharField(label=_(u"Entities to update"), required=False, widget=Label)
#     field_name   = ChoiceField(label=_(u"Field to update"))
#     field_value  = CharField(label=_(u"Value"), required=False)
# 
#     def get_cfields_cache(self):
#         return {cf.pk: cf for cf in CustomField.objects.filter(content_type=self.ct)}
# 
#     def __init__(self, model, subjects, forbidden_subjects, user, *args, **kwargs):
#         super(_EntitiesEditForm, self).__init__(user, *args, **kwargs)
# 
#         self.subjects = subjects
#         self.user = user
#         self.model = model
#         self.ct = ContentType.objects.get_for_model(model)
#         self._cfields_cache = None
# 
#         fields = self.fields
# 
#         if subjects:
#             fields['entities_lbl'].initial = related2unicode(subjects[0], user) \
#                                              if hasattr(subjects[0], 'get_related_entity') \
#                                              else entities2unicode(subjects, user)
#         else:
#             fields['entities_lbl'].initial = ugettext(u'NONE !')
# 
#         if forbidden_subjects:
#             fields['bad_entities_lbl'] = CharField(label=ugettext(u"Uneditable entities"),
#                                                    widget=Label,
#                                                    initial=entities2unicode(forbidden_subjects, user)
#                                                   )
# 
#     @staticmethod
#     def get_field(model, field_name, cfields_cache=None, instance=None):
#         field = None
#         matches = _CUSTOMFIELD_PATTERN.match(field_name)
# 
#         if matches is not None:
#             customfield_id = int(matches.group('id'))
#             field = cfields_cache.get(customfield_id) if cfields_cache else None
# 
#             if field is None:
#                 field = CustomField.objects.get(pk=customfield_id)
# 
#                 if cfields_cache:
#                     cfields_cache[customfield_id] = field
# 
#             return field, True
# 
#         try:
#             return model._meta.get_field(field_name), False
#         except FieldDoesNotExist:
#             return None, False
# 
#     @staticmethod
#     def get_custom_formfield(model_field, instance=None):
#         if instance is not None:
#             return model_field.get_formfield(instance.get_custom_value(model_field))
# 
#         return model_field.get_formfield(None)
# 
#     @staticmethod
#     def get_updatable_formfield(model_field, user, instance=None):
#         form_field = model_field.formfield()
# 
#         if isinstance(model_field, RelatedField):
#             if isinstance(model_field, ForeignKey) and issubclass(model_field.rel.to, CremeEntity):
#                 form_field = CreatorEntityField(model_field.rel.to, label=form_field.label, required=form_field.required)
#             else:
#                 form_field.choices = _get_choices(model_field, user)
# 
#         form_field.widget = _FIELDS_WIDGETS.get(model_field.__class__) or form_field.widget
#         form_field.user = user
# 
#         if instance:
#             form_field.initial = model_to_dict(instance, [model_field.name])[model_field.name]
# 
#         return form_field
# 
#     def clean(self, *args, **kwargs):
#         super(_EntitiesEditForm, self).clean(*args, **kwargs)
#         cleaned_data = self.cleaned_data
# 
#         if self._errors:
#             return cleaned_data
# 
#         field_name  = cleaned_data['field_name']
# 
#         model_field, is_custom = self.get_field(self.model, field_name, self._cfields_cache)
# 
#         if model_field is None:
#             raise ValidationError(_(u'Select a valid field.'))
# 
#         if is_custom:
#             self._custom_field = model_field
# 
#             field_klass = model_field.get_value_class()
#             field_value = cleaned_data['field_value']
# 
#             if field_value and not issubclass(field_klass, CustomFieldMultiEnum):
#                 field_value = field_value[0]
# 
#             form_field = model_field.get_formfield(None)
#             #form_field.initial = field_value #todo: useful ??
#             cleaned_value = form_field.clean(form_field.widget.value_from_datadict(self.data, self.files, 'field_value'))
# 
#             if cleaned_value and issubclass(field_klass, CustomFieldEnum):
#                 if not CustomFieldEnumValue.objects.filter(pk=cleaned_value).exists():
#                     raise ValidationError(_(u'Select a valid choice.'))
#         else:
#             self._custom_field = None
# 
#             form_field = self.get_updatable_formfield(model_field, self.user)
# 
#             if isinstance(form_field.widget, MultiWidget):
#                 field_value = form_field.widget.value_from_datadict(self.data, self.files, self.add_prefix('field_value'))
#             else:
#                 field_value = cleaned_data['field_value']
# 
#             cleaned_value = cleaned_data['field_value'] = form_field.clean(field_value)
# 
#             if isinstance(cleaned_value, CremeEntity) and not self.user.has_perm_to_view(cleaned_value):
#                 raise ValidationError(ugettext(u"You can't view this value, so you can't set it."))
# 
#             if cleaned_value is None and not model_field.null:
#                 raise ValidationError(ugettext(u'This field is required.'))
# 
#             if not (cleaned_value is not None or model_field.blank):
#                 raise ValidationError(ugettext(u'This field is required.'))
# 
#             #Checking valid choices & credentials
#             if cleaned_value and isinstance(model_field, RelatedField) and issubclass(model_field.rel.to, CremeEntity):
#                 allowed_choices = [choice[0] for choice in _get_choices(model_field, self.user)]
# 
#                 if isinstance(cleaned_value, list):
#                     for field_val in cleaned_value:
#                         if field_val.pk not in allowed_choices:
#                             raise ValidationError(_(u'Select a valid choice.'))
#                 elif cleaned_value.pk not in allowed_choices:
#                     raise ValidationError(_(u'Select a valid choice.'))
# 
#             for subject in self.subjects:
#                 setattr(subject, field_name, cleaned_value)
#                 subject.full_clean()
# 
#         cleaned_data['field_value'] = cleaned_value
# 
#         return cleaned_data
# 
#     def save(self):
#         custom_field = self._custom_field
# 
#         if custom_field is not None:
#             CustomFieldValue.save_values_for_entities(custom_field, self.subjects,
#                                                       self.cleaned_data['field_value']
#                                                      )
#         else:
#             for subject in self.subjects:
#                 subject.save()
# 
# 
# class EntitiesBulkUpdateForm(_EntitiesEditForm):
#     def __init__(self, model, subjects, forbidden_subjects, user, *args, **kwargs):
#         super(EntitiesBulkUpdateForm, self).__init__(model, subjects, forbidden_subjects, user, *args, **kwargs)
# 
#         self._cfields_cache = self.get_cfields_cache()
# 
#         sort = partial(sorted, key=lambda k: ugettext(k[1]))
# 
#         bulk_status = bulk_update_registry.status(model)
#         innerform_names = set(bulk_status.innerforms.keys())
#         regular_fields = (f for f in bulk_status.updatables() if f.name not in innerform_names)
# 
#         f_field_name = self.fields['field_name']
#         f_field_name.widget = AdaptiveWidget(ct_id=self.ct.id)
#         f_field_name.choices = (
#             (ugettext(u"Regular fields"), sort((unicode(field.name), unicode(field.verbose_name)) for field in regular_fields)),
#             (ugettext(u"Custom fields"),  sort((_CUSTOMFIELD_FORMAT % cf.id, cf.name) for cf in self._cfields_cache.itervalues())),
#           )
# 
# 
# class EntityInnerEditForm(CremeModelForm):
#     def __init__(self, model, field_name, user, instance, **kwargs):
#         """@param field_id Name of a regular field, or pk (as int or string) for CustomFields."""
#         super(EntityInnerEditForm, self).__init__(user, instance=instance, **kwargs)
#         model_field, is_custom = _EntitiesEditForm.get_field(model, field_name)
# 
#         self.field_name = field_name
#         self.model_field = model_field
#         self.is_custom = is_custom
#         self.verbose_fieldname = FieldInfo(model, field_name).verbose_name if not is_custom else model_field.name
# 
#         if is_custom:
#             form_field = EntitiesBulkUpdateForm.get_custom_formfield(model_field, instance)
#         else:
#             form_field = EntitiesBulkUpdateForm.get_updatable_formfield(model_field, user, instance)
# 
#         fields = self.fields
#         fields['field_value'] = form_field
# 
#     def save(self):
#         instance = self.instance
#         field_value = self.cleaned_data['field_value']
# 
#         if self.is_custom:
#             CustomFieldValue.save_values_for_entities(self.model_field, [instance],
#                                                       self.cleaned_data['field_value']
#                                                      )
#         else:
#             setattr(instance, self.field_name, field_value)
#             instance.save()

class BulkFieldSelectWidget(Select):
    def build_attrs(self, extra_attrs=None, **kwargs):
        attrs = super(BulkFieldSelectWidget, self).build_attrs(extra_attrs, **kwargs)
        attrs['onchange'] = 'creme.dialog.redirect($(this).val(), $(this));'
        return attrs


class BulkForm(CremeForm):
    def __init__(self, field, user, entities, is_bulk, parent_field=None, **kwargs):
        super(BulkForm, self).__init__(user, **kwargs)
        is_subfield = parent_field is not None

        self.is_bulk = is_bulk
        self.is_subfield = is_subfield
        self.is_custom = isinstance(field, CustomField)

        self.field_name = field.name if not self.is_custom else 'customfield-%d' % field.pk
        self.model_field = field
        self.model_parent_field = parent_field
        self.entities = entities

        if is_bulk:
            #choices_model = parent_field.model if is_subfield else field.model
            choices_model = parent_field.model if is_subfield else entities[0].__class__
            choices = self._bulk_model_choices(choices_model, entities)
            initial = self._bulk_url(choices_model,
                                     parent_field.name + '__' + self.field_name if is_subfield else self.field_name,
                                     entities,
                                    )

            self.fields['_bulk_fieldname'] = ChoiceField(choices=choices,
                                                         label=_(u"Field to update"),
                                                         initial=initial,
                                                         widget=BulkFieldSelectWidget,
                                                         required=False,
                                                        )

    def _bulk_url(self, model, fieldname, entities):
        return '/creme_core/entity/edit/bulk/%s/%s/field/%s' % (
                    ContentType.objects.get_for_model(model).pk,
                    ','.join(str(e.pk) for e in entities),
                    fieldname,
                )

    def _bulk_formfield(self, user, instance=None):
        if self.is_custom:
            return self._bulk_custom_formfield(self.model_field, instance)

        return self._bulk_updatable_formfield(self.model_field, user, instance)

    def _bulk_model_choices(self, model, entities):
        regular_fields = bulk_update_registry.regular_fields(model, expand=True)
        custom_fields = bulk_update_registry.custom_fields(model)

        url = self._bulk_url(model, '%s', entities)

        choices = []
        sub_choices = []

        for field, subfields in regular_fields:
            if not subfields:
                choices.append((url % unicode(field.name), unicode(field.verbose_name)))
            else:
                sub_choices.append((unicode(field.verbose_name),
                                    [(url % unicode(field.name + '__' + subfield.name), unicode(subfield.verbose_name))
                                        for subfield in subfields
                                    ],
                                   )
                                  )

        if custom_fields:
            choices.append((ugettext(u"Custom fields"),
                            [(url % (_CUSTOMFIELD_FORMAT % field.id), field.name)
                                for field in custom_fields
                            ]
                           )
                          )

        return choices + sub_choices

    def _bulk_custom_formfield(self, model_field, instance=None):
        if instance is not None:
            return model_field.get_formfield(instance.get_custom_value(model_field))

        return model_field.get_formfield(None)

    def _bulk_related_formfield(self, model_field, user, instance=None):
        form_field = model_field.formfield()
        related_to = model_field.rel.to

        if isinstance(model_field, ForeignKey):
            if issubclass(related_to, CremeEntity):
                form_field = CreatorEntityField(model=related_to, label=form_field.label,
                                                required=form_field.required,
                                               )
            else:
                form_field = CreatorModelChoiceField(queryset=related_to.objects.all(),
                                                     label=form_field.label,
                                                     required=form_field.required,
                                                    )
        elif isinstance(model_field, ManyToManyField):
            if issubclass(related_to, CremeEntity):
                form_field = MultiCreatorEntityField(model=related_to,
                                                     label=form_field.label,
                                                     required=form_field.required,
                                                    )
            else:
                form_field = ModelMultipleChoiceField(label=form_field.label,
                                                      queryset=related_to.objects.all(),
                                                      required=form_field.required,
                                                      widget=UnorderedMultipleChoiceWidget,
                                                     )

        return form_field

    def _bulk_updatable_formfield(self, model_field, user, instance=None):
        if isinstance(model_field, RelatedField):
            form_field = self._bulk_related_formfield(model_field, user, instance)
        else:
            form_field = model_field.formfield()
            # TODO : should remove this list and use some hooks in model fields in bulk registry to retrieve widgets
            form_field.widget = _BULK_FIELD_WIDGETS.get(model_field.__class__) or form_field.widget

        form_field.user = user

        if instance and self.is_subfield:
            instance = getattr(instance, self.model_parent_field.name)

        if instance:
            form_field.initial = getattr(instance, model_field.name)

        return form_field

    def _bulk_clean_entity(self, entity, values):
        for key, value in values.iteritems():
            setattr(entity, key, value)

        entity.full_clean()
        return entity

    def _bulk_clean_subfield(self, entity, values):
        instance = getattr(entity, self.model_parent_field.name)

        if instance is None:
            #TODO: code + _bulk_error_messages + params
            raise ValidationError(ugettext(u'The field %s is empty') % self.model_parent_field.verbose_name)

        return self._bulk_clean_entity(instance, values)

    def _bulk_clean_entities(self, entities, values):
        invalid_entities = []
        cleaned_entities = []
        clean = self._bulk_clean_subfield if self.is_subfield else self._bulk_clean_entity
        clean = partial(clean, values=values)

        for entity in entities:
            try:
                cleaned_entities.append(clean(entity))
            except ValidationError as e:
                invalid_entities.append((entity, e))

        return cleaned_entities, invalid_entities

    def _bulk_error_messages(self, entity, error):
        if not hasattr(error, 'message_dict'):
            return {NON_FIELD_ERRORS: error.messages}

        fields = {field.name: field
                    for field in (entity._meta.fields + entity._meta.many_to_many)
                 }
        messages = []

        for key, value in error.message_dict.iteritems():
            field = fields.get(key)
            message = ''.join(value) if isinstance(value, (list, tuple)) else value
            messages.append(u'%s : %s' % (ugettext(field.verbose_name), message)
                            if field is not None else
                            message
                           )

        return {NON_FIELD_ERRORS: messages}


class BulkDefaultEditForm(BulkForm):
    def __init__(self, field, user, entities, is_bulk=False, **kwargs):
        super(BulkDefaultEditForm, self).__init__(field, user, entities, is_bulk, **kwargs)

        instance = entities[0] if not is_bulk else None
        form_field = self._bulk_formfield(user, instance)

        self.fields['field_value'] = form_field

    def clean_field_value(self):
        field_value = self.cleaned_data.get('field_value')

        # TODO : CreatorEntityField doesn't check permission.
        if isinstance(field_value, CremeEntity) and not self.user.has_perm_to_view(field_value):
            raise ValidationError(ugettext(u"You can't view this value, so you can't set it."))

        return field_value

    def clean(self):
        if self.errors:
            return self.cleaned_data

        cleaned_data = super(BulkDefaultEditForm, self).clean()

        # in bulk mode get all entities, only the first one elsewhere
        entities = self.entities if self.is_bulk else self.entities[:1]

        # skip model clean step for customfields
        if self.is_custom:
            self.bulk_cleaned_entities = entities
            self.bulk_invalid_entities = []
            return cleaned_data

        values = {self.field_name: cleaned_data.get('field_value')}

        # update attribute <field_name> of each instance of entity and filter valid ones.
        self.bulk_cleaned_entities, self.bulk_invalid_entities = self._bulk_clean_entities(entities, values)

#         if not self.is_bulk and self.bulk_invalid_entities:
#             self._errors[self.field_name] = self.error_class(self.bulk_invalid_entities[0][1].messages)
        if not self.is_bulk and self.bulk_invalid_entities:
            entity, error = self.bulk_invalid_entities[0]
            raise ValidationError(self._bulk_error_messages(entity, error))

        return cleaned_data

    def save(self):
        entities = self.bulk_cleaned_entities
        field_value = self.cleaned_data['field_value']

        if self.is_custom:
            CustomFieldValue.save_values_for_entities(self.model_field, entities, field_value)
        else:
            for entity in entities:
                entity.save()
