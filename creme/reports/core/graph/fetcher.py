# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2020  Hybird
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
import logging
from typing import (
    Optional, Type, Union,
    Iterator,
    List, Tuple,
    TYPE_CHECKING,
)
import warnings

from django.utils.translation import (
    gettext_lazy as _,
    gettext,
    pgettext,
)
from django.db.models import FieldDoesNotExist, ForeignKey, Q

from creme.creme_core.models import (
    CremeEntity,
    RelationType,
    FieldsConfig,
    InstanceBrickConfigItem,
)
from creme.creme_core.utils.meta import ModelFieldEnumerator

from creme.reports import constants

if TYPE_CHECKING:
    from creme.creme_core.gui.bricks import InstanceBrick
    from creme.reports.models import AbstractReportGraph

logger = logging.getLogger(__name__)


class GraphFetcher:
    """A graph fetcher can fetch the result of a given ReportGraph, with or without
    a volatile link.
    It stores the verbose name of this link (for UI), and an error if the link data
    were invalid.
    """
    type_id = ''
    verbose_name = ''
    choices_group_name = ''
    error: Optional[str] = None

    DICT_KEY_TYPE  = 'type'
    DICT_KEY_VALUE = 'value'
    DICT_KEYS = (DICT_KEY_TYPE, DICT_KEY_VALUE)

    class IncompatibleContentType(Exception):
        pass

    class UselessResult(Exception):
        pass

    # def __init__(self, graph):
    def __init__(self, graph: 'AbstractReportGraph', value=None):
        self.graph = graph
        self.value = value
        # self.error = None
        # self.verbose_volatile_column: str = _('No volatile column')

    def as_dict_items(self):
        yield self.DICT_KEY_TYPE, self.type_id

        if self.value:
            yield self.DICT_KEY_VALUE, self.value

    @classmethod
    def choices(cls, model: Type[CremeEntity]) -> Iterator[Tuple[str, Union[str, List[Tuple[str, str]]]]]:
        raise NotImplementedError()

    def create_brick_config_item(self, brick_class: Optional[Type['InstanceBrick']] = None) -> InstanceBrickConfigItem:
        if brick_class is None:
            from creme.reports.bricks import ReportGraphBrick
            brick_class = ReportGraphBrick

        ibci = InstanceBrickConfigItem(
            entity=self.graph,
            brick_class_id=brick_class.id_,
        )

        for k, v in self.as_dict_items():
            ibci.set_extra_data(key=k, value=v)

        # TODO: argument to not commit ?
        ibci.save()

        return ibci

    def fetch(self, user, order: str = 'ASC') -> Tuple[List[str], list]:
        return self.graph.fetch(user=user, order=order)

    def _aux_fetch_4_entity(self,
                            entity: CremeEntity,
                            user,
                            order: str):
        "To be overload in child classes."
        return self.fetch(user=user, order=order)

    def fetch_4_entity(self,
                       entity: CremeEntity,
                       user,
                       order: str = 'ASC') -> Tuple[List[str], list]:
        """
        Data of the AbstractReportGraph narrowed to the entities linked to one
        entity (eg: the entity corresponding to the visited detail-view).
        @param entity: Entity used to narrow the results.
        @param user: logged user.
        @param order: 'ASC' or 'DESC'.
        @return: see <ReportGraphHand.fetch()>.
        @raise GraphFetcher.IncompatibleContentType if the ContentType of 'entity'
               is wrong (ie: the configuration should probably be fixed).
        @raise GraphFetcher.UselessResult if fetching data for 'entity' is useless
               (eg: it does mean anything in the business logic).
        """
        return (
            [], []
        ) if self.error else self._aux_fetch_4_entity(
            entity=entity, user=user, order=order,
        )

    # @property
    # def verbose_name(self) -> str:
    #     return f'{self.graph} - {self.verbose_volatile_column}'


class SimpleGraphFetcher(GraphFetcher):
    type_id = constants.RGF_NOLINK

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = _('No volatile column')

        if self.value:
            self.error = _('No value is needed.')

    @classmethod
    def choices(cls, model):
        yield '', pgettext('reports-volatile_choice', 'None')


