# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder as JSONEncoder
#from django.db.models.query_utils import Q
from django.http import HttpResponse, Http404
from django.contrib.contenttypes.models import ContentType
#from django.utils.translation import ugettext

from ..registry import creme_registry
from ..core.exceptions import ConflictError


logger = logging.getLogger(__name__)


def creme_entity_content_types():
    get_for_model = ContentType.objects.get_for_model
    return (get_for_model(model) for model in creme_registry.iter_entity_models())

def Q_creme_entity_content_types():
    return ContentType.objects.filter(pk__in=[ct_model.pk for ct_model in creme_entity_content_types()])

def get_ct_or_404(ct_id):
    try:
        ct = ContentType.objects.get_for_id(ct_id)
    except ContentType.DoesNotExist:
        raise Http404('No content type with this id: %s' % ct_id)

    return ct

def create_or_update(model, pk=None, **attrs):
    """Get a model instance by its PK, or create a new one ; then set its attributes.
    @param model Django model (class)
    @param pk PK of the wanted instance ; if None, PK is generated by the sql server.
    @param attrs Values of the attributes.
    """
    if pk is not None:
        try:
            instance = model.objects.get(pk=pk)
        except ObjectDoesNotExist:
            instance = model(id=pk)
    else:
        instance = model()

    for key, val in attrs.iteritems():
        setattr(instance, key, val)

    instance.save()

    return instance

def create_if_needed(model, get_dict, **attrs):
    try:
        instance = model.objects.get(**get_dict)
    except model.DoesNotExist:
        attrs.update(get_dict)
        instance = model.objects.create(**attrs)

    return instance

def jsonify(func):
    def _aux(*args, **kwargs):
        status = 200

        try:
            rendered = func(*args, **kwargs)
        except Http404 as e:
            msg = unicode(e)
            status = 404
        except PermissionDenied as e:
            msg = unicode(e)
            status = 403
        except ConflictError as e:
            msg = unicode(e)
            status = 409
        except Exception as e:
            logger.debug('Exception in @jsonify(%s): %s', func.__name__, e)
            msg = unicode(e)
            status = 400
        else:
            msg = JSONEncoder().encode(rendered)

        return HttpResponse(msg, mimetype='text/javascript', status=status)

    return _aux

def _get_from_request_or_404(method, method_name, key, cast=None, **kwargs):
    """@param cast A function that cast the return value, and raise an Exception if it is not possible (eg: int)
    """
    value = method.get(key)

    if value is None:
        if 'default' not in kwargs:
            raise Http404('No %s argument with this key: %s' % (method_name, key))

        value = kwargs['default']

    if cast:
        try:
            value = cast(value)
        except Exception as e:
            raise Http404('Problem with argument "%s" : it can not be coerced (%s)' % (key, str(e)))

    return value

def get_from_GET_or_404(GET, key, cast=None, **kwargs):
    return _get_from_request_or_404(GET, 'GET', key, cast, **kwargs)

def get_from_POST_or_404(POST, key, cast=None, **kwargs):
    return _get_from_request_or_404(POST, 'POST', key, cast, **kwargs)

def find_first(iterable, function, *default):
    """
    @param default Optionnal argument.
    """
    for elt in iterable:
        if function(elt):
            return elt

    if default:
        return default[0]

    raise IndexError

def entities2unicode(entities, user):
    """Return a unicode objects representing a sequence of CremeEntities,
    with care of permissions.
    """
    return u', '.join(entity.allowed_unicode(user) for entity in entities)

def related2unicode(entity, user):
    """Return a unicode object representing a related entity with its owner,
    with care of permissions of this owner.
    """
    return u'%s - %s' % (entity.get_related_entity().allowed_unicode(user), unicode(entity))

__B2S_MAP = {
        'true':  True,
        'false': False,
    }

def bool_from_str(string):
    b = __B2S_MAP.get(string.lower())

    if b is not None:
        return b

    raise ValueError('Can not be coerced to a boolean value: %s' % str(string))

def truncate_str(str, max_length, suffix=""):
    if max_length <= 0:
        return ""

    len_str = len(str)
    if len_str <= max_length and not suffix:
        return str

    total = max_length - len(suffix)
    if total > 0:
        return str[:total] + suffix
    elif total == 0:
        return suffix
    else:
        return str[:total]

def is_testenvironment(request):
    return request.META.get('SERVER_NAME') == 'testserver'

def safe_unicode(value, encodings=None):
    if isinstance(value, unicode):
        return value

    if not isinstance(value, basestring):
        value = value.__unicode__() if hasattr(value, '__unicode__') else repr(value)
        return safe_unicode(value, encodings)

    encodings = encodings or ('utf-8', 'cp1252', 'iso-8859-1',)

    for encoding in encodings:
        try:
            return unicode(value, encoding=encoding)
        except Exception:
            continue

    return unicode(value, encoding='utf-8', errors='replace')

def safe_unicode_error(err, encodings=None):
    #return safe_unicode(err.message) #this method is deprecated for python 3.* but str/unicode conversions won't be useful at all

    #Is this method deprecated for python 3.* (but str/unicode conversions won't be useful at all) ??
    try:
        return unicode(err)
    except:
        pass

    msg = err.message

    #if isinstance(msg, basestring):
    return safe_unicode(msg, encodings)

    #try:
        #return unicode(msg)
    #except:
        #pass

    #return unicode(err.__class__.__name__)
