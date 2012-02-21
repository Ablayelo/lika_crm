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

from collections import defaultdict

from django.db.models.query_utils import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, get_list_or_404
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.forms.relation import RelationCreateForm, MultiEntitiesRelationCreateForm
from creme_core.models import Relation, RelationType, CremeEntity, EntityCredentials
from creme_core.registry import creme_registry
from creme_core.views.generic import inner_popup, list_view_popup_from_widget
from creme_core.utils import get_ct_or_404, get_from_POST_or_404


class JSONSelectError(Exception):
    def __init__(self, message, status):
        super(Exception, self).__init__(message)
        self.status = status

def _json_select(query, fields, range, sort_field=None, use_columns=False):
    try:
        start, end = range

        if not use_columns:
            result = []

            if sort_field:
                sorted_result = [(sort_field(entity), [getter(entity) for getter in fields]) for entity in query]
                sorted_result.sort(cmp=lambda a, b:cmp(a[0], b[0])) #TODO: use 'key' param instead
                result = [e[1] for e in sorted_result[start:end]]
            else:
                for entity in query[start:end]:
                    result.append([getter(entity) for getter in fields]) #TODO: use extend + genexpr ?
        else:
            query = query.order_by(sort_field) if sort_field else query
            flat = len(fields) == 1
            result = list(query.values_list(flat=flat, *fields)[start:end])

        return JSONEncoder().encode(result) #TODO: move out the 'try' block
    except Exception as err:
        raise JSONSelectError(unicode(err), 500)

def _json_parse_field(field, allowed_fields, use_columns=False):
    if field not in allowed_fields.keys():
        raise JSONSelectError("forbidden field '%s'" % field, 403)

    if use_columns:
        return field

    getter = allowed_fields.get(field)

    if not getter:
        raise JSONSelectError("forbidden fields '%s'" % field, 403)

    return getter

def _json_parse_fields(fields, allowed_fields, use_columns=False):
    if not fields:
        raise JSONSelectError("no such field", 400)

    #return list(_json_parse_field(field, allowed_fields, use_columns) for field in fields)
    return [_json_parse_field(field, allowed_fields, use_columns) for field in fields]

def _json_parse_select_request(request, allowed_fields):
    if not request:
        raise JSONSelectError("not such parameter", 400)

    use_columns = bool(request.get('value_list', 0))
    range = [int(i) if i is not None else None for i in (request.get('start'), request.get('end'))]
    fields = _json_parse_fields(request.getlist('fields'), allowed_fields, use_columns)
    sort = request.get('sort')
    sort = _json_parse_field(sort, allowed_fields, use_columns) if sort is not None else None

    return (fields, range, sort, use_columns)

JSON_ENTITY_FIELDS = {'unicode':     unicode,
                      'id':          lambda e: e.id,
                      'entity_type': lambda e: e.entity_type_id
                     }

@login_required
def json_entity_get(request, id):
    try:
        fields, range, sort, use_columns = _json_parse_select_request(request.GET, JSON_ENTITY_FIELDS)
        query = EntityCredentials.filter(request.user, CremeEntity.objects.filter(pk=id))
        return HttpResponse(_json_select(query, fields, (0, 1), sort, use_columns), mimetype="text/javascript") #TODO: move out the 'try' block
    except JSONSelectError as err:
        return HttpResponse(err.message, mimetype="text/javascript", status=err.status)

JSON_PREDICATE_FIELDS = {'unicode': unicode,
                         'id':      lambda e: e.id
                        }

@login_required
def json_entity_predicates(request, id):
    try:
        predicates = _get_entity_predicates(request, id)
        parameters = _json_parse_select_request(request.GET, JSON_PREDICATE_FIELDS)
        return HttpResponse(_json_select(predicates, *parameters), mimetype="text/javascript")
    except JSONSelectError as err:
        return HttpResponse(err.message, mimetype="text/javascript", status=err.status)
    except Http404 as err:
        return HttpResponse(err, mimetype="text/javascript", status=404)
    except Exception as err:
        return HttpResponse(err, mimetype="text/javascript", status=500)

JSON_CONTENT_TYPE_FIELDS = {'unicode':  unicode,
                            'name':     lambda e: e.name,
                            'id':       lambda e: e.id
                           }

@login_required
def json_predicate_content_types(request, id):
    try:
        content_types = get_object_or_404(RelationType, pk=id).object_ctypes.all()
        fields, range, sort, use_columns = _json_parse_select_request(request.GET, JSON_CONTENT_TYPE_FIELDS)

        if not content_types:
            content_type_from_model = ContentType.objects.get_for_model
            content_types = [content_type_from_model(model) for model in creme_registry.iter_entity_models()]
            return HttpResponse(_json_select(content_types, fields, range, sort))

        return HttpResponse(_json_select(content_types, fields, range, sort, use_columns), mimetype="text/javascript")
    except JSONSelectError as err:
        return HttpResponse(err.message, mimetype="text/javascript", status=err.status)
    except Http404 as err:
        return HttpResponse(err, mimetype="text/javascript", status=404)
    except Exception as err:
        return HttpResponse(err, mimetype="text/javascript", status=500)

