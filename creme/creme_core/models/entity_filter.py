# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

#from future_builtins import filter
from datetime import datetime # date
from itertools import izip_longest
import logging
from re import compile as compile_re
import warnings

from django.db.models import (Model, CharField, TextField, BooleanField,
        PositiveSmallIntegerField, ForeignKey, Q)
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.signals import pre_delete
#from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.simplejson import loads as jsonloads, dumps as jsondumps
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy, ngettext
from django.utils.timezone import now

from ..global_info import get_global_info
from ..utils import update_model_instance
from ..utils.date_range import date_range_registry
from ..utils.dates import make_aware_dt, date_2_dict
from ..utils.meta import is_date_field, FieldInfo #get_model_field_info
from .relation import RelationType, Relation
from .custom_field import CustomField
from .fields import CremeUserForeignKey, CTypeForeignKey


logger = logging.getLogger(__name__)


class EntityFilterList(list):
    """Contains all the EntityFilter objects corresponding to a CremeEntity's ContentType.
    Indeed, it's as a cache.
    """
    #def __init__(self, content_type):
        #super(EntityFilterList, self).__init__(EntityFilter.objects.filter(entity_type=content_type))
        #self._selected = None
    def __init__(self, content_type, user):
        super(EntityFilterList, self).__init__(EntityFilter.get_for_user(user, content_type))
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def select_by_id(self, *ids):
        """Try several EntityFilter ids"""
        #linear search but with few items after all....
        for efilter_id in ids:
            for efilter in self:
                if efilter.id == efilter_id:
                    self._selected = efilter
                    return efilter

        return self._selected


class EntityFilterVariable(object):
    CURRENT_USER = '__currentuser__'

    def validate(self, field, value):
        return field.formfield().clean(value)


class _CurrentUserVariable(EntityFilterVariable):
    def resolve(self, value, user=None):
        return user.pk if user is not None else None

    def validate(self, field, value):
        if not isinstance(field, ForeignKey) or not issubclass(field.rel.to, User):
            return field.formfield().clean(value) 

        if isinstance(value, basestring) and value == EntityFilterVariable.CURRENT_USER:
            return

        field.formfield().clean(value)


