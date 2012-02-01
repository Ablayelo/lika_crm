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

from django.contrib.auth.decorators import permission_required, login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render

from vcfs.forms.vcf import VcfForm, VcfImportForm


@login_required
@permission_required('persons')
@permission_required('persons.add_contact')
def vcf_import(request):
    user = request.user

    if request.method == 'POST':
        POST = request.POST
        step = int(POST.get('vcf_step', 0))
        form = VcfForm(user=user, data=POST, files=request.FILES)

        if step == 0:
            if form.is_valid():
                form = VcfImportForm(user=user,
                                     vcf_data=form.cleaned_data['vcf_file'],
                                     initial={'vcf_step': 1,},
                                    )
        else:
            assert step == 1

            form = VcfImportForm(user=user, data=POST)

            if form.is_valid():
                contact = form.save()
                return HttpResponseRedirect(contact.get_absolute_url())

    else:
        form = VcfForm(user=user, initial={'vcf_step': 0})

    return render(request, 'creme_core/generics/blockform/edit.html', {'form': form})
