# -*- coding: utf-8 -*-

# from django.conf.urls import url
from django.urls import re_path, include

from .views import memo, alert, todo, action, user_message


urlpatterns = [
    re_path(r'^memo/', include([
        re_path(r'^add/(?P<entity_id>\d+)[/]?$', memo.MemoCreation.as_view(), name='assistants__create_memo'),
        re_path(r'^edit/(?P<memo_id>\d+)[/]?$',  memo.MemoEdition.as_view(),  name='assistants__edit_memo'),
    ])),
    re_path(r'^alert/', include([
        re_path(r'^add/(?P<entity_id>\d+)[/]?$',     alert.AlertCreation.as_view(), name='assistants__create_alert'),
        re_path(r'^edit/(?P<alert_id>\d+)[/]?$',     alert.AlertEdition.as_view(),  name='assistants__edit_alert'),
        re_path(r'^validate/(?P<alert_id>\d+)[/]?$', alert.validate,                name='assistants__validate_alert'),
    ])),
    re_path(r'^todo/', include([
        re_path(r'^add/(?P<entity_id>\d+)[/]?$',    todo.ToDoCreation.as_view(), name='assistants__create_todo'),
        re_path(r'^edit/(?P<todo_id>\d+)[/]?$',     todo.ToDoEdition.as_view(),  name='assistants__edit_todo'),
        re_path(r'^validate/(?P<todo_id>\d+)[/]?$', todo.validate,               name='assistants__validate_todo'),
    ])),
    re_path(r'^action/', include([
        re_path(r'^add/(?P<entity_id>\d+)[/]?$',      action.ActionCreation.as_view(), name='assistants__create_action'),
        re_path(r'^edit/(?P<action_id>\d+)[/]?$',     action.ActionEdition.as_view(),  name='assistants__edit_action'),
        re_path(r'^validate/(?P<action_id>\d+)[/]?$', action.validate,                 name='assistants__validate_action'),
    ])),
    re_path(r'^message/', include([
        re_path(r'^add[/]?$',                    user_message.UserMessageCreation.as_view(),        name='assistants__create_message'),
        re_path(r'^add/(?P<entity_id>\d+)[/]?$', user_message.RelatedUserMessageCreation.as_view(), name='assistants__create_related_message'),
        # re_path(r'^delete[/]?$',                 user_message.delete,                               name='assistants__delete_message'),
        re_path(r'^delete[/]?$',                 user_message.UserMessageDeletion.as_view(),        name='assistants__delete_message'),
    ])),
]
