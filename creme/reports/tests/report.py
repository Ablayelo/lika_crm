# -*- coding: utf-8 -*-

try:
    from datetime import datetime
    from decimal import Decimal
    from functools import partial
    from itertools import chain

    from django.contrib.contenttypes.models import ContentType
    from django.utils.datastructures import SortedDict as OrderedDict
    from django.utils.translation import ugettext as _
    from django.utils.encoding import smart_str
    from django.utils.unittest.case import skipIf
    #from django.core.serializers.json import simplejson

    from creme.creme_core.models import (RelationType, Relation,
        EntityFilter, EntityFilterCondition, CustomField, CustomFieldInteger)

    from creme.creme_core.models.header_filter import (HeaderFilterItem, HeaderFilter,
            HFI_FIELD, HFI_CUSTOM, HFI_RELATION, HFI_FUNCTION, HFI_CALCULATED)
    from creme.creme_core.constants import REL_SUB_HAS
    from creme.creme_core.utils.meta import get_verbose_field_name, get_instance_field_info

    from creme.documents.models import Folder, Document

    from creme.media_managers.models import Image

    from creme.persons.models import Contact, Organisation
    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_OBJ_CUSTOMER_SUPPLIER

    from creme.billing.models import Invoice

    from creme.opportunities.models import Opportunity
    from creme.opportunities.constants import REL_SUB_EMIT_ORGA

    from ..models import Field, Report
    from ..models.report import HFI_RELATED
    from .base import BaseReportsTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


try:
    from creme.creme_core.utils.xlrd_utils import XlrdReader
    from creme.creme_core.registry import export_backend_registry
    XlsImport = not 'xls' in export_backend_registry.iterkeys()
except Exception as e:
    XlsImport = True


__all__ = ('ReportTestCase',)


