# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2015  Hybird
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

from django.db.models.query import Q

from ..models import SearchConfigItem


class Searcher(object):
    def __init__(self, models, user):
        self._search_map = {sci.content_type.model_class(): sci.searchfields
                                for sci in SearchConfigItem.get_4_models(models, user)
                                    if not sci.disabled
                           }

    #def _build_query(self, research, fields, is_or=True):
    def _build_query(self, research, fields): #TODO: inline ??
        "Build a Q with all params fields"
        result_q = Q()

        for f in fields:
            #if is_or:
                #result_q |= q
            #else:
                #result_q &= q
            result_q |= Q(**{'%s__icontains' % f.name: research})

        return result_q

    def get_fields(self, model):
        "Get the list of SearchFields instances used to search in 'model'"
        return self._search_map[model]

    @property
    def models(self):
        return self._search_map.iterkeys()

    def search(self, model, research):
        """Return the models which fields contain the wanted value.
        @param model Class inheriting django.db.Model (CremeEntity)
        @param research Searched string.
        @return Queryset on model.
        """
        searchfields = self.get_fields(model)

        assert searchfields is not None # search on a disabled model ?

        return model.objects.filter(self._build_query(research, searchfields)) \
                            .distinct()
