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

from functools import partial
from itertools import chain
from logging import info

from django.db.models import Q, ManyToManyField
from django.forms.models import modelform_factory
from django.forms import Field, BooleanField, ModelChoiceField, ModelMultipleChoiceField, ValidationError, IntegerField
from django.forms.widgets import SelectMultiple, HiddenInput
from django.forms.util import flatatt
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_unicode
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_core.models import CremePropertyType, CremeProperty, RelationType, Relation, CremeEntity
from creme_core.gui.csv_import import csv_form_registry
from base import CremeForm, CremeModelForm, FieldBlockManager
from fields import MultiRelationEntityField, CremeEntityField
from widgets import UnorderedMultipleChoiceWidget
from validators import validate_linkable_entities

from documents.models import Document


def _csv_to_list(line_str):
    #TODO: improve the 'parsing' method ?? (what about a',' between the "" ??)
    #      factorise with csv export ??? use csv.Sniffer class to guess csv format ??
    return [word.strip('"').strip() for word in smart_unicode(line_str.strip()).split(',')]


class CSVUploadForm(CremeForm):
    csv_step       = IntegerField(widget=HiddenInput)
    csv_document   = CremeEntityField(label=_(u'CSV file'), model=Document,
                                      help_text=_(u"""A file that contains the fields values of an entity on each line, separated by commas and each surrounded by quotation marks "."""))
    csv_has_header = BooleanField(label=_(u'Header present ?'), required=False,
                                  help_text=_(u"""Does the first line of the line contain the header of the columns (eg: "Last name","First name") ?"""))

    def __init__(self, *args, **kwargs):
        super(CSVUploadForm, self).__init__(*args, **kwargs)
        self._csv_header = None

    @property
    def csv_header(self):
        return self._csv_header

    def clean(self):
        cleaned_data = self.cleaned_data
        csv_document = cleaned_data['csv_document']

        if not self.user.has_perm('creme_core.view_entity', csv_document):
            raise ValidationError(ugettext("You have not the credentials to read this document."))

        if cleaned_data['csv_has_header']:
            try:
                filedata = csv_document.filedata
                filedata.open()
                self._csv_header = _csv_to_list(filedata.readline())
            except Exception, e:
                raise ValidationError(ugettext("Error reading document: %s.") % e)
            finally:
                filedata.close()

        return cleaned_data


class LimitedList(object):
    def __init__(self, max_size):
        self._max_size = max_size
        self._size = 0
        self._data = []

    def append(self, obj):
        if self._size < self._max_size:
            self._data.append(obj)
        self._size += 1

    @property
    def max_size(self):
        return self._max_size

    def __len__(self):
        return self._size

    def __nonzero__(self):
        return bool(self._size)

    def __iter__(self):
        return iter(self._data)


class CSVExtractor(object):
    def __init__(self, column_index, default_value, value_castor):
        self._column_index  = column_index
        self._default_value = default_value
        self._value_castor  = value_castor
        self._subfield_search = None
        self._fk_model = None
        self._m2m = None
        self._fk_form = None

    def set_subfield_search(self, subfield_search, subfield_model, multiple, create_if_unfound):
        self._subfield_search = str(subfield_search)
        self._fk_model  = subfield_model
        self._m2m = multiple
        self._fk_form = modelform_factory(subfield_model)

    def extract_value(self, line):
        if self._column_index: #0 -> not in csv
            value = line[self._column_index - 1]

            if self._subfield_search:
                data = {self._subfield_search: value}

                try:
                    retriever = self._fk_model.objects.filter if self._m2m else self._fk_model.objects.get
                    return retriever(**data) #TODO: improve self._value_castor avoid te direct 'return' ?
                except Exception, e:
                    fk_form = self._fk_form

                    if fk_form: #try to create the referenced instance
                        creator = fk_form(data=data)

                        if creator.is_valid():
                           creator.save()
                           return creator.instance #TODO: improve self._value_castor avoid te direct 'return' ?
                        else:
                            info('Exception while extracting value [%s]: tried to retrieve and then building "%s" on %s', e, value, self._fk_model)
                    else:
                        info('Exception while extracting value [%s]: tried to retrieve "%s" on %s', e, value, self._fk_model) #TODO: log error in errors list shown to user ??

                    value = None

            if not value:
                value = self._default_value
        else:
            value = self._default_value

        return self._value_castor(value)


