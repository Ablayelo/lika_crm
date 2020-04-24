# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from collections import Counter

from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui import bricks as core_bricks
from creme.creme_core.models import InstanceBrickConfigItem

from creme import reports
from .core.graph import GraphFetcher
from .models import Field
from .report_chart_registry import report_chart_registry

Report = reports.get_report_model()
ReportGraph = reports.get_rgraph_model()


class ReportBarHatBrick(core_bricks.SimpleBrick):
    template_name = 'reports/bricks/report-hat-bar.html'


class ReportFieldsBrick(core_bricks.Brick):
    id_           = core_bricks.Brick.generate_id('reports', 'fields')
    dependencies  = (Field,)
    verbose_name  = _('Columns of the report')
    template_name = 'reports/bricks/fields.html'
    target_ctypes = (Report,)

    def detailview_display(self, context):
        columns = context['object'].columns

        return self._render(self.get_template_context(
            context,
            columns=columns,
            expand=any(field.sub_report_id for field in columns),
        ))


class ReportGraphsBrick(core_bricks.QuerysetBrick):
    id_           = core_bricks.QuerysetBrick.generate_id('reports', 'graphs')
    dependencies  = (ReportGraph,)
    verbose_name  = _("Report's graphs")
    template_name = 'reports/bricks/graphs.html'
    # order_by      = 'name'
    order_by      = 'created'
    target_ctypes = (Report,)

    def detailview_display(self, context):
        btc = self.get_template_context(
            context,
            ReportGraph.objects.filter(linked_report=context['object']),
            report_charts=report_chart_registry,
        )
        graphs = btc['page'].object_list
        counter = Counter(
            InstanceBrickConfigItem.objects
                                   .filter(entity__in=[g.id for g in graphs])
                                   .values_list('entity', flat=True)
        )

        for graph in graphs:
            graph.instance_bricks_count = counter[graph.id]

        return self._render(btc)


class InstanceBricksInfoBrick(core_bricks.QuerysetBrick):
    id_           = core_bricks.QuerysetBrick.generate_id('reports', 'instance_bricks_info')
    dependencies  = (InstanceBrickConfigItem,)
    verbose_name  = 'Instance bricks information'
    template_name = 'reports/bricks/instance-bricks-info.html'
    # order_by      = 'verbose'
    configurable  = False

    # def detailview_display(self, context):
    #     btc = self.get_template_context(
    #         context,
    #         InstanceBrickConfigItem.objects.filter(entity=context['object'].id),
    #     )
    #     get_fetcher = ReportGraph.get_fetcher_from_instance_brick
    #
    #     for ibci in btc['page'].object_list:
    #         ibci.fetcher = get_fetcher(ibci)
    #
    #     return self._render(btc)
    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            InstanceBrickConfigItem.objects.filter(
                brick_class_id=ReportGraphBrick.id_,
                entity=context['object'].id,
            ),
        ))


# class ReportGraphBrick(Brick):
class ReportGraphBrick(core_bricks.InstanceBrick):
    id_           = InstanceBrickConfigItem.generate_base_id('reports', 'graph')
    dependencies  = (ReportGraph,)
    verbose_name  = "Report's graph"  # Overloaded by __init__()
    template_name = 'reports/bricks/graph.html'

    # def __init__(self, instance_brick_config):
    #     super().__init__()
    #     self.instance_brick_id = instance_brick_config.id
    #     self.fetcher = fetcher = ReportGraph.get_fetcher_from_instance_brick(instance_brick_config)
    def __init__(self, instance_brick_config_item):
        super().__init__(instance_brick_config_item)
        # self.fetcher = fetcher = ReportGraph.get_fetcher_from_instance_brick(
        #     instance_brick_config_item,
        # )
        get_data = instance_brick_config_item.get_extra_data
        self.fetcher = fetcher = ReportGraph.fetcher_registry.get(
            graph=instance_brick_config_item.entity.get_real_entity(),
            fetcher_dict={
                key: get_data(key)
                for key in GraphFetcher.DICT_KEYS
            },
        )

        # self.verbose_name = fetcher.verbose_name
        fetcher_vname = fetcher.verbose_name
        self.verbose_name = f'{fetcher.graph} - {fetcher_vname}' if fetcher_vname else str(fetcher.graph)

        error = fetcher.error
        self.errors = [error] if error else None

    # def _auxiliary_display(self, context, x, y):
    def _auxiliary_display(self, context, x, y, error=None, **extra_context):
        fetcher = self.fetcher

        return self._render(self.get_template_context(
            context,
            graph=fetcher.graph,
            x=x, y=y,
            error=fetcher.error or error,
            # volatile_column=fetcher.verbose_volatile_column,
            volatile_column=fetcher.verbose_name,
            # instance_brick_id=self.instance_brick_id,
            instance_brick_id=self.config_item.id,
            report_charts=report_chart_registry,
            **extra_context
        ))

    def detailview_display(self, context):
        kwargs = {}
        try:
            x, y = self.fetcher.fetch_4_entity(
                entity=context['object'],
                user=context['user'],
            )
        except GraphFetcher.IncompatibleContentType as e:
            x = y = None
            kwargs['error'] = str(e)
        except GraphFetcher.UselessResult:
            x = y = None
            kwargs['hide_brick'] = True

        return self._auxiliary_display(context=context, x=x, y=y, **kwargs)

    def home_display(self, context):
        x, y = self.fetcher.fetch(user=context['user'])

        return self._auxiliary_display(context=context, x=x, y=y)

    @property
    def target_ctypes(self):
        return self.fetcher.linked_models
