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

from django.db.models import Q
from django.http import HttpResponse#, Http404
from django.shortcuts import get_object_or_404, render_to_response, get_list_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.template.context import RequestContext

from creme_core.models import CremeEntity, CremePropertyType, CremeProperty
from creme_core.views import generic
from creme_core.forms.creme_property import AddPropertiesForm, AddPropertiesBulkForm
from creme.creme_core.views.generic.popup import inner_popup
from creme_core.utils import get_ct_or_404, get_from_POST_or_404

@login_required
def add_properties_bulk(request, ct_id, ids):
    user     = request.user
    model    = get_ct_or_404(ct_id).model_class()
    entities = get_list_or_404(model, pk__in=[id for id in ids.split(',') if id])

    CremeEntity.populate_real_entities(entities)
    CremeEntity.populate_credentials(entities, user)

    filtered = {True: [], False: []}
    for entity in entities:
        filtered[entity.can_change(user)].append(entity)

    if request.method == 'POST':
        form = AddPropertiesBulkForm(model=model,
                                     entities=filtered[True],
                                     forbidden_entities=filtered[False],
                                     user=request.user,
                                     data=request.POST
                                     )

        if form.is_valid():
            form.save()
    else:
        form = AddPropertiesBulkForm(model=model,
                                     entities=filtered[True],
                                     forbidden_entities=filtered[False],
                                     user=request.user
                                    )

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':  form,
                        'title': _(u'Multiple adding of relations'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

#TODO: use  a true form (like the bulk) relation adding
#TODO: Remove me ?
@login_required
def add_to_entities(request):
    POST          = request.POST
    entities_ids  = get_from_POST_or_404(POST, 'ids')
    prop_type_id  = get_from_POST_or_404(POST, 'type_id')
    property_type = get_object_or_404(CremePropertyType, pk=prop_type_id)
    return_str    = ""
    get           = CremeEntity.objects.get
    property_get  = CremeProperty.objects.get
    has_perm      = request.user.has_perm

    #TODO: regroup queries ???
    for id in entities_ids.split(','):
        try:
            entity = get(pk=id)
        except CremeEntity.DoesNotExist:
            continue

        if not id.isdigit():
#            debug('not digit ?!')
            continue

        if not has_perm('creme_core.change_entity', entity):
            return_str += _(u'%s : <b>Permission denied</b>,') % entity
            continue

        try:
            property = property_get(type=property_type, creme_entity=entity)
        except CremeProperty.DoesNotExist:
            CremeProperty(type=property_type, creme_entity=entity).save()
        else:
            return_str += _(u'%(entity)s has already the property %(property)s,') % {'entity': entity, 'property': property}

    return_status = 200 if not return_str else 400
    return_str    = "%s" % return_str

    return HttpResponse(return_str, mimetype="text/javascript", status=return_status)

#TODO: Remove me ?
@login_required
def get_property_types_for_ct(request):
    ct = get_ct_or_404(get_from_POST_or_404(request.POST, 'ct_id'))
    property_types = CremePropertyType.objects.filter(Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True)) #TODO: in a CremeProperty method ??

    from django.core import serializers
    data = serializers.serialize('json', property_types, fields=('text',))

    return HttpResponse(data, mimetype='text/javascript')

@login_required
def add_to_entity(request, entity_id):
    return generic.add_to_entity(request, entity_id, AddPropertiesForm, _('New properties for <%s>'))