class CSVExtractorWidget(SelectMultiple):
    def __init__(self, *args, **kwargs):
        super(CSVExtractorWidget, self).__init__(*args, **kwargs)
        self.default_value_widget = None
        self.subfield_select = None
        self.propose_creation = False

    def _render_select(self, name, choices, sel_val, attrs=None):
        output = ['<select %s>' % flatatt(self.build_attrs(attrs, name=name))]

        output.extend(u"""<option value="%s" %s>%s</option>""" % (
                            opt_value, (u'selected="selected"' if sel_val == opt_value else u''), opt_label
                        ) for opt_value, opt_label in choices
                     )

        output.append('</select>')

        return u'\n'.join(output)


    def render(self, name, value, attrs=None, choices=()):
        value = value or {}
        attrs = self.build_attrs(attrs, name=name)
        output = [u'<table %s><tbody><tr><td>' % flatatt(attrs)]

        out_append = output.append
        rselect    = self._render_select

        out_append(rselect("%s_colselect" % name, choices=chain(self.choices, choices),
                           sel_val=int(value.get('selected_column', -1)),
                           attrs={'class': 'csv_col_select'}))

        if self.subfield_select:
            out_append(u"""</td>
                           <td class="csv_subfields_select">%(label)s %(select)s %(check)s
                            <script type="text/javascript">
                                $(document).ready(function() {
                                    creme.forms.toCSVImportField('%(id)s');
                                });
                            </script>""" % {
                          'label':  ugettext(u'Search by:'),
                          'select': rselect("%s_subfield" % name, choices=self.subfield_select, sel_val=value.get('subfield_search')),
                          'check':  '' if not self.propose_creation else \
                                    '&nbsp;%s <input type="checkbox" name="%s_create" %s>' % (
                                           ugettext(u'Create if not found ?'),
                                           name,
                                           'checked' if value.get('subfield_create') else '',
                                        ),
                          'id':     attrs['id'],
                        })

        out_append(u"""</td><td>&nbsp;%s:%s</td></tr></tbody></table>""" % (
                        ugettext(u"Default value"),
                        self.default_value_widget.render("%s_defval" % name, value.get('default_value')),
                    )
                  )

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {
                'selected_column':  get("%s_colselect" % name),
                'subfield_search':  get("%s_subfield" % name),
                'subfield_create':  get("%s_create" % name, False),
                'default_value':    self.default_value_widget.value_from_datadict(data, files, "%s_defval" % name)
               }


class CSVExtractorField(Field):
    default_error_messages = {
    }

    _EXCLUDED_SUBFIELDS = frozenset(('id', 'entity_type', 'is_deleted', 'is_actived', 'cremeentity_ptr', 'header_filter_search_field'))

    def __init__(self, choices, modelfield, modelform_field, *args, **kwargs):
        super(CSVExtractorField, self).__init__(self, widget=CSVExtractorWidget, *args, **kwargs)
        self.required = modelform_field.required
        self._modelfield = modelfield
        self._can_create = False #if True and field is a FK/M2M -> the referenced model can be created

        widget = self.widget

        self._choices = choices
        widget.choices = choices

        self._original_field = modelform_field
        widget.default_value_widget = modelform_field.widget

        if modelfield.rel:
            klass = modelfield.rel.to
            is_entity = issubclass(klass, CremeEntity)
            ffilter = (lambda fieldname: fieldname not in self._EXCLUDED_SUBFIELDS) if is_entity else \
                       lambda fieldname: fieldname != 'id'

            sf_choices = [(field.name, field.verbose_name) for field in klass._meta.fields if ffilter(field.name)]
            widget.subfield_select = sf_choices
            widget.propose_creation = self._can_create = (not is_entity) and (len(sf_choices) == 1) #TODO: creation creds too...

    def clean(self, value):
        col_index = int(value['selected_column'])
        def_value = value['default_value']

        if self.required and not col_index:
            if not def_value:
                raise ValidationError(self.error_messages['required'])

            self._original_field.clean(def_value) #to raise ValidationError if needed

        #TODO: check that col_index is in self._choices ???

        subfield_create = value['subfield_create']

        if not self._can_create and subfield_create:
            raise ValidationError("You can not create: %s" % self._modelfield)

        extractor = CSVExtractor(col_index, def_value, self._original_field.clean)

        subfield_search = value['subfield_search']
        if subfield_search:
            modelfield = self._modelfield
            extractor.set_subfield_search(subfield_search, modelfield.rel.to,
                                          multiple=isinstance(modelfield, ManyToManyField),
                                          create_if_unfound=subfield_create,
                                         )

        return extractor


