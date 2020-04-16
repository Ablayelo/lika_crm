# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020  Hybird
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
from typing import Dict, Iterator, Type, TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

from .core.graph.fetcher import GraphFetcher, SimpleGraphFetcher

if TYPE_CHECKING:
    from .models import AbstractReportGraph

logger = logging.getLogger(__name__)


class GraphFetcherRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self, default_class: Type[GraphFetcher]):
        self._fetcher_classes: Dict[str, Type[GraphFetcher]] = {}
        self.default_class = default_class

    def register(self, *fetcher_classes: Type[GraphFetcher]) -> 'GraphFetcherRegistry':
        set_default = self._fetcher_classes.setdefault

        for fetcher_cls in fetcher_classes:
            if set_default(fetcher_cls.type_id, fetcher_cls) is not fetcher_cls:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register(): '
                    f'the ID "{fetcher_cls.type_id}" is already used'
                    f'(trying to register class {fetcher_cls}).'
                )

        return self

    def get(self,
            graph: 'AbstractReportGraph',
            fetcher_dict: dict) -> GraphFetcher:
        fetcher_type_id = fetcher_dict.get(GraphFetcher.DICT_KEY_TYPE)
        fetcher_cls = self._fetcher_classes.get(fetcher_type_id)
        if fetcher_cls is None:
            logger.warning(
                '%s.get(): invalid ID "%s" for fetcher (basic fetcher is used).',
                type(self).__name__, fetcher_type_id,
            )

            fetcher = self.default_class(graph=graph)
            fetcher.error = _('Invalid volatile link ; please contact your administrator.')

            return fetcher

        return fetcher_cls(
            graph=graph,
            value=fetcher_dict.get(GraphFetcher.DICT_KEY_VALUE),
        )

    @property
    def fetcher_classes(self) -> Iterator[Type[GraphFetcher]]:
        return iter(self._fetcher_classes.values())


graph_fetcher_registry = GraphFetcherRegistry(SimpleGraphFetcher)
