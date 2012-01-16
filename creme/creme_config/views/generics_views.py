# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_model_with_popup, edit_model_with_popup
from creme_core.utils import get_from_POST_or_404, get_ct_or_404, jsonify

from creme_config.registry import config_registry
from creme_config.blocks import generic_models_block


def _get_appconf(user, app_name):
    user.has_perm_to_admin_or_die(app_name)

    try:
        app_config = config_registry.get_app(app_name)
    except KeyError:
        raise Http404('Unknown app')

    return  app_config

def _get_modelconf(app_config, model_name):
    #TODO: use only ct instead of model_name ???
    for modelconf in app_config.models():
        if modelconf.name_in_url == model_name:
            return modelconf

    raise Http404('Unknown model')

@login_required
def add_model(request, app_name, model_name):
    return add_model_with_popup(request,
                                _get_modelconf(_get_appconf(request.user, app_name), model_name).model_form,
                                _('New value'),
                                template='creme_core/generics/form/add_innerpopup.html',
                               )

@login_required
def portal_model(request, app_name, model_name):
    app_config = _get_appconf(request.user, app_name)
    model      = _get_modelconf(app_config, model_name).model

    return render_to_response('creme_config/generics/model_portal.html',
                              {'model':            model,
                               'app_name':         app_name,
                               'app_verbose_name': app_config.verbose_name,
                               'model_name':       model_name,
                              },
                              context_instance=RequestContext(request))

@login_required
def delete_model(request, app_name, model_name):
    model   = _get_modelconf(_get_appconf(request.user, app_name), model_name).model
    object_ = get_object_or_404(model, pk=get_from_POST_or_404(request.POST, 'id'))

    if not getattr(object_, 'is_custom', True):
        raise Http404('Can not delete (is not custom)')

    object_.delete()

    return HttpResponse()

@login_required
def edit_model(request, app_name, model_name, object_id):
    modelconf = _get_modelconf(_get_appconf(request.user, app_name), model_name)

    return edit_model_with_popup(request,
                                 {'pk': object_id},
                                 modelconf.model,
                                 modelconf.model_form,
                                 template='creme_core/generics/form/edit_innerpopup.html'
                                )

@login_required
def swap_order(request, app_name, model_name, object_id, offset):
    if request.method != 'POST':
        raise Http404('This view use POST method')

    model = _get_modelconf(_get_appconf(request.user, app_name), model_name).model
    fields = model._meta.get_all_field_names()

    if 'order' not in fields:
        raise Http404('Invalid model (no "user" field)')

    found = None
    ordered = []

    for i, instance in enumerate(model.objects.all()):
        new_order = i + 1

        if str(instance.pk) == object_id: #manage the model with string as pk
            found = i
            new_order += offset

        ordered.append([new_order, instance])

    if found is None:
        raise Http404('Invalid object id (not found)')

    swapped_index = found + offset

    if not (0 <= swapped_index < len(ordered)):
        raise Http404('Invalid object id')

    ordered[swapped_index][0] -= offset #update new_order

    for new_order, instance in ordered:
        if new_order != instance.order:
            instance.order = new_order
            instance.save()

    return HttpResponse()

@login_required
def portal_app(request, app_name):
    app_config = _get_appconf(request.user, app_name)

    return render_to_response('creme_config/generics/app_portal.html',
                              {'app_name':          app_name,
                               'app_verbose_name':  app_config.verbose_name,
                               'app_config':        list(app_config.models()), #list-> have the length in the template
                               'app_config_blocks': app_config.blocks(),#Get config registered blocks
                              },
                              context_instance=RequestContext(request)
                             )

@login_required
@jsonify
def reload_block(request, ct_id):
    ct_id = int(ct_id)
    model = get_ct_or_404(ct_id).model_class()
    app_name = model._meta.app_label

    request.user.has_perm_to_admin_or_die(app_name)

    context = RequestContext(request)
    context.update({
            'model':      model,
            'model_name': config_registry.get_app(app_name).get_model_conf(ct_id).name_in_url,
            'app_name':   app_name,
        })

    return [(generic_models_block.id_, generic_models_block.detailview_display(context))]
