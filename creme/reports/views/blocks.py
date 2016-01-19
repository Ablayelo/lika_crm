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

from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic.popup import inner_popup

from .. import get_rgraph_model
from ..forms.blocks import GraphInstanceBlockForm


# TODO: use add_to_entity() generic view => Post
#       => Problem: it doesn't fit to the needs (credential admin instead of change/link)

@login_required
@permission_required(('reports', 'reports.can_admin'))
def add_graph_instance_block(request, graph_id):
    graph = get_object_or_404(get_rgraph_model(), pk=graph_id)

    if request.method == 'POST':
        graph_form = GraphInstanceBlockForm(graph=graph, user=request.user, data=request.POST)

        if graph_form.is_valid():
            graph_form.save()
    else:
        graph_form = GraphInstanceBlockForm(graph=graph, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':   graph_form,
                        'title': _(u'Add an instance block for «%s»') % graph,
                        'submit_label': _('Save the block'),
                       },
                       is_valid=graph_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )
