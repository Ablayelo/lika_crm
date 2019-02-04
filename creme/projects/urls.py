# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme.activities import activity_model_is_custom

from . import project_model_is_custom, task_model_is_custom
from .views import project, task, resource


urlpatterns = [
    # TODO: Define what user could do or not if projet is 'close'
    #       (with the use of the button that sets an effective end date)
    # TODO: change url ?? project/close/(?P<project_id>\d+) ? 'id' as POST argument ?
    url(r'^project/(?P<project_id>\d+)/close[/]?$', project.close, name='projects__close_project'),

    url(r'^task/parent/delete[/]?$',               task.delete_parent,           name='projects__remove_parent_task'),
    url(r'^task/(?P<task_id>\d+)/parent/add[/]?$', task.ParentsAdding.as_view(), name='projects__add_parent_task'),

    # Task: Resource brick
    url(r'^task/(?P<task_id>\d+)/resource/add[/]?$', resource.ResourceCreation.as_view(), name='projects__create_resource'),
    url(r'^resource/edit/(?P<resource_id>\d+)[/]?$', resource.ResourceEdition.as_view(),  name='projects__edit_resource'),
    url(r'^resource/delete[/]?$',                    resource.delete,                     name='projects__delete_resource'),

    # Task: related activities brick
    url(r'^activity/delete[/]?$', task.delete_activity, name='projects__delete_activity'),
]

urlpatterns += swap_manager.add_group(
    activity_model_is_custom,
    Swappable(url(r'^task/(?P<task_id>\d+)/activity/add[/]?$',
                  task.RelatedActivityCreation.as_view(),
                  name='projects__create_activity',
                 ),
              check_args=Swappable.INT_ID,
             ),
    Swappable(url(r'^activity/edit/(?P<activity_id>\d+)[/]?$',
                  task.ActivityEditionPopup.as_view(),
                  name='projects__edit_activity',
                 ),
              check_args=Swappable.INT_ID,
             ),
    app_name='projects',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    project_model_is_custom,
    # Swappable(url(r'^projects[/]?$',                         project.listview,                  name='projects__list_projects')),
    Swappable(url(r'^projects[/]?$',                         project.ProjectsList.as_view(),    name='projects__list_projects')),
    Swappable(url(r'^project/add[/]?$',                      project.ProjectCreation.as_view(), name='projects__create_project')),
    Swappable(url(r'^project/edit/(?P<project_id>\d+)[/]?$', project.ProjectEdition.as_view(),  name='projects__edit_project'), check_args=Swappable.INT_ID),
    Swappable(url(r'^project/(?P<project_id>\d+)[/]?$',      project.ProjectDetail.as_view(),   name='projects__view_project'), check_args=Swappable.INT_ID),
    app_name='projects',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    task_model_is_custom,
    Swappable(url(r'^project/(?P<project_id>\d+)/task/add[/]?$', task.TaskCreation.as_view(),     name='projects__create_task'),     check_args=Swappable.INT_ID),
    Swappable(url(r'^task/edit/(?P<task_id>\d+)[/]?$',           task.TaskEdition.as_view(),      name='projects__edit_task'),       check_args=Swappable.INT_ID),
    Swappable(url(r'^task/edit/(?P<task_id>\d+)/popup[/]?$',     task.TaskEditionPopup.as_view(), name='projects__edit_task_popup'), check_args=Swappable.INT_ID),
    Swappable(url(r'^task/(?P<task_id>\d+)[/]?$',                task.TaskDetail.as_view(),       name='projects__view_task'),       check_args=Swappable.INT_ID),
    app_name='projects',
).kept_patterns()