class EntityFilter(Model): #CremeModel ???
    """A model that contains conditions that filter queries on CremeEntity objects.
    They are principally used in the list views.
    Conditions can be :
     - On regular fields (eg: CharField, IntegerField) with a special behaviour for date fields.
     - On related fields (throught ForeignKey or Many2Many).
     - On CustomFields (with a special behaviour for CustomFields with DATE type).
     - An other EntityFilter
     - The existence (or the not existence) of a kind of Relationship.
     - The holding (or the not holding) of a kind of CremeProperty
    """
    id          = CharField(primary_key=True, max_length=100, editable=False).set_tags(viewable=False)
    name        = CharField(max_length=100, verbose_name=_('Name'))
    user        = CremeUserForeignKey(verbose_name=_(u'Owner user'), blank=True, null=True).set_tags(viewable=False) #verbose_name=_(u'Owner')
    #entity_type = ForeignKey(ContentType, editable=False)
    entity_type = CTypeForeignKey(editable=False).set_tags(viewable=False)
    is_custom   = BooleanField(editable=False, default=True).set_tags(viewable=False)
    is_private  = BooleanField(pgettext_lazy('creme_core-entity_filter', u'Is private?'), default=False) #'True' means: can only be viewed (and so edited/deleted) by its owner.
    use_or      = BooleanField(verbose_name=_(u'Use "OR"'), default=False).set_tags(viewable=False)

    creation_label = _('Add a filter')
    _conditions_cache = None
    _connected_filter_cache = None
    _subfilter_conditions_cache = None

    _VARIABLE_MAP = {
            EntityFilterVariable.CURRENT_USER: _CurrentUserVariable()
        }

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Filter of Entity')
        verbose_name_plural = _(u'Filters of Entity')
        ordering = ('name',)

    class CycleError(Exception):
        pass

    class DependenciesError(Exception):
        pass

    class PrivacyError(Exception):
        pass

    def __unicode__(self):
        return self.name

    def can_edit_or_delete(self, user):
        warnings.warn("EntityFilter.can_edit_or_delete() method is deprecated; use can_edit()/can_delete() methods instead",
                      DeprecationWarning
                     )

        if not self.is_custom:
            return (False, ugettext(u"This filter can't be edited/deleted"))

        if not self.user_id: #all users allowed
            return (True, 'OK')

        if user.is_superuser:
            return (True, 'OK')

        if not user.has_perm(self.entity_type.app_label):
            return (False, ugettext(u"You are not allowed to access to this app"))

        if not self.user.is_team:
            if self.user_id == user.id:
                return (True, 'OK')
        elif self.user.team_m2m_teamside.filter(teammate=user).exists(): #TODO: move in a User method ??
            return (True, 'OK')

        return (False, ugettext(u"You are not allowed to edit/delete this filter"))

    def can_delete(self, user):
        if not self.is_custom:
            return (False, ugettext(u"This filter can't be edited/deleted"))

        return self.can_edit(user)

    def can_edit(self, user):
        assert not user.is_team

        if not self.user_id: #all users allowed
            return (True, 'OK')

        if user.is_staff:
            return (True, 'OK')

        #if user.is_superuser:
        if user.is_superuser and not self.is_private:
            return (True, 'OK')

        if not user.has_perm(self.entity_type.app_label):
            return (False, ugettext(u"You are not allowed to access to this app"))

        if not self.user.is_team:
            if self.user_id == user.id:
                return (True, 'OK')
        #elif self.user.team_m2m_teamside.filter(teammate=user).exists():
        elif user.id in self.user.teammates: #TODO: move in a User method ??
            return (True, 'OK')

        return (False, ugettext(u"You are not allowed to view/edit/delete this filter"))

    def can_view(self, user, content_type=None):
        if content_type and content_type != self.entity_type:
            return (False, 'Invalid entity type')

        return self.can_edit(user)

    def check_cycle(self, conditions):
        assert self.id

        #Ids of EntityFilters that are referenced by these conditions
        ref_filter_ids = {sf_id for sf_id in (cond._get_subfilter_id() for cond in conditions) if sf_id}

        if self.id in ref_filter_ids:
            raise EntityFilter.CycleError(ugettext(u'A condition can not reference its own filter.'))

        if self.get_connected_filter_ids() & ref_filter_ids: #TODO: method intersection not null
            raise EntityFilter.CycleError(ugettext(u'There is a cycle with a subfilter.'))

    def _check_privacy_parent_filters(self, is_private, owner):
        if not self.id:
            return # cannot have a parent because we are creating the filter

        if not is_private:
            return # public children filters cannot cause problem to their parents

        for cond in self._iter_parent_conditions():
            parent_filter = cond.filter

            if not parent_filter.is_private:
                raise EntityFilter.PrivacyError(
                            ugettext(u'This filter cannot be private because '
                                     u'it is a sub-filter for the public filter "%s"'
                                    ) % parent_filter.name
                        )

            if owner.is_team:
                parent_user = parent_filter.user

                if parent_filter.user.is_team:
                    if parent_filter.user != owner:
                        raise EntityFilter.PrivacyError(
                                    ugettext(u'This filter cannot be private and belong to this team '
                                             u'because it is a sub-filter for the filter "%(filter)s" '
                                             u'which belongs to the team "%(team)s".'
                                            ) % {'filter': parent_filter.name,
                                                 'team':   parent_filter.user,
                                                }
                                )
                elif parent_filter.user.id not in owner.teammates:
                    raise EntityFilter.PrivacyError(
                                ugettext(u'This filter cannot be private and belong to this team '
                                         u'because it is a sub-filter for the filter "%(filter)s" '
                                         u'which belongs to the user "%(user)s" (who is not a member of this team).'
                                        ) % {'filter': parent_filter.name,
                                             'user':   parent_filter.user,
                                            }
                            )
            else:
                if not parent_filter.can_view(owner)[0]:
                    raise EntityFilter.PrivacyError(
                                ugettext(u'This filter cannot be private because '
                                         u'it is a sub-filter for a private filter of another user.'
                                        )
                            )

                if parent_filter.user.is_team:
                    raise EntityFilter.PrivacyError(
                                ugettext(u'This filter cannot be private and belong to a user '
                                         u'because it is a sub-filter for the filter "%s" which belongs to a team.'
                                        ) % parent_filter.name
                            )

    def _check_privacy_sub_filters(self, conditions, is_private, owner):
        #TODO: factorise
        ref_filter_ids = {sf_id for sf_id in (cond._get_subfilter_id() for cond in conditions) if sf_id}

        if is_private:
            if not owner:
                raise EntityFilter.PrivacyError(ugettext(u'A private filter must be assigned to a user/team.'))

            if owner.is_team:
                # All the teammate should have the permission to see the sub-filters,
                # so they have to be public or belong to the team.
                invalid_filter_names = EntityFilter.objects \
                                                   .filter(pk__in=ref_filter_ids, is_private=True) \
                                                   .exclude(user=owner) \
                                                   .values_list('name', flat=True)

                if invalid_filter_names:
                    raise EntityFilter.PrivacyError(
                                ngettext(u'A private filter which belongs to a team can only use public sub-filters & private sub-filters which belong to this team.'
                                         u' So this private sub-filter cannot be chosen: %s',
                                         u'A private filter which belongs to a team can only use public sub-filters & private sub-filters which belong to this team.'
                                         u' So these private sub-filters cannot be chosen: %s',
                                         len(invalid_filter_names)
                                        ) % u', '.join(invalid_filter_names)
                            )
            else:
                invalid_filter_names = EntityFilter.objects \
                                                   .filter(pk__in=ref_filter_ids, is_private=True) \
                                                   .exclude(user__in=[owner] + owner.teams) \
                                                   .values_list('name', flat=True)

                if invalid_filter_names:
                    raise EntityFilter.PrivacyError(
                                ngettext(u'A private filter which can use public sub-filters, & private sub-filters which belong to the same user and his teams.'
                                         u' So this private sub-filter cannot be chosen: %s',
                                         u'A private filter which can use public sub-filters, & private sub-filters which belong to the same user and his teams.'
                                         u' So these private sub-filters cannot be chosen: %s',
                                         len(invalid_filter_names)
                                        ) % u', '.join(invalid_filter_names)
                            )
        else:
            invalid_filter_names = EntityFilter.objects \
                                               .filter(pk__in=ref_filter_ids, is_private=True) \
                                               .values_list('name', flat=True)

            if invalid_filter_names:
                # All user can see this filter, so all user should have the permission
                # to see the subfilters too ; so they have to be public (is_private=False)
                raise EntityFilter.PrivacyError(
                            ngettext(u'Your filter must be private in order to use this private sub-filter: %s',
                                     u'Your filter must be private in order to use these private sub-filters: %s',
                                     len(invalid_filter_names)
                                    ) % u', '.join(invalid_filter_names)
                        )

    def check_privacy(self, conditions, is_private, owner):
        "@raises EntityFilter.PrivacyError"
        self._check_privacy_sub_filters(conditions, is_private, owner)
        self._check_privacy_parent_filters(is_private, owner)

    #@staticmethod
    #def create(pk, name, model, is_custom=False, user=None, use_or=False):
        #"""Creation helper ; useful for populate.py scripts."""
        #from creme.creme_core.utils import create_or_update

        #ef = create_or_update(EntityFilter, pk=pk,
                              #name=name, is_custom=is_custom, user=user, use_or=use_or,
                              #entity_type=ContentType.objects.get_for_model(model)
                             #)

        #return ef
    @staticmethod
    def create(pk, name, model, is_custom=False, user=None, use_or=False,
               is_private=False, conditions=(),
              ):
        """Creation helper ; useful for populate.py scripts.
        @param user Can be None (ie: 'All users'), a User instance, or the string
                    'admin', which means 'the first admin user'.
        """
        forbidden = {'[', ']', '#', '?'} #'&'

        if any((c in forbidden) for c in pk):
            raise ValueError('EntityFilter.create(): invalid character in "pk" (forbidden: %s)' % forbidden)

        if is_private:
            if not user:
                raise ValueError('EntityFilter.create(): a private filter must belong to a User.')

            if not is_custom:
                # It should not be useful to create a private EntityFilter (so it
                # belongs to a user) which cannot be deleted.
                raise ValueError('EntityFilter.create(): a private filter must be custom.')

        if isinstance(user, User):
            if user.is_staff:
                # Staff users cannot be owner in order to stay 'invisible'.
                raise ValueError('EntityFilter.create(): the owner cannot be a staff user.')
        elif user == 'admin':
            user_qs = User.objects.order_by('id')
            try:
                user = user_qs.filter(is_superuser=True, is_staff=False)[0]
            except IndexError:
                try:
                    user = user_qs.filter(is_superuser=True)[0]
                except IndexError:
                    user = user_qs[0]

        ct = ContentType.objects.get_for_model(model)

        if is_custom:
            try:
                ef = EntityFilter.objects.get(pk=pk)
            except EntityFilter.DoesNotExist:
                ef = EntityFilter.objects.create(pk=pk, name=name, is_custom=is_custom,
                                                 user=user, use_or=use_or, entity_type=ct,
                                                 is_private=is_private,
                                                )
            else:
                if ef.entity_type != ct:
                    # Changing the ContentType would create mess in related Report for example.
                    raise ValueError('You cannot change the entity type of an existing filter')

                if not ef.is_custom:
                    raise ValueError('You cannot change the "is_custom" value of an existing filter')

                update_model_instance(ef, name=name, user=user, use_or=use_or)
        else:
            if not conditions:
                raise ValueError('You must provide conditions for a non-custom Filter '
                                 '(in order to compare with existing ones)'
                                )

            try:
                ef = EntityFilter.get_latest_version(pk)
            except EntityFilter.DoesNotExist:
                ef = EntityFilter.objects.create(pk=pk, name=name, is_custom=is_custom,
                                                 user=user, use_or=use_or, entity_type=ct,
                                                )
            else:
                if ef.entity_type != ct:
                    raise ValueError('You cannot change the entity type of an existing filter')

                if ef.is_custom:
                    raise ValueError('You cannot change the "is_custom" value of an existing filter')

                if use_or != ef.use_or or \
                   not EntityFilterCondition.conditions_equal(conditions, ef.get_conditions()):
                    from creme import __version__

                    new_pk = '%s[%s]' % (pk, __version__)
                    new_name = u'%s [%s]' % (name, __version__)

                    latest_pk = ef.pk

                    if latest_pk.startswith(new_pk):
                        copy_num_str = latest_pk[len(new_pk):]

                        if not copy_num_str:
                            new_pk += '2'
                            new_name += '(2)'
                        else:
                            try:
                                copy_num = int(copy_num_str) + 1
                            except ValueError:
                                raise ValueError('Malformed EntityFilter PK/version: %s', latest_pk)

                            new_pk += str(copy_num)
                            new_name += '(%i)' % copy_num

                    ef = EntityFilter.objects.create(pk=new_pk, name=new_name,
                                                     is_custom=is_custom,
                                                     user=user, use_or=use_or, entity_type=ct,
                                                    )
                else:
                    update_model_instance(ef, name=name)

        ef.set_conditions(conditions)

        return ef

    def delete(self):
        parents = {unicode(cond.filter) for cond in self._iter_parent_conditions()}

        if parents:
            raise EntityFilter.DependenciesError(ugettext(u'You can not delete this filter, because it is used as subfilter by : %s') % \
                                                    u', '.join(parents)
                                                )

        super(EntityFilter, self).delete()

    def filter(self, qs, user=None):
        #distinct is useful with condition on m2m that can retrieve several times the same Entity
        return qs.filter(self.get_q(user)).distinct()

    def _get_subfilter_conditions(self):
        sfc = self._subfilter_conditions_cache

        if sfc is None:
            self._subfilter_conditions_cache = sfc = \
                EntityFilterCondition.objects.filter(Q(type=EntityFilterCondition.EFC_SUBFILTER,
                                                       filter__entity_type=self.entity_type,
                                                      ) |
                                                     Q(type=EntityFilterCondition.EFC_RELATION_SUBFILTER)
                                                    )

        return sfc

    def _iter_parent_conditions(self):
        pk = self.id 

        for cond in self._get_subfilter_conditions():
            if cond._get_subfilter_id() == pk:
                yield cond

    def get_connected_filter_ids(self):
        #NB: 'level' means a level of filters connected to this filter :
        #  - 1rst level is 'self'.
        #  - 2rst level is filters with a sub-filter conditions relative to 'self'.
        #  - 3rd level  is filters with a sub-filter conditions relative to a filter of the 2nd level.
        # etc....
        if self._connected_filter_cache:
            return self._connected_filter_cache

        self._connected_filter_cache = connected = level_ids = {self.id}

        #Sub-filters conditions
        sf_conds = [(cond, cond._get_subfilter_id()) for cond in self._get_subfilter_conditions()]

        while level_ids:
            level_ids = {cond.filter_id for cond, filter_id in sf_conds if filter_id in level_ids}
            connected.update(level_ids)

        return connected

    @staticmethod
    def get_for_user(user, content_type=None):
        """Get the EntityFilter queryset corresponding of filters which a user can see.
        @param user A User instance.
        @param content_type None (means 'for all ContentTypes').
                            A ContentType instance (means 'filters related to this CT').
                            An iterable of ContentType instances (means 'filters related to these CT').
        """
        assert not user.is_team

        qs = EntityFilter.objects.all()

        if content_type:
            qs = qs.filter(entity_type=content_type) if isinstance(content_type, ContentType) else \
                 qs.filter(entity_type__in=content_type)

        return qs if user.is_staff else \
               qs.filter(Q(is_private=False) |
                         Q(is_private=True, user__in=[user] + user.teams)
                        )

    def get_q(self, user=None):
        query = Q()

        if user is None:
            user = get_global_info('user')

        if self.use_or:
            for condition in self.get_conditions():
                query |= condition.get_q(user)
        else:
            for condition in self.get_conditions():
                query &= condition.get_q(user)

        return query

    def _build_conditions_cache(self, conditions):
        self._conditions_cache = checked_conds = []
        append = checked_conds.append

        for condition in conditions:
            condition.filter = self
            error = condition.error

            if error:
                logger.warn('%s => EntityFilterCondition instance removed', error)
                condition.delete()
            else:
                append(condition)

    def get_conditions(self):
        if self._conditions_cache is None:
            self._build_conditions_cache(self.conditions.all())

        return self._conditions_cache

    #def set_conditions(self, conditions, check_cycles=True):
    def set_conditions(self, conditions, check_cycles=True, check_privacy=True):
        if check_cycles:
            self.check_cycle(conditions)

        if check_privacy:
            self.check_privacy(conditions, self.is_private, owner=self.user)

        old_conditions = EntityFilterCondition.objects.filter(filter=self).order_by('id')
        conds2del = []

        for old_condition, condition in izip_longest(old_conditions, conditions):
            if not condition: #less new conditions that old conditions => delete conditions in excess
                conds2del.append(old_condition.id)
            elif not old_condition:
                condition.filter = self
                condition.save()
            elif old_condition.update(condition):
                old_condition.save()
                condition.pk = old_condition.pk #if there is an error we delete it

        if conds2del:
            EntityFilterCondition.objects.filter(pk__in=conds2del).delete()

        self._build_conditions_cache(conditions)

    #TODO: in the manager ?
    @staticmethod
    def get_latest_version(base_pk):
        """Get the latest EntityFilter from the family which uses the 'base_pk'.
        @raises EntityFilter.DoesNotExist If there is none instance in this family
        """
        efilters = list(EntityFilter.objects.filter(Q(pk=base_pk) | Q(pk__startswith=base_pk + '[')))

        if not efilters:
            raise EntityFilter.DoesNotExist('No EntityFilter with pk="%s"' % base_pk)

        #VERSION_RE = compile_re(r'([\w,-]+)(\[(?P<version_num>\d[\d\.]+)( (?P<version_mod>alpha|beta|rc)(?P<version_modnum>\d+)?)?\])$')
        VERSION_RE = compile_re(r'([\w,-]+)(\[(?P<version_num>\d[\d\.]+)( (?P<version_mod>alpha|beta|rc)(?P<version_modnum>\d+)?)?\](?P<copy_num>\d+)?)?$')

        def key(efilter):
            # we build a tuple which can easily compared with the other generated tuples.
            # Example of PKs: 'base_pk' 'base_pk[1.15]' 'base_pk[1.15 alpha]'
            #                 'base_pk[1.15 rc]' 'base_pk[1.15 rc11]' 'base_pk[1.15 rc11]2'
            # eg: 'base_pk[1.15 rc11]2'
            #   ==> we extract '1.15', 'aplha', '11' & '2' and build ((1, 15), 'rc', 11, 2)
            search = VERSION_RE.search(efilter.pk)

            if not search:
                logger.critical('Malformed EntityFilter PK/version: %s', efilter.pk)
                return ((-1,),)

            groupdict = search.groupdict()
            version_num = groupdict['version_num'] # eg '1.5'
            if not version_num:
                return ((0,),)

            version_num_tuple = tuple(int(x) for x in version_num.split('.'))

            version_mod = groupdict['version_mod'] or '' # '', alpha', 'beta' or 'rc' -> yeah, they are already alphabetically sorted

            version_modnum_str = groupdict['version_modnum'] # eg '11' in 'rc11'
            version_modnum = int(version_modnum_str) if version_modnum_str else 1

            copy_num_str = groupdict['copy_num'] # eg '11' in 'base_pk[1.5]11'
            copy_num = int(copy_num_str) if copy_num_str else 0

            return (version_num_tuple, version_mod, version_modnum, copy_num)

        efilters.sort(key=key)

        return efilters[-1] #TODO: max()

    @staticmethod
    def get_variable(value):
        return EntityFilter._VARIABLE_MAP.get(value) if isinstance(value, basestring) else None

    @staticmethod
    def resolve_variable(value, user):
        variable = EntityFilter.get_variable(value)
        return variable.resolve(value, user) if variable else value