class ReportTestCase(BaseReportsTestCase):
    def test_portal(self):
        self.assertGET200('/reports/')

    def _create_cf_int(self):
        return CustomField.objects.create(content_type=ContentType.objects.get_for_model(Contact),
                                          name='Size (cm)', field_type=CustomField.INT
                                         )

    #def test_report_createview01(self):
        #cf = self._create_cf_int()

        #url = self.ADD_URL
        #response = self.assertGET200(url)

        #with self.assertNoException():
            #response.context['form'].fields['regular_fields']

        #name = 'My report on Contact'
        #data = {'user': self.user.pk,
                #'name': name,
                #'ct':   ContentType.objects.get_for_model(Contact).id,
               #}
        #self.assertFormError(self.client.post(url, data=data), 'form', None,
                             #[_(u"You must select an existing view, or at least one field from : %s") % 
                                #', '.join([_(u'Regular fields'), _(u'Related fields'),
                                           #_(u'Custom fields'), _(u'Relations'), _(u'Functions'),
                                           #_(u'Maximum'), _(u'Sum'), _(u'Average'), _(u'Minimum'),
                                          #])
                             #]
                            #)

        #response = self.client.post(url, follow=True,
                                    #data=dict(data,
                                              #**{'regular_fields_check_%s' % 1: 'on',
                                                 #'regular_fields_value_%s' % 1: 'last_name',
                                                 #'regular_fields_order_%s' % 1: 1,

                                                 #'custom_fields_check_%s' %  1: 'on',
                                                 #'custom_fields_value_%s' %  1: cf.id,
                                                 #'custom_fields_order_%s' %  1: 2,
                                                #}
                                             #)
                                   #)
        #self.assertNoFormError(response)

        #report = self.get_object_or_fail(Report, name=name)
        #columns = list(report.columns.all())
        #self.assertEqual(2, len(columns))

        #field = columns[0]
        #self.assertEqual('last_name',     field.name)
        #self.assertEqual(_(u'Last name'), field.title)
        #self.assertEqual(HFI_FIELD,       field.type)
        #self.assertFalse(field.selected)
        #self.assertFalse(field.report)

        #field = columns[1]
        #self.assertEqual(str(cf.id), field.name)
        #self.assertEqual(cf.name,    field.title)
        #self.assertEqual(HFI_CUSTOM, field.type)

    #def test_report_createview02(self):
    def test_report_createview01(self):
        cf = self._create_cf_int()

        name  = 'trinita'
        self.assertFalse(Report.objects.filter(name=name).exists())

        report = self.create_report(name, extra_hfitems=[HeaderFilterItem.build_4_customfield(cf)])
        self.assertEqual(self.user, report.user)
        self.assertEqual(Contact,   report.ct.model_class())
        self.assertIsNone(report.filter)

        columns = list(report.columns.all())
        self.assertEqual(5, len(columns))

        field = columns[0]
        self.assertEqual('last_name',     field.name)
        self.assertEqual(_(u'Last name'), field.title)
        self.assertEqual(HFI_FIELD,       field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.report)

        self.assertEqual('user', columns[1].name)

        field = columns[2]
        self.assertEqual(REL_SUB_HAS,  field.name)
        self.assertEqual(_(u'owns'),   field.title)
        self.assertEqual(HFI_RELATION, field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.report)

        field = columns[3]
        self.assertEqual('get_pretty_properties', field.name)
        self.assertEqual(_(u'Properties'),        field.title)
        self.assertEqual(HFI_FUNCTION,            field.type)

        field = columns[4]
        self.assertEqual(str(cf.id), field.name)
        self.assertEqual(cf.name,    field.title)
        self.assertEqual(HFI_CUSTOM, field.type)

    #def test_report_createview03(self):
    def test_report_createview02(self):
        "With EntityFilter"
        efilter = EntityFilter.create('test-filter', 'Mihana family', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=['Mihana']
                                                                   )
                               ])

        report  = self.create_report('My awesome report', efilter)
        self.assertEqual(efilter, report.filter)

    def test_report_createview03(self):
        "Validation errors"
        def post(hf_id, filter_id):
            return self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'user':   self.user.pk,
                                            'name':   'Report #1',
                                            'ct':     ContentType.objects.get_for_model(Contact).id,
                                            'hf':     hf_id,
                                            'filter': filter_id,
                                           }
                                     )

        response = post('unknown', 'unknown')
        msg = _('Select a valid choice. That choice is not one of the available choices.')
        self.assertFormError(response, 'form', 'hf',     msg)
        self.assertFormError(response, 'form', 'filter', msg)

        hf = HeaderFilter.create(pk='test_hf', name='name', model=Organisation)
        efilter = EntityFilter.create('test-filter', 'Bad filter', Organisation, is_custom=True)
        response = post(hf.id, efilter.id)
        self.assertFormError(response, 'form', 'hf',     msg)
        self.assertFormError(response, 'form', 'filter', msg)

    def test_report_editview(self):
        name = 'my report'
        report = self.create_report(name)
        url = '/reports/report/edit/%s' % report.id
        self.assertGET200(url)

        name = name.title()
        response = self.client.post(url, follow=True, 
                                    data={'user': self.user.pk,
                                          'name': name,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(report).name)

    def test_listview(self):
        reports = [self.create_report('Report#1'),
                   self.create_report('Report#2'),
                  ]

        response = self.assertGET200('/reports/reports')

        with self.assertNoException():
            reports_page = response.context['entities']

        for report in reports:
            self.assertIn(report, reports_page.object_list)

    def test_preview(self):
        create_c  = partial(Contact.objects.create, user=self.user)
        chiyo = create_c(first_name='Chiyo', last_name='Mihana', birthday=datetime(year=1995, month=3, day=26))
        osaka = create_c(first_name='Ayumu', last_name='Kasuga', birthday=datetime(year=1990, month=4, day=1))

        report = self.create_report('My report')
        url = '/reports/report/preview/%s' % report.id

        response = self.assertGET200(url)
        self.assertTemplateUsed('reports/preview_report.html')
        self.assertContains(response, chiyo.last_name)
        self.assertContains(response, osaka.last_name)

        response = self.assertPOST200(url,
                                      data={'date_filter_0': '',
                                            'date_filter_1': '1990-01-01',
                                            'date_filter_2': '1990-12-31',
                                            'date_field':    'birthday',
                                           }
                                     )
        self.assertTemplateUsed('reports/preview_report.html')
        self.assertNoFormError(response)
        self.assertContains(response, osaka.last_name)
        self.assertNotContains(response, chiyo.last_name)

    def test_report_change_field_order01(self):
        url = self.SET_FIELD_ORDER_URL
        self.assertPOST404(url)

        report = self.create_report('trinita')
        field  = self.get_field_or_fail(report, 'user')
        response = self.client.post(url, data={'report_id': report.id,
                                               'field_id':  field.id,
                                               'direction': 'up',
                                              }
                                   )
        self.assertNoFormError(response)

        report = self.refresh(report) #seems useless but...
        self.assertEqual(['user', 'last_name', REL_SUB_HAS, 'get_pretty_properties'],
                         [f.name for f in report.columns.order_by('order')]
                        )

    def test_report_change_field_order02(self):
        report = self.create_report('trinita')
        field  = self.get_field_or_fail(report, 'user')
        self.assertPOST200(self.SET_FIELD_ORDER_URL,
                           data={'report_id': report.id,
                                 'field_id':  field.id,
                                 'direction': 'down',
                                }
                          )

        report = self.refresh(report) #seems useless but...
        self.assertEqual(['last_name', REL_SUB_HAS, 'user', 'get_pretty_properties'],
                         [f.name for f in report.columns.order_by('order')]
                        )

    def test_report_change_field_order03(self):
        "Move 'up' the first field -> error"
        report = self.create_report('trinita')
        field  = self.get_field_or_fail(report, 'last_name')
        self.assertPOST403(self.SET_FIELD_ORDER_URL,
                           data={'report_id': report.id,
                                 'field_id':  field.id,
                                 'direction': 'up',
                                }
                          )

    def test_date_filter_form(self):
        report = self.create_report('My report')
        url = '/reports/date_filter_form/%s' % report.id
        response = self.assertGET200(url)

        date_field = 'birthday'
        response = self.assertPOST200(url,
                                      data={'date_filter_0': '',
                                            'date_filter_1': '1990-01-01',
                                            'date_filter_2': '1990-12-31',
                                            'date_field':    date_field,
                                           }
                                     )
        self.assertNoFormError(response)

        with self.assertNoException():
            callback_url = response.context['callback_url']

        self.assertEqual('/reports/report/export/%s/?field=%s'
                                                   '&range_name=base_date_range'
                                                   '&start=01|01|1990|00|00|00'
                                                   '&end=31|12|1990|23|59|59' % (
                                report.id, date_field,
                            ),
                         callback_url
                        )

    def test_report_csv01(self):
        "Empty report"
        self.assertFalse(Invoice.objects.all())

        rt = RelationType.objects.get(pk=REL_SUB_HAS)
        hf = HeaderFilter.create(pk='test_hf', name='Invoice view', model=Invoice)
        hf.set_items([HeaderFilterItem.build_4_field(model=Invoice, name='name'),
                      HeaderFilterItem.build_4_field(model=Invoice, name='user'),
                      HeaderFilterItem.build_4_relation(rt),
                      HeaderFilterItem.build_4_functionfield(Invoice.function_fields.get('get_pretty_properties')),
                     ])

        name = 'Report on invoices'
        self.assertPOST200(self.ADD_URL, follow=True, #TODO: factorise ??
                           data={'user': self.user.pk,
                                 'name': name,
                                 'ct':   ContentType.objects.get_for_model(Invoice).id,
                                 'hf':   hf.id,
                                }
                          )

        report = self.get_object_or_fail(Report, name=name)

        response = self.assertGET200('/reports/report/export/%s/csv' % report.id)
        self.assertEqual('text/html; charset=utf-8', response.request['CONTENT_TYPE'])
        self.assertEqual(smart_str('"%s","%s","%s","%s"\r\n' % (
                                      _(u'Name'), _(u'Owner user'), rt.predicate, _(u'Properties')
                                    )
                                  ),
                         response.content
                        )

    def test_report_csv02(self):
        self.create_contacts()
        self.assertEqual(4, Contact.objects.count()) #create_contacts + Fulbert

        report   = self.create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/csv' % report.id)

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(5, len(content)) #4 contacts + header
        self.assertEqual(smart_str('"%s","%s","%s","%s"' % (
                                      _(u'Last name'), _(u'Owner user'), _(u'owns'), _(u'Properties')
                                    )
                                  ),
                         content[0]
                        )
        self.assertEqual('"Ayanami","Kirika","","Kawaii"', content[1]) #alphabetical ordering ??
        self.assertEqual('"Creme","root","",""',           content[2])
        self.assertEqual('"Katsuragi","Kirika","Nerv",""', content[3])
        self.assertEqual('"Langley","Kirika","",""',       content[4])

    def test_report_csv03(self):
        "With date filter"
        self.create_contacts()
        report   = self.create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/csv' % report.id,
                                     data={'field': 'birthday',
                                           'start': datetime(year=1980, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                           'end':   datetime(year=2000, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                          }
                                    )

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(3, len(content))
        self.assertEqual('"Ayanami","Kirika","","Kawaii"', content[1])
        self.assertEqual('"Langley","Kirika","",""',       content[2])

    @skipIf(XlsImport, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_report_xls(self):
        "With date filter"
        self.create_contacts()
        report   = self.create_report('trinita')
        response = self.assertGET200('/reports/report/export/%s/xls' % report.id,
                                     data={'field': 'birthday',
                                           'start': datetime(year=1980, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                           'end':   datetime(year=2000, month=1, day=1).strftime('%d|%m|%Y|%H|%M|%S'),
                                          },
                                     follow=True,
                                    )
        result = list(XlrdReader(None, file_contents=response.content))

        self.assertEqual(3, len(result))
        self.assertEqual(["Ayanami", "Kirika", "", "Kawaii"], result[1])
        self.assertEqual(["Langley", "Kirika", "", ""],       result[2])

    #def test_get_related_fields(self):
        #url = '/reports/get_related_fields'
        #self.assertGET404(url)

        #get_ct = ContentType.objects.get_for_model

        #def post(model):
            #response = self.assertPOST200(url, data={'ct_id': get_ct(model).id})
            #return simplejson.loads(response.content)

        #self.assertEqual([], post(Organisation))
        #self.assertEqual([['document', _('Document')]],
                         #post(Folder)
                        #)

    def _find_choice(self, searched, choices):
        for i, (k, v) in enumerate(choices):
            if k == searched:
                return i
        else:
            self.fail('No "%s" choice' % searched)

    def _build_editfields_url(self, report):
        return '/reports/report/%s/field/add' % report.id

    def test_add_field01(self):
        report = self.create_simple_contacts_report('Report #1')
        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        rfield = report.columns.all()[0]

        with self.assertNoException():
            choices = response.context['form'].fields['regular_fields'].choices

        f_name = 'last_name'
        rf_index = self._find_choice(f_name, choices)
        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(1, len(columns))

        column = columns[0]
        self.assertEqual(f_name,          column.name)
        self.assertEqual(_(u'Last name'), column.title)
        self.assertEqual(1,               column.order)
        self.assertEqual(HFI_FIELD,       column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.report)
        self.assertEqual(rfield.id, column.id)
        self.assertEqual(rfield, column)

    def test_add_field02(self):
        "Custom field, aggregate on CustomField; additional old Field deleted"
        cf = self._create_cf_int()

        report = self.create_report('My beloved Report')
        old_rfields = list(report.columns.all())
        self.assertEqual(4, len(old_rfields))

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rf_choices = fields['regular_fields'].choices
            cf_choices = fields['custom_fields'].choices

            max_choices = fields['max'].choices
            min_choices = fields['min'].choices
            sum_choices = fields['sum'].choices
            avg_choices = fields['avg'].choices

        f_name = 'last_name'
        rf_index = self._find_choice(f_name, rf_choices)

        cf_id = str(cf.id)
        cf_index = self._find_choice(cf_id, cf_choices)

        aggr_id_base = 'cf__%s__%s' % (cf.field_type, cf_id)
        aggr_id = aggr_id_base + '__max'
        aggr_index = self._find_choice(aggr_id, max_choices)
        self._find_choice(aggr_id_base + '__min', min_choices)
        self._find_choice(aggr_id_base + '__sum', sum_choices)
        self._find_choice(aggr_id_base + '__avg', avg_choices)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,

                                               'custom_fields_check_%s' %  cf_index: 'on',
                                               'custom_fields_value_%s' %  cf_index: cf_id,
                                               'custom_fields_order_%s' %  cf_index: 1,

                                               'max_check_%s' %  aggr_index: 'on',
                                               'max_value_%s' %  aggr_index: aggr_id,
                                               'max_order_%s' %  aggr_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(3, len(columns))

        column = columns[0]
        self.assertEqual(f_name, column.name)
        self.assertEqual(old_rfields[0].id, column.id)

        column = columns[1]
        self.assertEqual(cf_id,      column.name)
        self.assertEqual(cf.name,    column.title)
        self.assertEqual(2,          column.order)
        self.assertEqual(HFI_CUSTOM, column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.report)
        self.assertEqual(old_rfields[1].id, column.id)

        column = columns[2]
        self.assertEqual(aggr_id,                             column.name)
        self.assertEqual('%s - %s' % (_('Maximum'), cf.name), column.title)
        self.assertEqual(3,                                   column.order)
        self.assertEqual(HFI_CALCULATED,                      column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.report)
        self.assertEqual(old_rfields[2].id, column.id)

        self.assertDoesNotExist(old_rfields[3])

    def test_add_field03(self):
        "Other types: relationships, function fields"
        report = self.create_report('My beloved Report')

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rf_choices = fields['regular_fields'].choices
            rt_choices = fields['relations'].choices
            ff_choices = fields['functions'].choices

        f_name = 'last_name'
        rf_index = self._find_choice(f_name, rf_choices)

        rtype_id = REL_SUB_EMPLOYED_BY
        rtype = self.get_object_or_fail(RelationType, pk=rtype_id)
        rt_index = self._find_choice(rtype_id, rt_choices)

        funfield = Contact.function_fields.get('get_pretty_properties')
        self.assertIsNotNone(funfield)
        ff_index = self._find_choice(funfield.name, ff_choices)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,

                                               'relations_check_%s' %  rt_index: 'on',
                                               'relations_value_%s' %  rt_index: rtype_id,
                                               'relations_order_%s' %  rt_index: 1,

                                               'functions_check_%s' %  ff_index: 'on',
                                               'functions_value_%s' %  ff_index: funfield.name,
                                               'functions_order_%s' %  ff_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(3, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(rtype_id,        column.name)
        self.assertEqual(rtype.predicate, column.title)
        self.assertEqual(2,               column.order)
        self.assertEqual(HFI_RELATION,    column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.report)

        column = columns[2]
        self.assertEqual(funfield.name,         column.name)
        self.assertEqual(funfield.verbose_name, column.title)
        self.assertEqual(3,                     column.order)
        self.assertEqual(HFI_FUNCTION,          column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.report)

    def test_add_field04(self):
        "Aggregate on regular fields"
        ct = ContentType.objects.get_for_model(Organisation)
        report = Report.objects.create(name='Secret report', ct=ct, user=self.user)

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rf_choices = fields['regular_fields'].choices
            max_choices = fields['max'].choices
            min_choices = fields['min'].choices

        f_name = 'name'
        rf_index = self._find_choice(f_name, rf_choices)

        vname = _('Capital')
        self.assertEqual([('capital__max', vname)], max_choices)
        aggr_id = 'capital__min'
        self.assertEqual([(aggr_id, vname)], min_choices)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,

                                               'min_check_%s' %  0: 'on',
                                               'min_value_%s' %  0: aggr_id,
                                               'min_order_%s' %  0: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(aggr_id,                           column.name)
        self.assertEqual('%s - %s' % (_('Minimum'), vname), column.title)
        self.assertEqual(2,                                 column.order)
        self.assertEqual(HFI_CALCULATED,                    column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.report)

    def test_add_field05(self):
        "Related entity"
        ct = ContentType.objects.get_for_model(Folder)
        report = Report.objects.create(name='Folder report', ct=ct, user=self.user)

        url = self._build_editfields_url(report)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            rf_choices = fields['regular_fields'].choices
            rel_choices = fields['related_fields'].choices

        f_name = 'title'
        rf_index = self._find_choice(f_name, rf_choices)

        rel_name = 'document'
        rel_index = self._find_choice(rel_name, rel_choices)

        response = self.client.post(url, data={'user': self.user.pk,
                                               'regular_fields_check_%s' % rf_index: 'on',
                                               'regular_fields_value_%s' % rf_index: f_name,
                                               'regular_fields_order_%s' % rf_index: 1,

                                               'related_fields_check_%s' %  rel_index: 'on',
                                               'related_fields_value_%s' %  rel_index: rel_name,
                                               'related_fields_order_%s' %  rel_index: 1,
                                              }
                                   )
        self.assertNoFormError(response)

        columns = list(report.columns.all())
        self.assertEqual(2, len(columns))

        self.assertEqual(f_name, columns[0].name)

        column = columns[1]
        self.assertEqual(rel_name,      column.name)
        self.assertEqual(_('Document'), column.title)
        self.assertEqual(2,             column.order)
        self.assertEqual(HFI_RELATED,   column.type)
        self.assertFalse(column.selected)
        self.assertIsNone(column.report)

    def _build_image_report(self):
        img_report = Report.objects.create(user=self.user, name="Report on images",
                                           ct=ContentType.objects.get_for_model(Image),
                                          )
        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        img_report.columns = [
            create_field(name="name",        title="Name",        order=1),
            create_field(name="description", title="Description", order=2),
          ]

        return img_report

    def _build_orga_report(self):
        orga_report = Report.objects.create(user=self.user, name="Report on organisations",
                                            ct=ContentType.objects.get_for_model(Organisation),
                                           )
        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        orga_report.columns = [
            create_field(name="name",              title="Name",               order=1),
            create_field(name="legal_form__title", title="Legal form - title", order=2),
          ]

        return orga_report

    def test_link_report01(self):
        contact_report = Report.objects.create(user=self.user, name="Report on contacts", 
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )

        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        contact_report.columns = rfields = [
            create_field(name="last_name",             title="Last name",      order=1),
            create_field(name="sector__title",         title="Sector - Title", order=2),
            create_field(name="image__name",           title="Image - Name",   order=3),
            create_field(name="get_pretty_properties", title="Properties",     order=4, type=HFI_FUNCTION),
          ]

        img_report = self._build_image_report()

        url_fmt = '/reports/report/%s/field/%s/link_report'
        self.assertGET404(url_fmt % (contact_report.id, rfields[3].id)) #not a HFI_FIELD Field
        self.assertGET404(url_fmt % (contact_report.id, rfields[0].id)) #not a FK field
        self.assertGET404(url_fmt % (contact_report.id, rfields[1].id)) #not a FK to a CremeEntity

        rfield = rfields[2]
        url = url_fmt % (contact_report.id, rfield.id)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': img_report.id}))

        rfield = self.refresh(rfield)
        self.assertEqual(img_report, rfield.report)

        #unlink --------------------------------------------------------------
        rfield.selected = True
        rfield.save()
        url = '/reports/report/field/unlink_report'
        self.assertGET404(url)
        self.assertPOST404(url, data={'field_id': rfields[0].id})
        self.assertPOST200(url, data={'field_id': rfield.id})

        rfield = self.refresh(rfield)
        self.assertIsNone(rfield.report)
        self.assertFalse(rfield.selected)

    def test_link_report02(self):
        get_ct = ContentType.objects.get_for_model
        contact_report = Report.objects.create(user=self.user, ct=get_ct(Contact),
                                               name="Report on contacts",
                                              )

        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        contact_report.columns = rfields = [
            create_field(name='last_name',         title="Last name",      order=1),
            create_field(name=REL_SUB_EMPLOYED_BY, title="Is employed by", order=2, type=HFI_RELATION),
          ]

        orga_ct = get_ct(Organisation)
        orga_report = self._build_orga_report()

        url_fmt = '/reports/report/%s/field/%s/link_relation_report/%s'
        self.assertGET404(url_fmt % (contact_report.id, rfields[0].id, orga_ct.id)) #not a HFI_RELATION Field
        self.assertGET404(url_fmt % (contact_report.id, rfields[1].id, get_ct(Image).id)) #ct not compatible

        url = url_fmt % (contact_report.id, rfields[1].id, orga_ct.id)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': orga_report.id}))
        self.assertEqual(orga_report, self.refresh(rfields[1]).report)

    def test_link_report03(self):
        self.assertEqual([('document', _(u'Document'))],
                         Report.get_related_fields_choices(Folder)
                        )
        get_ct = ContentType.objects.get_for_model
        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        create_report = partial(Report.objects.create, user=self.user, filter=None)

        folder_report = create_report(name="Report on folders", ct=get_ct(Folder))
        folder_report.columns = rfields = [
            create_field(name='title',    title='Title',    order=1),
            create_field(name='document', title='Document', order=2, type=HFI_RELATED),
          ]

        doc_report = create_report(name="Documents report", ct=get_ct(Document))
        doc_report.columns = [
            create_field(name='title',       title='Title',       order=1),
            create_field(name="description", title='Description', order=2),
          ]

        url_fmt = '/reports/report/%s/field/%s/link_related_report'
        self.assertGET404(url_fmt % (folder_report.id, rfields[0].id)) #not a HFI_RELATION Field

        url = url_fmt % (folder_report.id, rfields[1].id)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'report': doc_report.id}))
        self.assertEqual(doc_report, self.refresh(rfields[1]).report)

    def test_set_selected(self):
        img_report = self._build_image_report()
        orga_report = self._build_orga_report()

        contact_report = Report.objects.create(user=self.user, name="Report on contacts",
                                               ct=ContentType.objects.get_for_model(Contact),
                                              )
        create_field = partial(Field.objects.create, selected=False, report=None, type=HFI_FIELD)
        contact_report.columns = rfields = [
            create_field(name="last_name",         title="Last name",      order=1),
            create_field(name="image__name",       title="Image - Name",   order=2, report=img_report),
            create_field(name=REL_SUB_EMPLOYED_BY, title="Is employed by", order=3, 
                         report=orga_report, type=HFI_RELATION, selected=True,
                        ),
          ]

        url = '/reports/report/field/set_selected'
        self.assertGET404(url)

        data = {'report_id': contact_report.id, 
                'field_id':  rfields[0].id,
                'checked':   1,
               }
        self.assertPOST404(url, data=data)

        fk_rfield = rfields[1]
        rel_rfield = rfields[2]
        data['field_id'] = fk_rfield.id
        self.assertPOST200(url, data=data)
        self.assertTrue(self.refresh(fk_rfield).selected)
        self.assertFalse(self.refresh(rel_rfield).selected)

        self.assertPOST200(url, data=data)
        self.assertTrue(self.refresh(fk_rfield).selected)
        self.assertFalse(self.refresh(rel_rfield).selected)

        self.assertPOST200(url, data=dict(data, checked=0))
        self.assertFalse(self.refresh(fk_rfield).selected)
        self.assertFalse(self.refresh(rel_rfield).selected)

    def test_report_fetch01(self):
        create_contact = partial(Contact.objects.create, user=self.user)
        for i in xrange(5):
            create_contact(last_name='Mister %s' % i)

        create_contact(last_name='Mister X', is_deleted=True)

        report = self.create_simple_contacts_report("Contacts report")

        self.assertEqual(set(Contact.objects.filter(is_deleted=False)
                                            .values_list('last_name', flat=True)
                            ),
                         set(chain.from_iterable(report.fetch()))
                        )

    #def test_get_predicates_choices_4_ct(self):
        #response = self.assertPOST200('/reports/get_predicates_choices_4_ct',
                                      #data={'ct_id': ContentType.objects.get_for_model(Report).id}
                                     #)
        #self.assertEqual('text/javascript', response['Content-Type'])

        #content = simplejson.loads(response.content)
        #self.assertIsInstance(content, list)
        #self.assertTrue(content)

        #def relationtype_2_tuple(rtype_id):
            #rt = RelationType.objects.get(pk=rtype_id)
            #return [rt.id, rt.predicate]

        #self.assertIn(relationtype_2_tuple(REL_SUB_HAS), content)
        #self.assertNotIn(relationtype_2_tuple(REL_SUB_EMPLOYED_BY), content)

    def test_fetch01(self):
        self._create_reports()
        self._setUp_data_for_big_report()
        user = self.user

        targeted_organisations = [self.nintendo, self.sega, self.virgin, self.sony]
        targeted_contacts      = [self.crash, self.sonic, self.mario, self.luigi]

        #Target only own created organisations
        #Organisation.objects.exclude(id__in=[o.id for o in targeted_organisations]).delete()
        Contact.objects.exclude(id__in=[c.id for c in targeted_contacts]).delete()

        #Test opportunities report
        ##Headers
        self.assertEqual(set([u'name', u'reference', u'closing_date']),
                         set(f.name for f in self.report_opp.get_children_fields_flat())
                        )
        ##Data
        self.assertEqual([[u"Opportunity %s" % i, u"%s" % i, unicode(self.closing_date)] for i in xrange(1, 11)],
                         self.report_opp.fetch_all_lines(user=user)
                        )

        #Test invoices report
        ##Headers
        invoice_headers = ["name", "issuing_date", "status__name", "total_vat__sum"]
        self.assertEqual(invoice_headers, list(f.name for f in self.report_invoice.get_children_fields_flat()))

        nintendo_invoice_1 = [u"Invoice 1", unicode(self.issuing_date), unicode(self.invoice_status.name), Decimal("12.00")]
        nintendo_invoice_2 = [u"Invoice 2", unicode(self.issuing_date), unicode(self.invoice_status.name), Decimal("12.00")]
        self.assertEqual([nintendo_invoice_1, nintendo_invoice_2],
                         self.report_invoice.fetch_all_lines(user=user)
                        )

        #Test organisations report
        ##Headers
        ##REL_OBJ_BILL_ISSUED replaced by invoice_headers because of explosion of subreport
        orga_headers = list(chain([u"name", u"user__username", u"legal_form__title"],
                                  invoice_headers,
                                  [REL_OBJ_CUSTOMER_SUPPLIER, REL_SUB_EMIT_ORGA, u"capital__min", u'get_pretty_properties']
                                 )
                           )
        self.assertEqual(orga_headers, list(f.name for f in self.report_orga.get_children_fields_flat()))

        Relation.objects.create(subject_entity=self.nintendo,
                                type_id=REL_OBJ_CUSTOMER_SUPPLIER,
                                object_entity=self.sony,
                                user=user
                               )
        Relation.objects.create(subject_entity=self.nintendo,
                                type_id=REL_OBJ_CUSTOMER_SUPPLIER,
                                object_entity=self.sega,
                                user=user
                               )

        opportunity_nintendo_1 = self.create_opportunity(name="Opportunity nintendo 1", reference=u"1.1", emitter=self.nintendo)
        opp_nintendo_values = " - ".join(u"%s: %s" % (get_verbose_field_name(model=Opportunity, separator="-", field_name=field_name),
                                                      get_instance_field_info(opportunity_nintendo_1, field_name)[1]
                                                     )
                                           for field_name in [u'name', u'reference', u'closing_date']
                                        )
        min_capital = min(o.capital for o in targeted_organisations)

        ##Data
        nintendo = self.nintendo
        sega     = self.sega
        sony     = self.sony
        virgin   = self.virgin

        funf = Organisation.function_fields.get('get_pretty_properties')

        orga_data = OrderedDict([
            ("nintendo_invoice1", list(chain([nintendo.name, unicode(nintendo.user.username), self.nintendo_lf.title], nintendo_invoice_1,                [u", ".join([unicode(sony), unicode(sega)]), opp_nintendo_values, min_capital, funf(nintendo).for_csv()]))),
            ("nintendo_invoice2", list(chain([nintendo.name, unicode(nintendo.user.username), self.nintendo_lf.title], nintendo_invoice_2,                [u", ".join([unicode(sony), unicode(sega)]), opp_nintendo_values, min_capital, funf(nintendo).for_csv()]))),
            ("sega",              list(chain([sega.name,     unicode(sega.user.username),     self.sega_lf.title],     [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, funf(sega).for_csv()]))),
            ("sony",              list(chain([sony.name,     unicode(sony.user.username),     self.sony_lf.title],     [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, funf(sony).for_csv()]))),
            ("virgin",            list(chain([virgin.name,   unicode(virgin.user.username),   self.virgin_lf.title],   [u"" for i in nintendo_invoice_2], [u"",                                        u""],               [min_capital, funf(virgin).for_csv()]))),
        ])
        #self.assertEqual(orga_data.values(), self.report_orga.fetch_all_lines(user=user))
        self.assertListContainsSubset(orga_data.values(), self.report_orga.fetch_all_lines(user=user))

        #Test contacts report
        ##Headers
        self.assertEqual(list(chain(["last_name", "first_name", "language__name"], orga_headers)),
                         list(f.name for f in self.report_contact.get_children_fields_flat())
                        )

        #self.maxDiff = None

        ##Data
        crash = self.crash
        luigi = self.luigi
        mario = self.mario
        sonic = self.sonic

        self.assertEqual([list(chain([crash.last_name, crash.first_name, u""], orga_data['sony'])),
                          list(chain([luigi.last_name, luigi.first_name, u""], orga_data['nintendo_invoice1'])),
                          list(chain([luigi.last_name, luigi.first_name, u""], orga_data['nintendo_invoice2'])),
                          list(chain([mario.last_name, mario.first_name, u", ".join(mario.language.values_list("name", flat=True))], orga_data['nintendo_invoice1'])),
                          list(chain([mario.last_name, mario.first_name, u", ".join(mario.language.values_list("name", flat=True))], orga_data['nintendo_invoice2'])),
                          list(chain([sonic.last_name, sonic.first_name, u""], orga_data['sega'])),
                        ],
                       self.report_contact.fetch_all_lines()
                      )

        #TODO: test HFI_RELATED

    def test_fetch02(self):
        "Custom fields"
        create_contact = partial(Contact.objects.create, user=self.user)
        ned  = create_contact(first_name='Eddard', last_name='Stark')
        robb = create_contact(first_name='Robb',   last_name='Stark')
        aria = create_contact(first_name='Aria',   last_name='Stark')

        efilter = EntityFilter.create('test-filter', 'Starks', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=[ned.last_name]
                                                                   )
                               ])

        cf = self._create_cf_int()
        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned,  value=190)
        create_cfval(entity=aria, value=150)

        report = self.create_report('Contacts with CField', efilter=efilter)

        create_field = partial(Field.objects.create, selected=False, report=None)
        report.columns = [ #TODO: create Field builder like HFI...
            create_field(name='first_name', title='First Name', type=HFI_FIELD,  order=1),
            create_field(name=cf.id,        title=cf.name,      type=HFI_CUSTOM, order=2),
            create_field(name=1024,         title='Invalid',    type=HFI_CUSTOM, order=3), #simulates deleted CustomField
          ]

        self.assertEqual([[aria.first_name, '150', ''],
                          [ned.first_name,  '190', ''],
                          [robb.first_name, '',    ''],
                         ],
                         report.fetch_all_lines()
                        )

    #def test_fetch02_fix01(self): #todo: remove when datamigration is done
        #"Custom fields: get by name"
        #create_contact = partial(Contact.objects.create, user=self.user)
        #ned  = create_contact(first_name='Eddard', last_name='Stark')
        #robb = create_contact(first_name='Robb',   last_name='Stark')
        #aria = create_contact(first_name='Aria',   last_name='Stark')

        #efilter = EntityFilter.create('test-filter', 'Starks', Contact, is_custom=True)
        #efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    #operator=EntityFilterCondition.IEQUALS,
                                                                    #name='last_name', values=[ned.last_name]
                                                                   #)
                               #])

        #cf = self._create_cf_int()
        ##same name to be annoying
        #CustomField.objects.create(content_type=ContentType.objects.get_for_model(Organisation),
                                   #name=cf.name, field_type=CustomField.INT
                                  #)

        #create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        #create_cfval(entity=ned,  value=190)
        #create_cfval(entity=aria, value=150)

        #report = self.create_report('Contacts with CField', efilter=efilter)

        #create_field = partial(Field.objects.create, selected=False, report=None)
        #report.columns = [
            #create_field(name='first_name', title='First Name', type=HFI_FIELD,  order=1),
            #create_field(name=cf.name,      title=cf.name,      type=HFI_CUSTOM, order=2), #<====
          #]

        #self.assertEqual([[aria.first_name, '150'],
                          #[ned.first_name,  '190'],
                          #[robb.first_name, ''],
                         #],
                         #report.fetch_all_lines()
                        #)

    #def test_fetch02_fix02(self):  #todo: remove when DataMigration is done
        #"Custom fields: get by name, but name changed"
        #create_contact = partial(Contact.objects.create, user=self.user)
        #ned  = create_contact(first_name='Eddard', last_name='Stark')
        #robb = create_contact(first_name='Robb',   last_name='Stark')
        #aria = create_contact(first_name='Aria',   last_name='Stark')

        #efilter = EntityFilter.create('test-filter', 'Starks', Contact, is_custom=True)
        #efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    #operator=EntityFilterCondition.IEQUALS,
                                                                    #name='last_name', values=[ned.last_name]
                                                                   #)
                               #])

        #cf = self._create_cf_int()
        ##same name to be annoying
        #CustomField.objects.create(content_type=ContentType.objects.get_for_model(Organisation),
                                   #name=cf.name, field_type=CustomField.INT
                                  #)

        #create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        #create_cfval(entity=ned,  value=190)
        #create_cfval(entity=aria, value=150)

        #report = self.create_report('Contacts with CField', efilter=efilter)

        #create_field = partial(Field.objects.create, selected=False, report=None)
        #report.columns = [
            #create_field(name='first_name',    title='First Name', type=HFI_FIELD,  order=1),
            #create_field(name=cf.name + 'foo', title=cf.name,      type=HFI_CUSTOM, order=2), #<====
          #]

        #self.assertEqual([[aria.first_name, ''],
                          #[ned.first_name,  ''],
                          #[robb.first_name, ''],
                         #],
                         #report.fetch_all_lines()
                        #)

    #def test_get_aggregate_fields(self):
        #url = '/reports/get_aggregate_fields'
        #self.assertGET404(url)
        #self.assertPOST404(url)

        #data = {'ct_id': ContentType.objects.get_for_model(Organisation).id}
        #response = self.assertPOST200(url, data=data)
        #self.assertEqual([], simplejson.loads(response.content))

        #response = self.assertPOST200(url, data=dict(data, aggregate_name='stuff'))
        #self.assertEqual([], simplejson.loads(response.content))

        #response = self.assertPOST200(url, data=dict(data, aggregate_name='sum'))
        #self.assertEqual([['capital__sum', _('Capital')]],
                         #simplejson.loads(response.content)
                        #)

#TODO: test with subreports, expanding etc...
