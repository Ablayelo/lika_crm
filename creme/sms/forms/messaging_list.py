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

from django.utils.translation import ugettext_lazy as _
from django.forms import ChoiceField, ValidationError
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Filter
from creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager
from creme_core.forms.fields import MultiCremeEntityField, CremeEntityField

from persons.models import Contact

from sms.models import MessagingList


class MessagingListForm(CremeEntityForm):
    class Meta:
        model = MessagingList
        fields = ('user', 'name')


class AddContactsForm(CremeForm):
    recipients = MultiCremeEntityField(label=_(u'Contacts'),
                                       required=False, model=Contact) # other filter (name + email)??

    blocks = FieldBlockManager(('general', _(u'Contacts recipients'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(AddContactsForm, self).__init__(*args, **kwargs)
        self.messaging_list = entity

    def save(self):
        contacts = self.messaging_list.contacts

        #TODO: check if email if ok ????
        for contact in self.cleaned_data['recipients']:
            contacts.add(contact)


class AddPersonsFromFilterForm(CremeForm): #private class ???
    #NB: itseems empty_value can not be set to 'All' with a ModelChoiceField --> ChoiceField
    filters = ChoiceField(label=_(u'Filters'), choices=())

    person_model = None #Contact/Organisation

    def __init__(self, entity, *args, **kwargs):
        super(AddPersonsFromFilterForm, self).__init__(*args, **kwargs)
        self.messaging_list = entity

        choices = [(0, _(u'All'))]

        ct = ContentType.objects.get_for_model(self.person_model)
        choices.extend(Filter.objects.filter(model_ct=ct).values_list('id', 'name'))

        self.fields['filters'].choices = choices

    def get_persons_m2m(self):
        raise NotImplementedError

    def save(self):
        persons   = self.get_persons_m2m()
        filter_id = int(self.cleaned_data['filters'])

        if filter_id:
            filter_  = Filter.objects.get(pk=filter_id)
            new_persons = self.person_model.objects.filter(filter_.get_q())
        else:
            new_persons = self.person_model.objects.all()

        #TODO: check if phone number is ok ????
        for person in new_persons:
            persons.add(person)


class AddContactsFromFilterForm(AddPersonsFromFilterForm):
    blocks = FieldBlockManager(('general', _(u'Contacts recipients'), '*'))

    person_model = Contact

    def get_persons_m2m(self):
        return self.messaging_list.contacts