class _ConditionOperator(object):
    __slots__ = ('name', '_accept_subpart', '_exclude', '_key_pattern', '_allowed_fieldtypes')

    #Fields for which the subpart of a valid value is not valid
    _NO_SUBPART_VALIDATION_FIELDS = {models.EmailField, models.IPAddressField}

    def __init__(self, name, key_pattern, exclude=False, accept_subpart=True, allowed_fieldtypes=None):
        self._key_pattern        = key_pattern
        self._exclude            = exclude
        self._accept_subpart     = accept_subpart
        self.name                = name

        # needed by javascript widget to filter operators for each field type 
        self._allowed_fieldtypes = allowed_fieldtypes or tuple()

    @property
    def allowed_fieldtypes(self):
        return self._allowed_fieldtypes

    @property
    def exclude(self):
        return self._exclude

    @property
    def key_pattern(self):
        return self._key_pattern

    @property
    def accept_subpart(self):
        return self._accept_subpart

    def __unicode__(self):
        return unicode(self.name)

    def get_q(self, efcondition, values):
        key = self.key_pattern % efcondition.name
        query = Q()

        for value in values:
            query |= Q(**{key: value})

        return query

    def validate_field_values(self, field, values):
        """Raises a ValidationError to notify of a problem with 'values'."""
        if not field.__class__ in self._NO_SUBPART_VALIDATION_FIELDS or not self.accept_subpart:
            clean = field.formfield().clean
            variable = None

            for value in values:
                variable = EntityFilter.get_variable(value)

                if variable is not None:
                    variable.validate(field, value)
                else:
                    clean(value)

        return values


