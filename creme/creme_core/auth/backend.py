# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.contrib.auth.backends import ModelBackend

from creme_core.models import EntityCredentials


_ADD_PREFIX = 'add_'
_EXPORT_PREFIX = 'export_'

class EntityBackend(ModelBackend):
    supports_object_permissions = True

    def has_perm(self, user_obj, perm, obj=None):
        if obj:
            return EntityCredentials.get_creds(user_obj, obj).has_perm(perm)

        if user_obj.role is not None:
            app_name, dot, action_name = perm.partition('.')

            if not action_name:
                if app_name == 'my_page': #NB: for side menu (TODO: can we improve that ??)
                    return True

                return user_obj.role.is_app_allowed_or_administrable(app_name)

            if action_name == 'can_admin':
                return app_name in user_obj.role.admin_4_apps

            if action_name.startswith(_ADD_PREFIX):
                return user_obj.role.can_create(app_name, action_name[len(_ADD_PREFIX):])

            if action_name.startswith(_EXPORT_PREFIX):
                return user_obj.role.can_export(app_name, action_name[len(_EXPORT_PREFIX):])

        #return super(EntityBackend, self).has_perm(user_obj, perm)
        return False
