# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from itertools import chain
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey

from creme.creme_core.models import CremeModel, CustomField 
from creme.creme_core.utils.unicode_collation import collator

class FieldNotAllowed(Exception):
    pass

class _BulkUpdateRegistry(object):
    class ModelBulkStatus(object):
        def __init__(self, model, ignore=False):
            self._model = model
            self.ignore = ignore

            self.excludes = set()
            self.expandables = set()

            self._innerforms = {}
            self._regularfields = {}

        def _reset_cache(self):
            self._regularfields = {}

        def is_expandable(self, field):
            if not isinstance(field, ForeignKey) or field.get_tag('enumerable'):
                return False

            return issubclass(field.rel.to, CremeModel) or field.name in self.expandables

        def is_updatable(self, field):
            return field.editable or isinstance(field, CustomField)

        @property
        def regular_fields(self):
            if self.ignore:
                return {}

            if self._regularfields:
                return self._regularfields

            regular_fields = chain(self._model._meta.fields, self._model._meta.many_to_many)
            self._regularfields = {field.name: field
                                      for field in regular_fields if field.name not in self.excludes
                                  }

            return self._regularfields

        @property
        def updatable_regular_fields(self):
            is_updatable = self.is_updatable
            return {key: field for key, field in self.regular_fields.iteritems() if is_updatable(field)}

        @property
        def expandable_regular_fields(self):
            is_expandable = self.is_expandable
            return {key: field for key, field in self.regular_fields.iteritems() if is_expandable(field)}

        @property
        def custom_fields(self):
            if self.ignore:
                return {}

            model = self._model

            custom_fields = {'customfield-%d' % field.pk: field for field in
                                CustomField.objects.filter(content_type=ContentType.objects.get_for_model(model))
                            }

            for field in custom_fields.values():
                field.model = self._model

            return custom_fields

        def get_field(self, name):
            if name.startswith('customfield-'):
                field = self.custom_fields.get(name)
            else:
                field = self.regular_fields.get(name)

                if field and not self.is_updatable(field):
                    raise FieldNotAllowed(u"The field %s.%s is not editable" % (self._model._meta.verbose_name, name))

            if field is None:
                raise FieldDoesNotExist(u"The field %s.%s doesn't exist" % (self._model._meta.verbose_name, name))

            return field

        def get_expandable_field(self, name):
            field = self.regular_fields.get(name)

            if field is None:
                raise FieldDoesNotExist(u"The field %s.%s doesn't exist" % (self._model._meta.verbose_name, name))

            if not self.is_expandable(field):
                raise FieldNotAllowed(u"The field %s.%s is not expandable" % (self._model._meta.verbose_name, name))

            return field

        def get_form(self, name, default=None):
            return self._innerforms.get(name, default)

    def __init__(self):
        self._status = {}

    def _get_or_create_status(self, model):
        bulk = self._status.get(model)

        if bulk is None:
            bulk = self._status[model] = self.ModelBulkStatus(model)

        return bulk

    def register(self, model, exclude=None, expandables=None, innerforms=None):
        bulk = self._get_or_create_status(model)

        if exclude:
            bulk.excludes.update(set(exclude))

        if expandables:
            bulk.expandables.update(set(expandables))

        if innerforms:
            bulk._innerforms.update(dict(innerforms))

        # merge exclusion of subclasses
        for old_model, old_bulk in self._status.iteritems():
            if old_model is not model:
                # registered subclass inherits exclusions of new model 
                if issubclass(old_model, model):
                    old_bulk.excludes.update(bulk.excludes)
                    old_bulk.expandables.update(bulk.expandables)

                # new model inherits exclusions and custom forms of registered superclass
                if issubclass(model, old_model):
                    bulk.excludes.update(old_bulk.excludes)
                    bulk.expandables.update(old_bulk.expandables)

                    merged_innerforms = dict(old_bulk._innerforms)
                    merged_innerforms.update(bulk._innerforms)
                    bulk._innerforms = merged_innerforms

        bulk._reset_cache()
        return bulk

    def ignore(self, model):
        bulk = self._get_or_create_status(model)
        bulk.ignore = True
        return bulk

    def status(self, model):
        bulk = self._status.get(model)

        # get excluded field by inheritance in case of working model is not registered yet
        if bulk is None:
            bulk = self.register(model)

        return bulk

    def get_default_field(self, model):
        fields = self.regular_fields(model)
        return fields[0]

    def get_field(self, model, field_name):
        status = self.status(model)
        field_basename, _sep_, subfield_name = field_name.partition('__')

        if subfield_name:
            parent_field = status.get_expandable_field(field_basename)
            field = self.get_field(parent_field.rel.to, subfield_name)
        else:
            field = status.get_field(field_basename)

        return field

    def get_form(self, model, field_name, default=None):
        status = self.status(model)
        field_basename, _sep_, subfield_name = field_name.partition('__')

        if subfield_name:
            field = status.get_expandable_field(field_basename)
            substatus = self.status(field.rel.to)
            subfield = substatus.get_field(subfield_name)
            form = substatus.get_form(subfield_name, default)

            return partial(form,
                           field=subfield,
                           parent_field=field) if form else None

        field = status.get_field(field_basename)
        form = status.get_form(field_basename, default)
        return partial(form, field=field) if form else None

    def is_updatable(self, model, field_name, exclude_unique=True):
        try:
            field = self.get_field(model, field_name)
        except (FieldDoesNotExist, FieldNotAllowed):
            return False

        return not (exclude_unique and field.unique)

    def is_expandable(self, model, field_name, exclude_unique=True):
        try:
            field = self.status(model).get_expandable_field(field_name)
        except (FieldDoesNotExist, FieldNotAllowed):
            return False

        return not (exclude_unique and field.unique)

    def regular_fields(self, model, expand=False, exclude_unique=True):
        sort_key = collator.sort_key

        status = self.status(model)
        is_updatable = status.is_updatable

        fields = status.regular_fields.values()

        if exclude_unique:
            fields = [field for field in fields if not field.unique]

        if expand is True:
            related_fields = self.regular_fields
            is_expandable = status.is_expandable

            field_states = [(field, is_expandable(field), is_updatable(field)) for field in fields]

            fields = [(field, related_fields(model=field.rel.to, exclude_unique=exclude_unique) if expandable else None)
                         for field, expandable, updatable in field_states if expandable or updatable
                     ]

            return sorted(fields, key=lambda f: sort_key(f[0].verbose_name))

        return sorted(filter(is_updatable, fields), key=lambda f: sort_key(f.verbose_name))

    def custom_fields(self, model):
        sort_key = collator.sort_key
        return sorted(self.status(model).custom_fields.values(), key=lambda f: sort_key(f.name))


bulk_update_registry = _BulkUpdateRegistry()