class CSVImportForm(CremeModelForm):
    csv_step       = IntegerField(widget=HiddenInput)
    csv_document   = IntegerField(widget=HiddenInput)
    csv_has_header = BooleanField(widget=HiddenInput, required=False)

    blocks = FieldBlockManager(('general', _(u'Importing from a CSV file'), '*'))

    def __init__(self, *args, **kwargs):
        super(CSVImportForm, self).__init__(*args, **kwargs)
        self.import_errors = LimitedList(50)
        self.imported_objects_count = 0

    #NB: hack to bypass the model validation (see form_factory() comment)
    def _post_clean(self):
        pass

    def clean_csv_document(self):
        document_id = self.cleaned_data['csv_document']

        try:
            csv_document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise ValidationError(ugettext("This document doesn't exist or doesn't exist any more."))

        if not self.user.has_perm('creme_core.view_entity', csv_document):
            raise ValidationError(ugettext("You have not the credentials to read this document."))

        return csv_document

    def _post_instance_creation(self, instance, line): #overload me
        pass

    def save(self):
        model_class = self._meta.model
        get_cleaned = self.cleaned_data.get

        exclude = frozenset(self._meta.exclude)
        regular_fields   = []
        extractor_fields = []

        for field in model_class._meta.fields:
            fname = field.name

            if fname in exclude:
                continue

            cleaned = get_cleaned(fname)
            if not cleaned:
                continue

            good_fields = extractor_fields if isinstance(cleaned, CSVExtractor) else regular_fields
            good_fields.append((fname, cleaned))

        filedata = self.cleaned_data['csv_document'].filedata
        filedata.open()
        lines = filedata.xreadlines()

        if get_cleaned('csv_has_header'):
            lines.next()

        for file_line in lines:
            try:
                line = _csv_to_list(file_line)

                instance = model_class()

                for name, cleaned_field in regular_fields:
                    setattr(instance, name, cleaned_field)

                for name, cleaned_field in extractor_fields:
                    setattr(instance, name, cleaned_field.extract_value(line))

                instance.save()
                self.imported_objects_count += 1

                self._post_instance_creation(instance, line)

                for m2m in self._meta.model._meta.many_to_many:
                    extractor = get_cleaned(m2m.name) #can be a regular_field ????
                    if extractor:
                        setattr(instance, m2m.name, extractor.extract_value(line))
            except Exception, e:
                self.import_errors.append((line, str(e)))
                info('Exception in CSV importing: %s (%s)', e, type(e))

        filedata.close()


class CSVImportForm4CremeEntity(CSVImportForm):
    user           = ModelChoiceField(label=_('User'), queryset=User.objects.all(), empty_label=None)
    property_types = ModelMultipleChoiceField(label=_(u'Properties'), required=False,
                                              queryset=CremePropertyType.objects.none(),
                                              widget=UnorderedMultipleChoiceWidget)
    relations      = MultiRelationEntityField(label=_(u'Relations'), required=False)

    blocks = FieldBlockManager(('general',    _(u'Generic information'),  '*'),
                               ('properties', _(u'Related properties'),   ('property_types',)),
                               ('relations',  _(u'Associated relations'), ('relations',)),
                              )

    class Meta:
        exclude = ('is_deleted', 'is_actived')

    def __init__(self, *args, **kwargs):
        super(CSVImportForm4CremeEntity, self).__init__(*args, **kwargs)

        fields = self.fields
        ct     = ContentType.objects.get_for_model(self._meta.model)

        fields['property_types'].queryset = CremePropertyType.objects.filter(Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True))
        fields['relations'].set_allowed_rtypes(RelationType.get_compatible_ones(ct).values_list('id', flat=True))
        fields['user'].initial = self.user.id

    def clean_relations(self):
        relations = self.cleaned_data['relations']
        user = self.user

        #TODO: self._check_duplicates(relations, user) #see RelationCreateForm
        validate_linkable_entities([entity for rt_id, entity in relations], user)

        return relations

    def _post_instance_creation(self, instance, line):
        cleaned_data = self.cleaned_data

        for prop_type in cleaned_data['property_types']:
            CremeProperty(type=prop_type, creme_entity=instance).save()

        create_relation = partial(Relation.objects.create, user=instance.user, subject_entity=instance)

        for relationtype, entity in cleaned_data['relations']:
            create_relation(type=relationtype, object_entity=entity)


def extractorfield_factory(modelfield, header_dict, choices):
    formfield = modelfield.formfield()

    if not formfield: #happens for crementity_ptr (OneToOneField)
        return None

    selected_column = header_dict.get(modelfield.verbose_name.lower())
    if selected_column is None:
        selected_column = header_dict.get(modelfield.name.lower(), 0)

    return CSVExtractorField(choices, modelfield, formfield,
                             label=modelfield.verbose_name,
                             initial={'selected_column': selected_column}
                            )


#NB: we use ModelForm to get the all the django machinery to build a form from a model
#    bit we need to avoid the model validation, because we are are not building a true
#    'self.instance', but a set of instances ; we just use the regular form validation.
def form_factory(ct, header):
    choices = [(0, _('Not in the CSV file'))]
    header_dict = {}

    if header:
        fstring = ugettext(u'Column %(index)s - %(name)s')

        for i, col_name in enumerate(header):
            i += 1
            choices.append((i, fstring % {'index': i, 'name': col_name}))
            header_dict[col_name.lower()] = i
    else:
        fstring = ugettext(u'Column %i')
        choices.extend((i, fstring % i) for i in xrange(1, 21))

    model_class = ct.model_class()
    customform_factory = csv_form_registry.get(ct)

    if customform_factory:
        base_form_class = customform_factory(header_dict, choices)
    elif issubclass(model_class, CremeEntity):
        base_form_class = CSVImportForm4CremeEntity
    else:
        base_form_class = CSVImportForm

    return modelform_factory(model_class, form=base_form_class,
                             formfield_callback=partial(extractorfield_factory, header_dict=header_dict, choices=choices)
                            )
