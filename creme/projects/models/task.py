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

from itertools import chain

from django.core.urlresolvers import reverse
from django.db.models import (CharField, TextField, DateTimeField, PositiveIntegerField,
        ForeignKey, ManyToManyField, PROTECT)
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity, Relation

#from creme.activities.models import Activity
#from creme.activities.constants import NARROW

from ..constants import COMPLETED_PK, CANCELED_PK, REL_OBJ_LINKED_2_PTASK, REL_SUB_PART_AS_RESOURCE
from .project import Project
from .taskstatus import TaskStatus


#class ProjectTask(Activity):
#    project      = ForeignKey(Project, verbose_name=_(u'Project'), related_name='tasks_set', editable=False)
#    order        = PositiveIntegerField(_(u'Order'), blank=True, null=True, editable=False) #TODO: null = False ?
#    parent_tasks = ManyToManyField("self", blank=True, null=True, symmetrical=False,
#                                   related_name='children_set', editable=False,
#                                  )
##    duration     = PositiveIntegerField(_(u'Estimated duration (in hours)'), blank=False, null=False) #already have activity duration in Activity
#    tstatus      = ForeignKey(TaskStatus, verbose_name=_(u'Task situation'), on_delete=PROTECT)
#
#    class Meta:
#        app_label = 'projects'
#        verbose_name = _(u'Task of project')
#        verbose_name_plural = _(u'Tasks of project')
#        ordering = Activity._meta.ordering #NB: sadly it seems that inheriting from Activity.Meta does not work.
#
#    def __init__ (self, *args , **kwargs):
#        super(ProjectTask, self).__init__(*args, **kwargs)
#        self.floating_type = NARROW

#class ProjectTask(CremeEntity):
class AbstractProjectTask(CremeEntity):
    title        = CharField(_(u'Title'), max_length=100)
    project      = ForeignKey(Project, verbose_name=_(u'Project'), related_name='tasks_set', editable=False)
    order        = PositiveIntegerField(_(u'Order'), blank=True, null=True, editable=False) #TODO: null = False ?
    parent_tasks = ManyToManyField('self', blank=True, null=True, symmetrical=False,
                                   related_name='children_set', editable=False, #TODO; rename children ?
                                  )
    start        = DateTimeField(_(u'Start'), blank=True, null=True)
    end          = DateTimeField(_(u'End'), blank=True, null=True)
    duration     = PositiveIntegerField(_(u'Duration (in hours)'), blank=True, null=True) #TODO: null=False (required in form) (idem with start/end)
    description  = TextField(_(u'Description'), blank=True, null=True)
    tstatus      = ForeignKey(TaskStatus, verbose_name=_(u'Task situation'), on_delete=PROTECT)

    class Meta:
        abstract = True
        app_label = 'projects'
        verbose_name = _(u'Task of project')
        verbose_name_plural = _(u'Tasks of project')
        ordering = ('-start',)

    effective_duration = None
    resources          = None
#    working_periods    = None
    parents            = None

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
#        return "/projects/task/%s" % self.id
        return reverse('projects__view_task', args=(self.id,))

    def get_edit_absolute_url(self):
#        return "/projects/task/edit/%s" % self.id
        return reverse('projects__edit_task', args=(self.id,))

    def get_related_entity(self):
        return self.project

    def _pre_delete(self):
        for resource in self.get_resources():
            resource.delete()

        for relation in self.relations.filter(type=REL_OBJ_LINKED_2_PTASK):
            relation._delete_without_transaction()

#    def delete(self):
#        for resource in self.get_resources():
#            resource.delete()
#        super(ProjectTask, self).delete()

    @property
    def safe_duration(self):
        return self.duration or 0

    def get_parents(self):
        if self.parents is None:
            self.parents = self.parent_tasks.all()
        return self.parents

    def get_subtasks(self): #TODO: store result in a cache ?
        """Return all the subtasks in a list.
        Subtasks include the task itself, all its children, the children of its children etc...
        """
        subtasks = level_tasks = [self]

        #TODO: use prefetch_related() ??
        while level_tasks:
            level_tasks = list(chain.from_iterable(task.children_set.all() for task in level_tasks))
            subtasks.extend(level_tasks)

        return subtasks

    def get_resources(self):
        if self.resources is None:
#            self.resources = self.resources_set.all()
            self.resources = self.resources_set.select_related('linked_contact')
        return self.resources

#    def get_working_periods(self):
#        if self.working_periods is None:
#            self.working_periods = self.tasks_set.all()
#        return self.working_periods
    @property
    def related_activities(self):
        activities = [r.object_entity.get_real_entity()
                            for r in self.get_relations(REL_OBJ_LINKED_2_PTASK,
                                                        real_obj_entities=True,
                                                       )
                     ]
        resource_per_contactid = {r.linked_contact_id: r for r in self.get_resources()}
        contact_ids = dict(
                Relation.objects.filter(type=REL_SUB_PART_AS_RESOURCE,
                                        object_entity__in=[a.id for a in activities],
                                       )
                                .values_list('object_entity_id', 'subject_entity_id')
            )

        for activity in activities:
            activity.projects_resource = resource_per_contactid[contact_ids[activity.id]]

        return activities

    def get_task_cost(self):
#        return sum(period.duration * (period.resource.hourly_cost or 0)
#                        for period in self.get_working_periods()
#                  )
        return sum((activity.duration or 0) * activity.projects_resource.hourly_cost
                        for activity in self.related_activities
                  )

    def get_effective_duration(self, format='h'):
        if self.effective_duration is None:
#            self.effective_duration = sum(period.duration for period in self.get_working_periods())
            self.effective_duration = sum(activity.duration or 0 for activity in self.related_activities)

        if format == '%':
            duration = self.duration

            return (self.effective_duration * 100) / duration if duration else 100

        return self.effective_duration

    def get_delay(self):
        return self.get_effective_duration() - self.safe_duration

    def is_alive(self):
        return self.tstatus_id not in (COMPLETED_PK, CANCELED_PK)

    def _clone_m2m(self, source):#Handled manually in clone_scope
        pass

#    def _pre_save_clone(self, source):#Busy hasn't the same semantic here
#        pass

    def _post_save_clone(self, source):
        for resource in source.get_resources():
            resource.clone_for_task(self)

#        for working_period in source.get_working_periods():
#            working_period.clone(self)

    @staticmethod
    def clone_scope(tasks, project):
        """Clone each task in 'tasks',assign them to 'project', and restore links between each task
        @params tasks : an iterable of ProjectTask
        @params project : A Project
        """
        context = {}

        project_task_filter = ProjectTask.objects.filter

        for task in tasks:
            new_task = task.clone()
            new_task.project = project
            new_task.save()
            #new_task = task.clone(project) TODO

            context[task.id] = {'new_pk':     new_task.id, 
                                'o_children': project_task_filter(parent_tasks=task.id)
                                                .values_list('pk', flat=True),
                               }

        new_links = {values['new_pk']: [context[old_child_id]['new_pk']
                                            for old_child_id in values['o_children']
                                       ]
                        for values in context.itervalues()
                    }

        for task in project_task_filter(pk__in=new_links.keys()):
            for sub_task in project_task_filter(pk__in=new_links[task.id]):
                sub_task.parent_tasks.add(task)


class ProjectTask(AbstractProjectTask):
    class Meta(AbstractProjectTask.Meta):
        swappable = 'PROJECTS_TASK_MODEL'