class _ConditionBooleanOperator(_ConditionOperator):
    def validate_field_values(self, field, values):
        if len(values) != 1 or not isinstance(values[0], bool):
            raise ValueError(u'A list with one bool is expected for condition %s' % self.name)

        return values


class _IsEmptyOperator(_ConditionBooleanOperator):
    def __init__(self, name, exclude=False, **kwargs):
        super(_IsEmptyOperator, self).__init__(name, key_pattern='%s__isnull', exclude=exclude, accept_subpart=False, **kwargs)

    def get_q(self, efcondition, values):
        field_name = efcondition.name

        # as default, set isnull operator (allways true, negate is done later)
        query = Q(**{self.key_pattern % field_name: True})

        # add filter for text fields, "isEmpty" should mean null or empty string 
        #finfo = get_model_field_info(efcondition.filter.entity_type.model_class(), field_name)
        finfo = FieldInfo(efcondition.filter.entity_type.model_class(), field_name)
        #if isinstance(finfo[-1]['field'], (CharField, TextField)):
        if isinstance(finfo[-1], (CharField, TextField)):
            query |= Q(**{field_name: ''})

        # negate filter on false value
        if not values[0]:
            query.negate()

        return query


class _RangeOperator(_ConditionOperator):
    def __init__(self, name):
        super(_RangeOperator, self).__init__(name, '%s__range', allowed_fieldtypes=('number', 'date'))

    def validate_field_values(self, field, values):
        if len(values) != 2:
            raise ValueError(u'A list with 2 elements is expected for condition %s' % self.name)

        return [super(_RangeOperator, self).validate_field_values(field, values)]


