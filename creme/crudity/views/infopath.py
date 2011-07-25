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
from django.contrib.auth.decorators import permission_required, login_required
from django.http import Http404
from crudity.backends.registry import from_email_crud_registry
from crudity.builders.infopath import InfopathFormBuilder

@login_required
@permission_required('crudity')
def create_form(request, subject):
    subject = subject.upper()
    create_be = from_email_crud_registry.get_creates()
    backend = create_be.get(subject)

    if backend is None:
        raise Http404(u"This backend is not registered")

    return InfopathFormBuilder(request, backend).render()