class RegularFieldLinkedGraphFetcher(GraphFetcher):
    type_id = constants.RGF_FK
    choices_group_name = _('Fields')

    # def __init__(self, field_name, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     model = self.graph.model
    #     self.field_name = None
    #     self.verbose_volatile_column = '??'
    #
    #     try:
    #         field = model._meta.get_field(field_name)
    #     except FieldDoesNotExist:
    #         logger.warning('Instance block: invalid field %s.%s in block config.',
    #                        model.__name__, field_name,
    #                       )
    #         self.error = _('The field is invalid.')
    #     else:
    #         if isinstance(field, ForeignKey):
    #             self.verbose_volatile_column = gettext('{field} (Field)').format(field=field.verbose_name)
    #             self._field_name = field_name
    #             self._volatile_model = field.remote_field.model
    #         else:
    #             logger.warning('Instance block: field %s.%s in block config is not a FK.',
    #                            model.__name__, field_name,
    #                           )
    #             self.error = _('The field is invalid (not a foreign key).')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = self.graph.model
        self._field_name: Optional[str] = None
        self.verbose_name = '??'

        field_name = self.value
        if not field_name:
            logger.warning('Instance block: no given field in block config.')
            self.error = _('No field given.')
        else:
            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist as e:
                logger.warning(
                    'Instance block: invalid field in block config: %s',
                    e,
                )
                self.error = _('The field is invalid.')
            else:
                fconf = FieldsConfig.LocalCache()
                error = self._check_field(field=field, fields_configs=fconf)
                if error:
                    logger.warning(
                        'Instance block: invalid field in block config: %s',
                        error,
                    )
                    self.error = error
                else:
                    self.verbose_name = gettext('{field} (Field)').format(
                        field=field.verbose_name,
                    )
                    self._field_name = field_name
                    self._volatile_model = field.remote_field.model

    @staticmethod
    def _check_field(field, fields_configs: FieldsConfig.LocalCache) -> Optional[str]:
        if not isinstance(field, ForeignKey):
            return _('The field is invalid (not a foreign key).')

        if not issubclass(field.remote_field.model, CremeEntity):
            return _('The field is invalid (not a foreign key to CremeEntity).')

        if not field.get_tag('viewable'):
            return 'the field is not viewable'  # TODO: test

        if fields_configs.get_4_model(field.model).is_field_hidden(field):
            return _('The field is hidden.')

        return None

    def _aux_fetch_4_entity(self, entity, order, user):
        return self.graph.fetch(
            extra_q=Q(**{self._field_name: entity.pk}), order=order, user=user,
        ) if isinstance(entity, self._volatile_model) else (
            [], []
        )

    @classmethod
    def choices(cls, model):
        fconf = FieldsConfig.LocalCache()
        check_field = partial(cls._check_field, fields_configs=fconf)

        yield from ModelFieldEnumerator(
            model, deep=0, only_leafs=False,
        ).filter(
            lambda f, deep: check_field(field=f) is None,
        ).choices()

    @staticmethod
    def validate_fieldname(graph, field_name):
        warnings.warn(
            'RegularFieldLinkedGraphFetcher.validate_fieldname() is deprecated.',
            DeprecationWarning
        )

        from creme.creme_core.utils.meta import FieldInfo

        try:
            field_info = FieldInfo(graph.model, field_name)
        except FieldDoesNotExist:
            return f'invalid field "{field_name}"'

        if len(field_info) > 1:
            return f'field "{field_name}" with deep > 1'

        field = field_info[0]

        if not (isinstance(field, ForeignKey) and
                issubclass(field.remote_field.model, CremeEntity)):
            return f'field "{field_name}" is not a ForeignKey to CremeEntity'


class RelationLinkedGraphFetcher(GraphFetcher):
    type_id = constants.RGF_RELATION
    choices_group_name = _('Relationships')

    # def __init__(self, rtype_id, *args, **kwargs):
    #         super().__init__(*args, **kwargs)
    #         try:
    #             rtype = RelationType.objects.get(pk=rtype_id)
    #         except RelationType.DoesNotExist:
    #             logger.warning('Instance block: invalid RelationType "%s" in block config.',
    #                            rtype_id,
    #                           )
    #             self.error = _('The relationship type is invalid.')
    #             self.verbose_volatile_column = '??'
    #         else:
    #             self.verbose_volatile_column = gettext('{rtype} (Relationship)').format(rtype=rtype)
    #             self._rtype = rtype
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = '??'
        self._rtype: Optional[RelationType] = None
        rtype_id = self.value

        if not rtype_id:
            self.error = _('No relationship type given.')
        else:
            try:
                rtype = RelationType.objects.get(pk=rtype_id)
            except RelationType.DoesNotExist as e:
                logger.warning(
                    'Instance block: invalid RelationType in block config: %s',
                    e,
                )
                self.error = _('The relationship type is invalid.')
            else:
                model = self.graph.model
                if not rtype.is_compatible(model):
                    self.error = gettext(
                        'The relationship type is not compatible with «{}».'
                    ).format(model._meta.verbose_name)
                else:
                    self.verbose_name = gettext(
                        '{rtype} (Relationship)'
                    ).format(rtype=rtype)
                    self._rtype = rtype

    def _aux_fetch_4_entity(self, entity, order, user):
        return self.graph.fetch(
            extra_q=Q(
                relations__type=self._rtype,
                relations__object_entity=entity.pk,
            ),
            user=user,
            order=order,
        )

    @classmethod
    def choices(cls, model):
        for rtype in RelationType.objects.compatible(model, include_internals=True):
            yield rtype.id, str(rtype)