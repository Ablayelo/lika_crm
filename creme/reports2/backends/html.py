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

from django.template.loader import render_to_string
from base import ReportBackend

class HtmlReportBackend(ReportBackend):

    def __init__(self, report, context_instance, template="reports2/backends/html_report.html" ):
        super(HtmlReportBackend, self).__init__(report, template)
        self.context_instance = context_instance

    def render(self):
        return render_to_string(self.template, {'data' : self.report.fetch_all_lines()}, context_instance=self.context_instance)

    def render_to_response(self):
        pass

