# -*- coding: utf-8 -*-

from django.apps import apps
# from django.conf.urls import url
from django.urls import re_path

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme.persons import contact_model_is_custom

from . import opportunity_model_is_custom
from .views import opportunity, contact


urlpatterns = [
    *swap_manager.add_group(
        opportunity_model_is_custom,
        # Swappable(url(r'^opportunities[/]?$',   opportunity.listview,                      name='opportunities__list_opportunities')),
        Swappable(re_path(r'^opportunities[/]?$',   opportunity.OpportunitiesList.as_view(),   name='opportunities__list_opportunities')),
        Swappable(re_path(r'^opportunity/add[/]?$', opportunity.OpportunityCreation.as_view(), name='opportunities__create_opportunity')),
        Swappable(re_path(r'^opportunity/add_to/(?P<person_id>\d+)[/]?$',
                      opportunity.RelatedOpportunityCreation.as_view(),
                      name='opportunities__create_related_opportunity',
                     ),
                  check_args=Swappable.INT_ID,
                 ),
        Swappable(re_path(r'^opportunity/add_to/(?P<person_id>\d+)/popup[/]?$',
                      opportunity.RelatedOpportunityCreationPopup.as_view(),
                      name='opportunities__create_related_opportunity_popup',
                     ),
                  check_args=Swappable.INT_ID,
                 ),
        Swappable(re_path(r'^opportunity/edit/(?P<opp_id>\d+)[/]?$', opportunity.OpportunityEdition.as_view(), name='opportunities__edit_opportunity'), check_args=Swappable.INT_ID),
        Swappable(re_path(r'^opportunity/(?P<opp_id>\d+)[/]?$',      opportunity.OpportunityDetail.as_view(),  name='opportunities__view_opportunity'), check_args=Swappable.INT_ID),
        app_name='opportunities',
    ).kept_patterns(),

    *swap_manager.add_group(
        contact_model_is_custom,
        Swappable(re_path(r'^opportunity/(?P<opp_id>\d+)/add_contact[/]?$',
                          contact.RelatedContactCreation.as_view(),
                          name='opportunities__create_related_contact',
                         )
                 ),
        app_name='opportunities',
    ).kept_patterns(),
]

if apps.is_installed('creme.billing'):
    from .views import billing

    urlpatterns += [
        re_path(r'^opportunity/generate_new_doc/(?P<opp_id>\d+)/(?P<ct_id>\d+)[/]?$',
                billing.generate_new_doc, name='opportunities__generate_billing_doc',
               ),
        re_path(r'^opportunity/(?P<opp_id>\d+)/linked/quote/(?P<quote_id>\d+)/(?P<action>set_current|unset_current)[/]?$',
                billing.current_quote, name='opportunities__linked_quote_is_current',
               ),
    ]