class EntityFilterCondition(Model):
    """Tip: Use the helper methods build_4_* instead of calling constructor."""
    filter = ForeignKey(EntityFilter, related_name='conditions')
    type   = PositiveSmallIntegerField() #NB: see EFC_*
    name   = CharField(max_length=100)
    value  = TextField() #TODO: use a JSONField ?

    EFC_SUBFILTER          = 1
    EFC_FIELD              = 5
    EFC_DATEFIELD          = 6
    EFC_RELATION           = 10
    EFC_RELATION_SUBFILTER = 11
    EFC_PROPERTY           = 15
    EFC_CUSTOMFIELD        = 20
    EFC_DATECUSTOMFIELD    = 21

    #OPERATORS (fields, custom_fields)
    EQUALS          =  1
    IEQUALS         =  2
    EQUALS_NOT      =  3
    IEQUALS_NOT     =  4
    CONTAINS        =  5
    ICONTAINS       =  6
    CONTAINS_NOT    =  7
    ICONTAINS_NOT   =  8
    GT              =  9
    GTE             = 10
    LT              = 11
    LTE             = 12
    STARTSWITH      = 13
    ISTARTSWITH     = 14
    STARTSWITH_NOT  = 15
    ISTARTSWITH_NOT = 16
    ENDSWITH        = 17
    IENDSWITH       = 18
    ENDSWITH_NOT    = 19
    IENDSWITH_NOT   = 20
    ISEMPTY         = 21
    RANGE           = 22

    _FIELDTYPES_ALL  = {'string',
                        'enum', 'enum__null',
                        'number', 'number__null',
                        'date', 'date__null',
                        'boolean', 'boolean__null',
                        'fk', 'fk__null',
                        'user', 'user__null',
                       }

    _FIELDTYPES_ORDERABLE = {'number', 'number__null',
                             'date', 'date__null',
                            }

    _FIELDTYPES_RELATED = {'fk', 'fk__null',
                           'enum', 'enum__null',
                          }

    _OPERATOR_MAP = {
            EQUALS:          _ConditionOperator(_(u'Equals'),                                 '%s__exact',
                                                accept_subpart=False, allowed_fieldtypes=_FIELDTYPES_ALL),
            IEQUALS:         _ConditionOperator(_(u'Equals (case insensitive)'),              '%s__iexact',
                                                accept_subpart=False, allowed_fieldtypes=('string',)),
            EQUALS_NOT:      _ConditionOperator(_(u"Does not equal"),                         '%s__exact',
                                                exclude=True, accept_subpart=False, allowed_fieldtypes=_FIELDTYPES_ALL),
            IEQUALS_NOT:     _ConditionOperator(_(u"Does not equal (case insensitive)"),      '%s__iexact',
                                                exclude=True, accept_subpart=False, allowed_fieldtypes=('string',)),
            CONTAINS:        _ConditionOperator(_(u"Contains"),                               '%s__contains', allowed_fieldtypes=('string',)),
            ICONTAINS:       _ConditionOperator(_(u"Contains (case insensitive)"),            '%s__icontains', allowed_fieldtypes=('string',)),
            CONTAINS_NOT:    _ConditionOperator(_(u"Does not contain"),                       '%s__contains', exclude=True, allowed_fieldtypes=('string',)),
            ICONTAINS_NOT:   _ConditionOperator(_(u"Does not contain (case insensitive)"),    '%s__icontains', exclude=True, allowed_fieldtypes=('string',)),
            GT:              _ConditionOperator(_(u">"),                                      '%s__gt', allowed_fieldtypes=_FIELDTYPES_ORDERABLE),
            GTE:             _ConditionOperator(_(u">="),                                     '%s__gte', allowed_fieldtypes=_FIELDTYPES_ORDERABLE),
            LT:              _ConditionOperator(_(u"<"),                                      '%s__lt', allowed_fieldtypes=_FIELDTYPES_ORDERABLE),
            LTE:             _ConditionOperator(_(u"<="),                                     '%s__lte', allowed_fieldtypes=_FIELDTYPES_ORDERABLE),
            STARTSWITH:      _ConditionOperator(_(u"Starts with"),                            '%s__startswith', allowed_fieldtypes=('string',)),
            ISTARTSWITH:     _ConditionOperator(_(u"Starts with (case insensitive)"),         '%s__istartswith', allowed_fieldtypes=('string',)),
            STARTSWITH_NOT:  _ConditionOperator(_(u"Does not start with"),                    '%s__startswith', exclude=True, allowed_fieldtypes=('string',)),
            ISTARTSWITH_NOT: _ConditionOperator(_(u"Does not start with (case insensitive)"), '%s__istartswith', exclude=True, allowed_fieldtypes=('string',)),
            ENDSWITH:        _ConditionOperator(_(u"Ends with"),                              '%s__endswith', allowed_fieldtypes=('string',)),
            IENDSWITH:       _ConditionOperator(_(u"Ends with (case insensitive)"),           '%s__iendswith', allowed_fieldtypes=('string',)),
            ENDSWITH_NOT:    _ConditionOperator(_(u"Does not end with"),                      '%s__endswith', exclude=True, allowed_fieldtypes=('string',)),
            IENDSWITH_NOT:   _ConditionOperator(_(u"Does not end with (case insensitive)"),   '%s__iendswith', exclude=True, allowed_fieldtypes=('string',)),
            ISEMPTY:         _IsEmptyOperator(_(u"Is empty"), allowed_fieldtypes=('string', 'fk__null', 'user__null', 'enum__null', 'boolean__null')),
            RANGE:           _RangeOperator(_(u"Range")),
        }

    class Meta:
        app_label = 'creme_core'

    class ValueError(Exception):
        pass

    def __repr__(self):
        return u'EntityFilterCondition(filter_id=%(filter)s, type=%(type)s, name=%(name)s, value=%(value)s)' % {
                    'filter': self.filter_id,
                    'type':   self.type,
                    'name':   self.name or 'None',
                    'value':  self.value,
                }

    @staticmethod
    def build_4_customfield(custom_field, operator, value):
        if not EntityFilterCondition._OPERATOR_MAP.get(operator):
            raise EntityFilterCondition.ValueError('build_4_customfield(): unknown operator: %s', operator)

        if custom_field.field_type == CustomField.DATETIME:
            raise EntityFilterCondition.ValueError('build_4_customfield(): does not manage DATE CustomFields')

        if custom_field.field_type == CustomField.BOOL and operator != EntityFilterCondition.EQUALS:
            raise EntityFilterCondition.ValueError('build_4_customfield(): BOOL type is only compatible with EQUALS operator')

        cf_value_class = custom_field.get_value_class()

        try:
            if operator == EntityFilterCondition.ISEMPTY:
                operator_obj = EntityFilterCondition._OPERATOR_MAP.get(operator)
                operator_obj.validate_field_values(None, [value])
            else:
                cf_value_class.get_formfield(custom_field, None).clean(value)
        except Exception as e:
            raise EntityFilterCondition.ValueError(str(e))

        value = {'operator': operator,
                 'value':    value,
                 'rname':    cf_value_class.get_related_name(),
                }

        return EntityFilterCondition(type=EntityFilterCondition.EFC_CUSTOMFIELD,
                                     name=str(custom_field.id),
                                     value=EntityFilterCondition.encode_value(value)
                                    )

    @staticmethod
    def _build_daterange_dict(date_range=None, start=None, end=None):
        range_dict = {}

        if date_range:
            if not date_range_registry.get_range(date_range):
                raise EntityFilterCondition.ValueError('build_4_date(): invalid date range.')

            range_dict['name'] = date_range
        else:
            if start: range_dict['start'] = date_2_dict(start)
            if end:   range_dict['end']   = date_2_dict(end)

        if not range_dict:
            raise EntityFilterCondition.ValueError('date_range or start/end must be given.')

        return range_dict

    @staticmethod
    def build_4_date(model, name, date_range=None, start=None, end=None):
        try:
            ##field = model._meta.get_field(name)
            #finfo = get_model_field_info(model, name, silent=False)
            finfo = FieldInfo(model, name)
        except FieldDoesNotExist as e:
            raise EntityFilterCondition.ValueError(str(e))

        ##if not is_date_field(field):
        #if not is_date_field(finfo[-1]['field']):
        if not is_date_field(finfo[-1]):
            raise EntityFilterCondition.ValueError('build_4_date(): field must be a date field.')

        return EntityFilterCondition(type=EntityFilterCondition.EFC_DATEFIELD, name=name,
                                     value=EntityFilterCondition.encode_value(EntityFilterCondition._build_daterange_dict(date_range, start, end))
                                    )

    @staticmethod
    def build_4_datecustomfield(custom_field, date_range=None, start=None, end=None):
        if not custom_field.field_type == CustomField.DATETIME:
            raise EntityFilterCondition.ValueError('build_4_datecustomfield(): not a date custom field.')

        value = EntityFilterCondition._build_daterange_dict(date_range, start, end)
        value['rname'] = custom_field.get_value_class().get_related_name()

        return EntityFilterCondition(type=EntityFilterCondition.EFC_DATECUSTOMFIELD,
                                     name=str(custom_field.id),
                                     value=EntityFilterCondition.encode_value(value),
                                    )

    #TODO multivalue is stupid for some operator (LT, GT etc...) => improve checking ???
    @staticmethod
    def build_4_field(model, name, operator, values):
        """Search in the values of a model field.
        @param name Name of the field
        @param operator Operator ID ; see EntityFilterCondition.EQUALS and friends.
        @param values List of searched values (logical OR between them).
                      Exceptions: - RANGE: 'values' is always a list of 2 elements
                                  - ISEMPTY: 'values' is a list containing one boolean.
        """
        operator_obj = EntityFilterCondition._OPERATOR_MAP.get(operator)
        if not operator_obj:
            raise EntityFilterCondition.ValueError('Unknown operator: %s' % operator)

        try:
            #finfo = get_model_field_info(model, name, silent=False)
            finfo = FieldInfo(model, name)
        except FieldDoesNotExist as e:
            raise EntityFilterCondition.ValueError(str(e))

        try:
            #values = operator_obj.validate_field_values(finfo[-1]['field'], values)
            values = operator_obj.validate_field_values(finfo[-1], values)
        except Exception as e:
            raise EntityFilterCondition.ValueError(str(e))

        return EntityFilterCondition(type=EntityFilterCondition.EFC_FIELD,
                                     name=name, value=EntityFilterCondition.encode_value({'operator': operator, 'values': values})
                                    )

    @staticmethod
    def build_4_property(ptype, has=True):
        return EntityFilterCondition(type=EntityFilterCondition.EFC_PROPERTY, name=ptype.id,
                                     value=EntityFilterCondition.encode_value(bool(has))
                                    )

    @staticmethod
    def build_4_relation(rtype, has=True, ct=None, entity=None):
        value = {'has': bool(has)}

        if entity:
            value['entity_id'] = entity.id
        elif ct:
            value['ct_id'] = ct.id

        return EntityFilterCondition(type=EntityFilterCondition.EFC_RELATION,
                                     name=rtype.id,
                                     value=EntityFilterCondition.encode_value(value)
                                    )

    @staticmethod
    def build_4_relation_subfilter(rtype, subfilter, has=True):
        return EntityFilterCondition(type=EntityFilterCondition.EFC_RELATION_SUBFILTER,
                                     name=rtype.id,
                                     value=EntityFilterCondition.encode_value(
                                                {'has': bool(has), 'filter_id': subfilter.id}
                                            )
                                    )

    @staticmethod
    def build_4_subfilter(subfilter):
        assert isinstance(subfilter, EntityFilter)
        return EntityFilterCondition(type=EntityFilterCondition.EFC_SUBFILTER,
                                     name=subfilter.id,
                                    )

    @staticmethod
    def conditions_equal(conditions1, conditions2):
        """Compare 2 sequences on EntityFilterConditions related to the _same_
        EntityFilter instance.
        Beware: the 'filter' fields are not compared (so the related ContentType
        is not used).
        """
        key = lambda cond: (cond.type, cond.name, cond.value)

        return all(cond1 and cond2 and 
                   cond1.type == cond2.type and
                   cond1.name == cond2.name and
                   cond1.value == cond2.value
                        for cond1, cond2 in izip_longest(sorted(conditions1, key=key),
                                                         sorted(conditions2, key=key),
                                                        )
                  )

    @property
    def decoded_value(self):
        return jsonloads(self.value)

    @staticmethod
    def encode_value(value):
        return jsondumps(value)

    @property
    def error(self): #TODO: map of validators
        etype = self.type
        if etype == EntityFilterCondition.EFC_FIELD:
            try:
                #get_model_field_info(self.filter.entity_type.model_class(), self.name, silent=False)
                FieldInfo(self.filter.entity_type.model_class(), self.name)
            except FieldDoesNotExist as e:
                return str(e)
        elif etype == EntityFilterCondition.EFC_DATEFIELD:
            try: #TODO: factorise
                ##self.filter.entity_type.model_class()._meta.get_field(self.name)
                #finfo = get_model_field_info(self.filter.entity_type.model_class(), self.name, silent=False)
                finfo = FieldInfo(self.filter.entity_type.model_class(), self.name)
            except FieldDoesNotExist as e:
                return str(e)

            #if not is_date_field(finfo[-1]['field']):
            if not is_date_field(finfo[-1]):
                return '%s is not a date field' % self.name #TODO: test

    def _get_q_customfield(self, user):
        #NB: Sadly we retrieve the ids of the entity that match with this condition
        #    instead of use a 'JOIN', in order to avoid the interaction between
        #    several conditions on the same type of CustomField (ie: same table).
        search_info = self.decoded_value
        operator = EntityFilterCondition._OPERATOR_MAP[search_info['operator']]
        related_name = search_info['rname']
        fname = '%s__value' % related_name

        if isinstance(operator, _IsEmptyOperator):
            query = Q(**{'%s__isnull' % related_name: search_info['value']})
        else:
            query = Q(**{'%s__custom_field' % related_name: int(self.name),
                         operator.key_pattern % fname:      search_info['value'],
                        }
                     )

        if operator.exclude:
            query.negate()

        return Q(pk__in=self.filter.entity_type.model_class().objects.filter(query).values_list('id', flat=True))

    def _load_daterange(self, decoded_value):
        get = decoded_value.get
        kwargs = {'name': get('name')}

        for key in ('start', 'end'):
            date_kwargs = get(key)
            if date_kwargs:
                #kwargs[key] = date(**date_kwargs)
                kwargs[key] = make_aware_dt(datetime(**date_kwargs))

        return date_range_registry.get_range(**kwargs)

    def _get_q_datecustomfield(self, user):
        #NB: see _get_q_customfield() remark
        search_info = self.decoded_value
        related_name = search_info['rname']
        fname = '%s__value' % related_name

        q_dict = self._load_daterange(search_info).get_q_dict(field=fname, now=now())
        q_dict['%s__custom_field' % related_name] = int(self.name)

        return Q(pk__in=self.filter.entity_type.model_class().objects.filter(**q_dict).values_list('id', flat=True))

    def _get_q_field(self, user):
        search_info = self.decoded_value
        operator = EntityFilterCondition._OPERATOR_MAP[search_info['operator']]
        resolve = EntityFilter.resolve_variable
        values = [resolve(value, user) for value in search_info['values']]

        query = operator.get_q(self, values)

        if operator.exclude:
            query.negate()

        return query

    #TODO: "relations__*" => old method that does not work with several conditions
    #      on relations use it when there is only one condition on relations ??
    def _get_q_relation(self, user):
        #kwargs = {'relations__type': self.name}
        kwargs = {'type': self.name}
        value = self.decoded_value

        #for key, query_key in (('entity_id', 'relations__object_entity'), ('ct_id', 'relations__object_entity__entity_type')):
        for key, query_key in (('entity_id', 'object_entity'), ('ct_id', 'object_entity__entity_type')):
            arg = value.get(key)

            if arg:
                kwargs[query_key] = arg
                break

        #query = Q(**kwargs)
        query = Q(pk__in=Relation.objects.filter(**kwargs).values_list('subject_entity_id', flat=True))

        if not value['has']:
            query.negate()

        return query

    #TODO: "relations__*" => old method that does not work with several conditions
    #      on relations use it when there is only one condition on relations ??
    def _get_q_relation_subfilter(self, user):
        value = self.decoded_value
        subfilter = EntityFilter.objects.get(pk=value['filter_id'])
        filtered = subfilter.filter(subfilter.entity_type.model_class().objects.all()).values_list('id', flat=True)

        #query = Q(relations__type=self.name, relations__object_entity__in=filtered)
        query = Q(pk__in=Relation.objects.filter(type=self.name, object_entity__in=filtered)
                                         .values_list('subject_entity_id', flat=True)
                 )

        if not value['has']:
            query.negate()

        return query

    def _get_q_property(self, user):
        query = Q(properties__type=self.name)

        if not self.decoded_value: #is a boolean indicating if got or has not got the property type
            query.negate()

        return query

    _GET_Q_FUNCS = {
            EFC_SUBFILTER:          (lambda self, user: EntityFilter.objects.get(id=self.name).get_q(user)),
            EFC_FIELD:              _get_q_field,
            EFC_RELATION:           _get_q_relation,
            EFC_RELATION_SUBFILTER: _get_q_relation_subfilter,
            EFC_PROPERTY:           _get_q_property,
            EFC_DATEFIELD:          (lambda self, user: Q(**self._load_daterange(self.decoded_value).get_q_dict(field=self.name, now=now()))),
            EFC_CUSTOMFIELD:        _get_q_customfield,
            EFC_DATECUSTOMFIELD:    _get_q_datecustomfield,
        }

    def get_q(self, user=None):
        return EntityFilterCondition._GET_Q_FUNCS[self.type](self, user)

    def _get_subfilter_id(self):
        type = self.type

        if type == self.EFC_SUBFILTER:
            return self.name
        elif type == self.EFC_RELATION_SUBFILTER:
            return self.decoded_value['filter_id']

    def update(self, other_condition):
        """Fill a condition with the content a another one (in order to reuse the old instance if possible).
        @return True if there is at least one change, else False.
        """
        changed = False

        for attr in ('type', 'name', 'value'):
            other = getattr(other_condition, attr)

            if getattr(self, attr) != other:
                setattr(self, attr, other)
                changed = True

        return changed


def _delete_relationtype_efc(sender, instance, **kwargs):
    EntityFilterCondition.objects.filter(type__in=(EntityFilterCondition.EFC_RELATION,
                                                   EntityFilterCondition.EFC_RELATION_SUBFILTER
                                                  ),
                                         name=instance.id
                                        )\
                                 .delete()

def _delete_customfield_efc(sender, instance, **kwargs):
    EntityFilterCondition.objects.filter(type=EntityFilterCondition.EFC_CUSTOMFIELD, name=instance.id).delete()

pre_delete.connect(_delete_relationtype_efc, sender=RelationType)
pre_delete.connect(_delete_customfield_efc,  sender=CustomField)
