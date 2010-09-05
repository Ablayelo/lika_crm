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

from django.db.models import CharField, ManyToManyField, ForeignKey
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from creme_core.models import CremeModel, CremeEntity, RelationType, Relation


class Graph(CremeEntity):
    name                   = CharField(_(u'Name of the graph'), max_length=100)
    orbital_relation_types = ManyToManyField(RelationType, verbose_name=_(u'Types of the peripheral relations'))

    class Meta:
        app_label = 'graphs'
        verbose_name = _(u'Graph')
        verbose_name_plural = _(u'Graphs')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/graphs/graph/%s" % self.id

    def get_edit_absolute_url(self):
        return "/graphs/graph/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/graphs/graphs"

    def get_delete_absolute_url(self):
        return "/graphs/graph/delete/%s" % self.id

    def generate_png(self):
        from os.path import join, exists
        from os import makedirs

        import pygraphviz as pgv

        graph = pgv.AGraph(directed=True)

        #NB: "self.roots.all()" causes a strange additional query (retrieving of the base CremeEntity !)....
        roots = RootNode.objects.filter(graph=self.id).select_related('entity')

        add_node = graph.add_node
        add_edge = graph.add_edge

        #TODO: entity cache ? regroups relations by type ? ...

        CremeEntity.populate_real_entities([root.entity for root in roots]) #small optimisation

        for root in roots:
            add_node(unicode(root.entity), shape='box')
            #add_node('filled box',    shape='box', style='filled', color='#FF00FF')
            #add_node('filled box v2', shape='box', style='filled', fillcolor='#FF0000', color='#0000FF', penwidth='2.0') #default pensize="1.0"

        orbital_nodes = {} #cache

        for root in roots:
            subject = root.entity
            relations = subject.relations.filter(type__in=root.relation_types.all()).select_related('object_entity', 'type')
            Relation.populate_real_object_entities(relations) #small optimisation

            for relation in relations:
                obj     = relation.object_entity
                uni_obj = unicode(obj)

                add_edge(unicode(subject), uni_obj,
                         label=unicode(relation.type.predicate).encode('utf-8')) # beware: not unicode for label (pygraphviz use label as dict key)
                #add_edge('b', 'd', color='#FF0000', fontcolor='#00FF00', label='foobar', style='dashed')

                orbital_nodes[obj.id] = uni_obj

        orbital_rtypes = self.orbital_relation_types.all()

        if orbital_rtypes:
            orbital_ids = orbital_nodes.keys()

            for relation in Relation.objects.filter(subject_entity__in=orbital_ids,
                                                    object_entity__in=orbital_ids,
                                                    type__in=orbital_rtypes).select_related('type'):
                add_edge(orbital_nodes[relation.subject_entity_id], orbital_nodes[relation.object_entity_id],
                         label=unicode(relation.type.predicate).encode('utf-8'),
                         style='dashed')

        #print graph.string()

        graph.layout(prog='dot') #algo: neato dot twopi circo fdp nop

        #TODO: use a true tmp file ???? or in populate ???
        dir_path = join(settings.MEDIA_ROOT, 'upload', 'graphs')
        if not exists(dir_path):
            makedirs(dir_path)

        filename = 'graph_%i.png' % self.id

        #TODO: delete old files ???
        graph.draw(join(dir_path, filename), format='png') #format: pdf svg

        return HttpResponseRedirect('/download_file/upload/graphs/' + filename)


class RootNode(CremeModel):
    graph          = ForeignKey(Graph, related_name='roots')
    entity         = ForeignKey(CremeEntity)
    relation_types = ManyToManyField(RelationType)

    class Meta:
        app_label = 'graphs'