def _get_entity_predicates(request, id):
    entity = get_object_or_404(CremeEntity, pk=id).get_real_entity() #TODO: useful 'get_real_entity() ??'

    entity.can_view_or_die(request.user)

    predicates = RelationType.objects.filter(is_internal=False).order_by('predicate')

    #TODO: use CremePropertyType constraints too
    return predicates.filter(Q(subject_ctypes=entity.entity_type)|Q(subject_ctypes__isnull=True)).distinct()

def add_relations(request, subject_id, relation_type_id=None):
    """
        NB: In case of relation_type_id=None is internal relation type is verified in RelationCreateForm clean
    """
    subject = get_object_or_404(CremeEntity, pk=subject_id)
    subject.can_link_or_die(request.user)

    relations_types = None

    if relation_type_id:
        get_object_or_404(RelationType, pk=relation_type_id).is_not_internal_or_die()
        relations_types = [relation_type_id]

    if request.method == 'POST':
        form = RelationCreateForm(subject=subject, user=request.user, relations_types=relations_types, data=request.POST)

        if form.is_valid():
            form.save()
    else:
        form = RelationCreateForm(subject=subject, user=request.user, relations_types=relations_types)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':  form,
                        'title': _(u'Relationships for <%s>') % subject,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
def add_relations_bulk(request, model_ct_id, relations_types=None):#TODO: Factorise with add_properties_bulk and bulk_update?
    user = request.user
    model    = get_object_or_404(ContentType, pk=model_ct_id).model_class()
    entities = get_list_or_404(model, pk__in=request.REQUEST.getlist('ids'))

    CremeEntity.populate_real_entities(entities)
    CremeEntity.populate_credentials(entities, user)

    filtered = {True: [], False: []}
    for entity in entities:
        filtered[entity.can_link(user)].append(entity)

    if relations_types is not None:
        relations_types = [rt for rt in relations_types.split(',') if rt]

    if request.method == 'POST':
        form = MultiEntitiesRelationCreateForm(subjects=filtered[True],
                                               forbidden_subjects=filtered[False],
                                               user=request.user,
                                               data=request.POST,
                                               relations_types=relations_types,
                                              )

        if form.is_valid():
            form.save()
    else:
        form = MultiEntitiesRelationCreateForm(subjects=filtered[True],
                                               forbidden_subjects=filtered[False],
                                               user=request.user,
                                               relations_types=relations_types,
                                              )

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {'form':  form,
                        'title': _(u'Multiple adding of relationships'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
def delete(request):
    relation = get_object_or_404(Relation, pk=get_from_POST_or_404(request.POST, 'id'))
    subject  = relation.subject_entity
    user = request.user

    subject.can_unlink_or_die(user)
    relation.object_entity.can_unlink_or_die(user)
    relation.type.is_not_internal_or_die()

    relation.get_real_entity().delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(subject.get_real_entity().get_absolute_url())

@login_required
def delete_similar(request):
    """Delete relations with the same type between 2 entities"""
    POST = request.POST
    subject_id = get_from_POST_or_404(POST, 'subject_id')
    rtype_id   = get_from_POST_or_404(POST, 'type')
    object_id  = get_from_POST_or_404(POST, 'object_id')

    user = request.user
    subject = get_object_or_404(CremeEntity, pk=subject_id)

    subject.can_unlink_or_die(user)
    get_object_or_404(CremeEntity, pk=object_id).can_unlink_or_die(user)

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    for relation in Relation.objects.filter(subject_entity=subject.id, type=rtype, object_entity=object_id):
        relation.get_real_entity().delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(subject.get_real_entity().get_absolute_url())

@login_required
def delete_all(request):
    subject_id = get_from_POST_or_404(request.POST, 'subject_id')
    user = request.user
    subject = get_object_or_404(CremeEntity, pk=subject_id)
    subject.can_unlink_or_die(user)

    errors   = defaultdict(list)

    for relation in Relation.objects.filter(type__is_internal=False, subject_entity=subject_id):
        relation = relation.get_real_entity()
        if relation.object_entity.can_unlink(user):
            relation.delete()
        else:
            errors[403].append(_(u'%s : <b>Permission denied</b>,') % relation)

    if not errors:
        status = 200
        message = _(u"Operation successfully completed")
    else:
        status = min(errors.iterkeys())
        message = ",".join(msg for error_messages in errors.itervalues() for msg in error_messages)

    return HttpResponse(message, mimetype="text/javascript", status=status)

@login_required
def objects_to_link_selection(request, rtype_id, subject_id, object_ct_id, o2m=False, *args, **kwargs):
    """Display an inner popup to select entities to link as relations' objects.
    @param rtype_id RelationType id of the future relations.
    @param subject_id Id of the entity used as subject for relations.
    @param object_ct_id Id of the ContentType of the future relations' objects.
    @param o2m One-To-Many ; if false, it seems Manay-To-Many => multi selection.
    Tip: see the js function creme.relations.handleAddFromPredicateEntity()
    """
    subject = get_object_or_404(CremeEntity, pk=subject_id)
    subject.can_link_or_die(request.user)

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    #TODO: filter with relation creds too
    #extra_q = ~Q(relations__type=rtype.symmetric_type_id, relations__object_entity=subject_id) #It seems that way causes some entities linked with another reelation type to be skipped...
    extra_q = ~Q(pk__in=CremeEntity.objects.filter(relations__type=rtype.symmetric_type_id, relations__object_entity=subject_id).values_list('id', flat=True))

    prop_types = list(rtype.object_properties.all())
    if prop_types:
        extra_q &= Q(properties__type__in=prop_types)

    extra_q_kw = kwargs.get('extra_q')
    if extra_q_kw is not None:
        extra_q &= extra_q_kw

    return list_view_popup_from_widget(request, object_ct_id, o2m, extra_q=extra_q)


#TODO: factorise code (with RelatedEntitiesField for example) ?  With a smart static method method in RelationType ?
@login_required
def add_relations_with_same_type(request):
    """Allow to create from a POST request several relations with the same
    relation type, between a subject and several other entities.
    Tip: see the js function creme.relations.handleAddFromPredicateEntity()
    """
    user = request.user
    POST = request.POST
    subject_id = get_from_POST_or_404(POST, 'subject_id', int)
    rtype_id   = get_from_POST_or_404(POST, 'predicate_id') #TODO: rename POST arg
    entity_ids = POST.getlist('entities')

    if not entity_ids:
        raise Http404('Void "entities" parameter.')

    rtype = get_object_or_404(RelationType, pk=rtype_id)
    rtype.is_not_internal_or_die()

    entity_ids.append(subject_id) #NB: so we can do only one query
    entities = list(CremeEntity.objects.filter(pk__in=entity_ids))

    CremeEntity.populate_credentials(entities, user)

    subject_properties = frozenset(rtype.subject_properties.values_list('id', flat=True))
    object_properties  = frozenset(rtype.object_properties.values_list('id', flat=True))

    if subject_properties or object_properties:
        CremeEntity.populate_properties(entities) #Optimise the get_properties() (but it retrieves CremePropertyType objects too)

    for i, entity in enumerate(entities):
        if entity.id == subject_id:
            subject = entity
            entities.pop(i)
            break
    else:
        raise Http404('Can not find entity with id=%s' % subject_id)

    subject.can_link_or_die(user)

    errors = defaultdict(list)
    len_diff = len(entity_ids) - len(entities)

    if len_diff != 1: #'subject' has been poped from entities, but not subject_id from entity_ids, so 1 and not 0
        errors[404].append(_(u"%s entities doesn't exist / doesn't exist any more") % len_diff)

    #TODO: move in a RelationType method ??
    subject_ctypes = frozenset(int(ct_id) for ct_id in rtype.subject_ctypes.values_list('id', flat=True))
    if subject_ctypes and subject.entity_type_id not in subject_ctypes:
        raise Http404('Incompatible type for subject') #404 ??

    if subject_properties and not any(p.type_id in subject_properties for p in subject.get_properties()):
        raise Http404('Missing compatible property for subject') #404 ??

    #TODO: move in a RelationType method ??
    object_ctypes = frozenset(int(ct_id) for ct_id in rtype.object_ctypes.values_list('id', flat=True))
    check_ctype = (lambda e: e.entity_type_id in object_ctypes) if object_ctypes else \
                  lambda e: True

    check_properties = (lambda e: any(p.type_id in object_properties for p in e.get_properties())) if object_properties else \
                       lambda e: True

    create_relation = Relation.objects.create
    for entity in entities:
        if not check_ctype(entity):
            errors[404].append(_(u"Incompatible type for object entity with id=%s") % entity.id) #404 ??
        elif not check_properties(entity):
            errors[404].append(_(u"Missing compatible property for object entity with id=%s") % entity.id) #404 ??
        elif not entity.can_link(user):
            errors[403].append(_("Permission denied to entity with id=%s") % entity.id)
        else:
            create_relation(subject_entity=subject, type=rtype, object_entity=entity, user=user)

    if not errors:
        status = 200
        message = _(u"Operation successfully completed")
    else:
        status = min(errors.iterkeys())
        message = ",".join(msg for error_messages in errors.itervalues() for msg in error_messages)

    return HttpResponse(message, status=status)
