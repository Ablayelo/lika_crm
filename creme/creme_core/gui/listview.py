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

from collections import defaultdict
from datetime import datetime
from functools import partial
import logging

from django.db.models import Q, FieldDoesNotExist
#from django.db.models.sql.constants import QUERY_TERMS
from django.utils.encoding import smart_str

from ..models import Relation, CustomField #CustomFieldEnumValue
from ..models.header_filter import HFI_FIELD, HFI_RELATION, HFI_CUSTOM, HFI_FUNCTION
from ..utils.date_range import CustomRange
from ..utils.dates import get_dt_from_str
from ..utils.meta import get_date_fields

#TODO: rename to listview_state.py

logger = logging.getLogger(__name__)

def simple_value(value):
    if value:
        if hasattr(value, '__iter__') and len(value) == 1:
            return value[0]
        return value
    return '' #TODO : Verify same semantic than "null" sql

#def int_value(value):
    #try:
        #return int(value)
    #except ValueError:
        #return 0

#def string_value(value): #todo: rename to regex_value ???
    #if value and isinstance(value, basestring):
        #return value
    #return '.*'

#def bool_value(value):
    #return bool(int_value(value))

#NB: This gather all django/creme query terms for filtering.
#    We set simple_value function to stay compatible with the API
#QUERY_TERMS_FUNC = {
    ##'exact':            lambda x: x,
    ##'iexact':           simple_value,
    ##'contains':         simple_value,
    ##'icontains':        simple_value,
    ##'gt':               simple_value,
    ##'gte':              simple_value,
    ##'lt':               simple_value,
    ##'lte':              simple_value,
    #'in':               lambda x: x if hasattr(x, '__iter__') else [],
    ##'startswith':       simple_value,
    ##'istartswith':      simple_value,
    ##'endswith':         simple_value,
    ##'iendswith':        simple_value,
    ##'range':            simple_value,
    #'year':             int_value,
    #'month':            int_value,
    #'day':              int_value,
    #'week_day':         int_value,
    #'isnull':           bool,
    ##'search':           simple_value,
    #'regex':            string_value,
    #'iregex':           string_value,
    #'creme-boolean':    bool_value,
#}

#COMMENTED on 4 april 2013
#def get_field_name_from_pattern(pattern):
    #"""
        #Gives field__sub_field for field__sub_field__pattern
        #where pattern is in QUERY_TERMS_FUNC keys
        #>>> get_field_name_from_pattern('foo__bar__icontains')
        #'foo__bar'
        #>>> get_field_name_from_pattern('foo__bar')
        #'foo__bar'
    #"""
    #patterns = pattern.split('__')
    #keys = QUERY_TERMS_FUNC.keys()
    #for p in patterns:
        #if p in keys:
            #patterns.remove(p)
            #break#Logically we should have only one query pattern

    #return "__".join(patterns)


class ListViewState(object):
    def __init__(self, **kwargs):
        get_arg = kwargs.get
        self.entity_filter_id = get_arg('filter')
        self.header_filter_id = get_arg('hfilter')
        self.page = get_arg('page')
        self.rows = get_arg('rows')
        self._search = get_arg('_search') #TODO: rename to search ?? or add property
        self.sort_order = get_arg('sort_order')
        self.sort_field = get_arg('sort_field')
        self.url = get_arg('url')
        self.research = ()
        self.extra_q = None

    def __repr__(self):
        return u'<ListViewState(efilter_id=%s, hfilter_id=%s, page=%s, rows=%s, _search=%s, sort=%s%s, url=%s, research=%s)>' % (
                    self.entity_filter_id, self.header_filter_id, self.page, self.rows,
                    self._search, self.sort_order, self.sort_field, self.url, self.research,
                )

    def register_in_session(self, request):
        session = request.session
        current_lvs = session.get(self.url or request.path) #TODO: pop() ??
        if current_lvs is not None:
            try:
                del session[self.url or request.path] #useful ???????
            except KeyError:
                pass
        session[self.url] = self

    @staticmethod
    def get_state(request, url=None):
        return request.session.get(url or request.path)

    @staticmethod
    def build_from_request(request):
        #TODO: use request.REQUEST ??
        kwargs = dict((str(k), v) for k, v in request.GET.items())
        kwargs.update(dict((str(k), v) for k, v in request.POST.items()))
        kwargs['url'] = request.path
        return ListViewState(**kwargs)

    def handle_research(self, request, header_filter_items):
        "Handle strings to use in order to filter (strings are in the request)."
        if self._search:
            if not request.POST and self.research:
                return

            REQUEST = request.REQUEST
            list_session = []

            for hfi in header_filter_items:
                if not hfi.has_a_filter:
                    continue

                name = hfi.name

                if not REQUEST.has_key(name):
                    continue

                filtered_attr = [smart_str(value.strip()) for value in REQUEST.getlist(name)]

                if filtered_attr and any(filtered_attr):
                    list_session.append((name, hfi.pk, hfi.type, hfi.filter_string, filtered_attr))

            self.research = list_session
        else:
            self.research = ()

    def _build_condition(self, pattern, value):
        #words = pattern.split('__')
        #get = QUERY_TERMS.get
        #qterm = None

        ##NB: reversed because in general the pattern is at the end
        #for word in reversed(words):
            #qterm = get(word)

            #if qterm is not None:
                #break

        #return {'__'.join('exact' if word == 'creme-boolean' else word
                            #for word in words
                         #): QUERY_TERMS_FUNC.get(qterm, simple_value)(value)
               #}
        return {pattern.replace('creme-boolean', 'exact'): simple_value(value)}

    def _date_or_None(self, value, index):
        try:
            return get_dt_from_str(value[index]).date()
        except (IndexError, AttributeError):
            pass

    def _build_date_range_q(self, name, value):
        don = partial(self._date_or_None, value=value)
        return Q(**CustomRange(don(index=0), don(index=1)).get_q_dict(name, datetime.now()))

    def _get_item_by_pk(self, hf_items, pk):
        try:
            return next(hfi for hfi in hf_items if hfi.pk == pk)
        except StopIteration:
            logger.warn('No HeaderFilterItem with pk=%s', pk)

    #TODO: move some parts of code to HeaderFilterItem (more object code) ?
    #TODO: stop using 'filter_string' (and update pickled tuple)
    def get_q_with_research(self, model, hf_items):
        query = Q()
        cf_searches = defaultdict(list)
        date_fields_names = set(field.name for field in get_date_fields(model))

        for item in self.research:
            name, hfi_pk, hfi_type, pattern, value = item #TODO: only hfi_pk & value are really useful
            hf_item = self._get_item_by_pk(hf_items, hfi_pk)

            if hf_item is None:
                continue

            if hfi_type == HFI_FIELD:
                if name in date_fields_names: #TODO: Hack for dates => refactor
                    query &= self._build_date_range_q(name, value)
                else:
                    query &= Q(**self._build_condition(pattern, value))
            elif hfi_type == HFI_RELATION:
                rct = hf_item.relation_content_type
                model_class = rct.model_class() if rct is not None else Relation

                query &= model_class.filter_in(model, hf_item.relation_predicat, value[0])
            elif hfi_type == HFI_FUNCTION:
                if hf_item.has_a_filter:
                    query &= model.function_fields.get(name).filter_in_result(value[0])
            elif hfi_type == HFI_CUSTOM:
                cf = CustomField.objects.get(pk=name)
                cf_searches[cf.field_type].append((cf, pattern, value))

        for field_type, searches in cf_searches.iteritems():
            if len(searches) == 1:
                cf, pattern, value = searches[0]
                related_name = cf.get_value_class().get_related_name()

                if cf.field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                    #value = CustomFieldEnumValue.objects.get(custom_field=cf, value=value[0]).id
                    value = value[0]

                condition = self._build_condition(pattern, value)
                condition.update({'%s__custom_field' % related_name: cf})

                query &= Q(**condition)
            else:
                for cf, pattern, value in searches:
                    pattern = pattern.partition('__')[2] #remove 'tableprefix__'

                    if field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                        #todo: DoesNotExist
                        #todo: group the queries on CustomFieldEnumValue
                        #value = CustomFieldEnumValue.objects.get(custom_field=cf, value=value[0]).id
                        value = value[0]

                    query &= Q(pk__in=cf.get_value_class().objects
                                                          .filter(custom_field=cf, 
                                                                  **self._build_condition(pattern, value)
                                                                 )
                                                          .values_list('entity_id', flat=True)
                              )

        return query

    def set_sort(self, model, field_name, order):
        "@param order string '' or '-'(reverse order)."
        sort_field = 'id'

        if field_name:
            try:
                model._meta.get_field(field_name)
            except FieldDoesNotExist as e:
                logger.warn('set_sort_field: %s', e)
            else:
                sort_field = field_name
        else:
            ordering = model._meta.ordering
            if ordering:
                sort_field = ordering[0]

        self.sort_field = sort_field
        self.sort_order = order if order == '-' else ''
