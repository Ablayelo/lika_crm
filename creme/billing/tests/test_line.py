# -*- coding: utf-8 -*-

try:
    #from datetime import date
    from decimal import Decimal
    from functools import partial
    from json import dumps as json_dump

    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _
    #from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    #from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellFunctionField
    from creme.creme_core.models import Relation, SetCredentials, Vat # HeaderFilter

    from creme.persons.models import Contact, Organisation
    from creme.persons.tests.base import skipIfCustomOrganisation

    from creme.products.models import Product, Service # Category, SubCategory
    from creme.products.tests.base import skipIfCustomProduct, skipIfCustomService

    from ..constants import *
    # from ..models import *
    from .base import (_BillingTestCase, skipIfCustomInvoice,
            skipIfCustomProductLine, skipIfCustomServiceLine,
            Invoice, ProductLine, ServiceLine)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomOrganisation
@skipIfCustomInvoice
class LineTestCase(_BillingTestCase):
    clean_files_in_teardown = False

    @classmethod
    def setUpClass(cls):
        _BillingTestCase.setUpClass()
        ##cls.populate('creme_core', 'creme_config', 'products', 'billing')
        #cls.populate('creme_config', 'products', 'billing')
        cls.populate('products', 'billing')

    @skipIfCustomProduct
    def test_add_product_lines01(self):
        "Multiple adding"
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
#        url = '/billing/%s/product_line/add_multiple' % invoice.id
        url = reverse('billing__create_product_lines', args=(invoice.id,))
        self.assertGET200(url)
        self.assertFalse(invoice.service_lines)

        product1 = self.create_product()
        product2 = self.create_product()
        vat = Vat.objects.get_or_create(value=Decimal('5.5'))[0]
        quantity = 2
        response = self.client.post(url, data={'items': '[%d,%d]' % (product1.id, product2.id),
                                               'quantity':       quantity,
                                               'discount_value': Decimal('20'),
                                               'vat':            vat.id,
                                              }
                                   )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice) #refresh lines cache
        self.assertEqual(2, len(invoice.product_lines))

        line0, line1 = invoice.product_lines
        self.assertEqual(quantity,        line0.quantity)
        self.assertEqual(quantity,        line1.quantity)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line0)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line1)
        self.assertRelationCount(1, line0,   REL_SUB_LINE_RELATED_ITEM, product1)
        self.assertRelationCount(1, line1,   REL_SUB_LINE_RELATED_ITEM, product2)

        self.assertEqual(Decimal('3.2'), invoice.total_no_vat) # 2 * 0.8 + 2 * 0.8
        self.assertEqual(Decimal('3.38'), invoice.total_vat) # 3.2 * 1.07 = 3.38

        self.assertEqual(invoice.get_absolute_url(), line0.get_absolute_url())

    @skipIfCustomProduct
    def test_lines_with_negatives_values(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        quote = self.create_quote_n_orgas('Quote001')[0]
        unit_price = Decimal('-50.0')
        product_name = 'on the fly product'
        create_pline = partial(ProductLine.objects.create, user=user, on_the_fly_item=product_name,
                               unit_price=unit_price, unit=''
                               )
        create_pline(related_document=quote)
        create_pline(related_document=invoice)
        self.assertEqual(Decimal('-50.0'), invoice.total_vat)
        self.assertEqual(Decimal('0'), quote.total_vat)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_listviews(self):
        self.login()

        invoice1 = self.create_invoice_n_orgas('Invoice001')[0]
        invoice2 = self.create_invoice_n_orgas('Invoice002')[0]

        create_pline = partial(ProductLine.objects.create, user=self.user)
        pline1 = create_pline(related_document=invoice1, on_the_fly_item='FlyP1')
        pline2 = create_pline(related_document=invoice2, on_the_fly_item='FlyP2')

        create_sline = partial(ServiceLine.objects.create, user=self.user)
        sline1 = create_sline(related_document=invoice1, on_the_fly_item='FlyS1')
        sline2 = create_sline(related_document=invoice2, on_the_fly_item='FlyS2')

        #---------------------------------------------------------------------
#        response = self.assertGET200('/billing/lines')
#
#        with self.assertNoException():
#            lines_page = response.context['entities']
#
#        self.assertEqual(4, lines_page.paginator.count)
#
#        real_lines = [l.get_real_entity() for l in lines_page.object_list]
#        self.assertIn(pline1, real_lines)
#        self.assertIn(sline2, real_lines)

        #---------------------------------------------------------------------
#        response = self.assertGET200('/billing/product_lines')
        response = self.assertGET200(reverse('billing__list_product_lines'))

        with self.assertNoException():
            plines_page = response.context['entities']

        self.assertEqual(2, plines_page.paginator.count)

        self.assertIn(pline1, plines_page.object_list)
        self.assertIn(pline2, plines_page.object_list)

        #---------------------------------------------------------------------
#        response = self.assertGET200('/billing/service_lines')
        response = self.assertGET200(reverse('billing__list_service_lines'))

        with self.assertNoException():
            slines_page = response.context['entities']

        self.assertEqual(2, slines_page.paginator.count)

        self.assertIn(sline1, slines_page.object_list)
        self.assertIn(sline2, slines_page.object_list)

    @skipIfCustomProductLine
    def test_delete_product_line01(self):
        self.login()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=self.user, related_document=invoice,
                                                  on_the_fly_item='Flyyyyy'
                                                 )
        self.assertPOST404('/creme_core/entity/delete_related/%s' % product_line.entity_type_id,
                           data={'id': product_line.id},
                          )
        self.assertPOST200('/creme_core/entity/delete/%s' % product_line.id, data={}, follow=True)
        self.assertFalse(self.refresh(invoice).product_lines)
        self.assertFalse(ProductLine.objects.exists())

    @skipIfCustomService
    def test_add_service_lines01(self):
        "Multiple adding"
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
#        url = '/billing/%s/service_line/add_multiple' % invoice.id
        url = reverse('billing__create_service_lines', args=(invoice.id,))
        self.assertGET200(url)
        self.assertFalse(invoice.service_lines)

        service1 = self.create_service()
        service2 = self.create_service()
        vat = Vat.objects.get_or_create(value=Decimal('19.6'))[0]
        quantity = 2
        response = self.client.post(url, data={'items': '[%d,%d]' % (service1.id, service2.id),
                                               'quantity':       quantity,
                                               'discount_value': Decimal('10'),
                                               'vat':            vat.id,
                                              }
                                   )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice) #refresh lines cache
        self.assertEqual(2, len(invoice.service_lines))

        lines = invoice.service_lines
        line0 = lines[0]
        line1 = lines[1]
        self.assertEqual(quantity, line0.quantity)
        self.assertEqual(quantity, line1.quantity)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line0)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line1)
        self.assertRelationCount(1, line0,   REL_SUB_LINE_RELATED_ITEM, service1)
        self.assertRelationCount(1, line1,   REL_SUB_LINE_RELATED_ITEM, service2)

        self.assertEqual(Decimal('21.6'), invoice.total_no_vat) # 2 * 5.4 + 2 * 5.4
        self.assertEqual(Decimal('25.84'), invoice.total_vat) # 21.6 * 1.196 = 25.84

    @skipIfCustomProductLine
    def test_related_document01(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='Flyyyyy',
                                                 )
        self.assertEqual(invoice, product_line.related_document)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, product_line)

    @skipIfCustomProduct
    @skipIfCustomProductLine
    def test_related_item01(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        product = self.create_product()

        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  related_item=product,
                                                 )
        self.assertEqual(product, product_line.related_item)
        self.assertRelationCount(1, product_line, REL_SUB_LINE_RELATED_ITEM, product)

    @skipIfCustomProductLine
    def test_related_item02(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='Flyyyyy',
                                                 )
        self.assertIsNone(product_line.related_item)

    @skipIfCustomProduct
    @skipIfCustomProductLine
    def test_product_line_clone(self):
        user = self.login()

        product = self.create_product()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        invoice2 = self.create_invoice_n_orgas('Invoice002')[0]

        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  related_item=product,
                                                 )
        product_line2 = product_line.clone(invoice2)

        product_line2 = self.refresh(product_line2)
        self.assertEqual(invoice2, product_line2.related_document)
        self.assertEqual(product, product_line2.related_item)

        rel_filter = Relation.objects.filter
        self.assertEqual([product_line2.pk],
                         list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice2)
                                        .values_list('object_entity', flat=True)
                             )
                        )
        self.assertEqual({product_line.pk, product_line2.pk},
                         set(rel_filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=product)
                                       .values_list('subject_entity', flat=True)
                            )
                        )

    @skipIfCustomServiceLine
    def test_service_line_clone(self):
        user = self.login()

        service = self.create_service()
        invoice1 = self.create_invoice_n_orgas('Invoice001')[0]
        invoice2 = self.create_invoice_n_orgas('Invoice002')[0]

        service_line1 = ServiceLine.objects.create(user=user, related_document=invoice1,
                                                   related_item=service,
                                                  )

        service_line2 = service_line1.clone(invoice2)
        service_line2 = self.refresh(service_line2)
        self.assertEqual(invoice2, service_line2.related_document)
        self.assertEqual(service, service_line2.related_item)
        self.assertNotEqual(service_line1, service_line2)

        rel_filter = Relation.objects.filter
        self.assertEqual([service_line1.pk], list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice1).values_list('object_entity', flat=True)))
        self.assertEqual([service_line2.pk], list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice2).values_list('object_entity', flat=True)))
        self.assertEqual({service_line1.pk, service_line2.pk},
                         set(rel_filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=service)
                                       .values_list('subject_entity', flat=True)
                            )
                        )

#    def test_get_verbose_type(self):
#        self.login()
#
#        invoice = self.create_invoice_n_orgas('Invoice001')[0]
#        kwargs = {'user': self.user, 'related_document': invoice}
#        pl = ProductLine.objects.create(on_the_fly_item="otf1", unit_price=Decimal("1"), **kwargs)
#        verbose_type = _(u"Product")
#        self.assertEqual(verbose_type, unicode(pl.get_verbose_type()))
#
#        funf = pl.function_fields.get('get_verbose_type')
#        self.assertIsNotNone(funf)
#        self.assertEqual(verbose_type, funf(pl).for_html())
#
#        sl = ServiceLine.objects.create(on_the_fly_item="otf2", unit_price=Decimal("4"), **kwargs)
#        verbose_type = _(u"Service")
#        self.assertEqual(verbose_type, unicode(sl.get_verbose_type()))
#        self.assertEqual(verbose_type, sl.function_fields.get('get_verbose_type')(sl).for_html())

    @skipIfCustomProductLine
    def test_multiple_delete01(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user, related_document=invoice)
        ids = tuple(create_line(on_the_fly_item='Fly ' + price,
                                unit_price=Decimal(price)
                               ).id for price in ('10', '20')
                   )

        invoice.save() # updates totals

        self.assertEqual(2, len(invoice.product_lines))
        expected_total = Decimal('30')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

        self.assertPOST200('/creme_core/entity/delete/multi', follow=True,
                           data={'ids': '%s,%s' % ids}
                          )
        self.assertFalse(ProductLine.objects.filter(pk__in=ids))

        invoice = self.refresh(invoice)
        self.assertFalse(invoice.product_lines)

        expected_total = Decimal('0')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    @skipIfCustomProductLine
    def test_multiple_delete02(self):
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Organisation]
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.DELETE | \
                                            EntityCredentials.LINK | EntityCredentials.UNLINK, #not EntityCredentials.CHANGE |
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]
        self.assertFalse(user.has_perm_to_change(invoice))

        create_line = partial(ProductLine.objects.create, user=user,
                              related_document=invoice
                             )
        ids = tuple(create_line(on_the_fly_item='Fly ' + price,
                                unit_price=Decimal(price)
                               ).id for price in ('10', '20')
                   )

        self.assertPOST403('/creme_core/entity/delete/multi', follow=True,
                           data={'ids': '%s,%s' % ids}
                          )
        self.assertEqual(2, ProductLine.objects.filter(pk__in=ids).count())

    def test_delete_vat01(self):
        self.login()

        vat = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=True)
        self.assertPOST200('/creme_config/creme_core/vat_value/delete', data={'id': vat.pk})
        self.assertDoesNotExist(vat)

    @skipIfCustomProductLine
    def test_delete_vat02(self):
        user = self.login()

        vat = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=True)
        invoice = self.create_invoice_n_orgas('Nerv')[0]
        line = ProductLine.objects.create(user=user, related_document=invoice,
                                          on_the_fly_item='Flyyyyy', vat_value=vat,
                                         )

        self.assertPOST404('/creme_config/creme_core/vat_value/delete', data={'id': vat.pk})
        self.assertStillExists(vat)

        self.get_object_or_fail(Invoice, pk=invoice.pk)

        line = self.get_object_or_fail(ProductLine, pk=line.pk)
        self.assertEqual(vat, line.vat_value)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_csv_import(self):
        self.login()
#        self.assertGET404(self._build_import_url(Line))
        self.assertGET404(self._build_import_url(ServiceLine))
        self.assertGET404(self._build_import_url(ProductLine))

    def _build_add2catalog_url(self, line):
        return '/billing/line/%s/add_to_catalog' % line.id

    def _build_dict_cat_subcat(self, cat, subcat):
        return {'sub_category': '{"category": %s, "subcategory": %s}' % (cat.id, subcat.id)}

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item01(self):
        "convert on the fly product"
        user = self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        unit_price = Decimal('50.0')
        product_name = 'on the fly product'
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=product_name,
                                                  unit_price=unit_price, unit='',
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        self.assertGET200(self._build_add2catalog_url(product_line))
        response = self.client.post(self._build_add2catalog_url(product_line),
                                      data=self._build_dict_cat_subcat(cat, subcat))

        self.assertNoFormError(response)
        self.assertTrue(Product.objects.exists())

        self.get_object_or_fail(Product, name=product_name, unit_price=unit_price, user=user)

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item02(self):
        "convert on the fly service"
        user = self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        unit_price = Decimal('50.0')
        service_name = 'on the fly service'
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=service_name,
                                                  unit_price=unit_price, unit='',
                                                 )
        cat, subcat = self.create_cat_n_subcat()

        response = self.client.post(self._build_add2catalog_url(service_line),
                                      data=self._build_dict_cat_subcat(cat, subcat))

        self.assertNoFormError(response)
        self.assertTrue(Service.objects.exists())

        self.get_object_or_fail(Service, name=service_name, unit_price=unit_price, user=user)

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item03(self):
        "On-the-fly + product creation + no creation creds"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Contact, Organisation], #not 'Product'
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.LINK |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        self.assertPOST403(self._build_add2catalog_url(product_line),
                           data=self._build_dict_cat_subcat(cat, subcat))

        self.assertFalse(Product.objects.exists())

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item04(self):
        "On-the-fly + service creation + no creation creds"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Contact, Organisation], #not 'Service'
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.LINK |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        self.assertPOST403(self._build_add2catalog_url(service_line),
                           data=self._build_dict_cat_subcat(cat, subcat))

        self.assertFalse(Service.objects.exists())

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item05(self):
        "already related item product line"
        user = self.login()

        product = self.create_product()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  related_item=product,
                                                  unit_price=Decimal('50.0')
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        response = self.assertPOST200(self._build_add2catalog_url(product_line),
                                      data=self._build_dict_cat_subcat(cat, subcat))

        self.assertFormError(response, 'form', None,
                             _(u'You are not allowed to add this item to the catalog because it is not on the fly')
                            )
        self.assertEqual(1, Product.objects.count())

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item06(self):
        "already related item service line"
        user = self.login()

        service = self.create_service()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  related_item=service,
                                                  unit_price=Decimal('50.0')
                                                 )
        cat, subcat = self.create_cat_n_subcat()
        response = self.assertPOST200(self._build_add2catalog_url(service_line),
                                      data=self._build_dict_cat_subcat(cat, subcat))

        self.assertFormError(response, 'form', None,
                             _(u'You are not allowed to add this item to the catalog because it is not on the fly')
                            )
        self.assertEqual(1, Service.objects.count())

    @skipIfCustomServiceLine
    def test_multi_save_lines01(self):
        "1 service line updated"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=u'on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )

        name = 'on the fly service updated'
        unit_price = '100.0'
        quantity = '2'
        unit = 'day'
        discount = '20'
        discount_unit = DISCOUNT_PERCENT
        response = self.client.post('/billing/%s/multi_save_lines' % invoice.id,
                                    #TODO: json.dumps
                                    data={service_line.entity_type_id: json_dump({
                                                        'service_line_formset-TOTAL_FORMS':        len(invoice.service_lines),
                                                        'service_line_formset-INITIAL_FORMS':      1,
                                                        'service_line_formset-MAX_NUM_FORMS':      u'',
                                                        #'service_line_formset-0-line_ptr':         service_line.id,
                                                        'service_line_formset-0-cremeentity_ptr':  service_line.id,
                                                        'service_line_formset-0-user':             user.id,
                                                        'service_line_formset-0-on_the_fly_item':  name,
                                                        'service_line_formset-0-unit_price':       unit_price,
                                                        'service_line_formset-0-quantity':         quantity,
                                                        'service_line_formset-0-discount':         discount,
                                                        'service_line_formset-0-discount_unit':    discount_unit,
                                                        'service_line_formset-0-vat_value':        Vat.objects.all()[1].id,
                                                        'service_line_formset-0-unit':             unit,
                                                    })
                                           }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        service_line = self.refresh(service_line)
        self.assertEqual(name,                service_line.on_the_fly_item)
        self.assertEqual(Decimal(unit_price), service_line.unit_price)
        self.assertEqual(Decimal(quantity),   service_line.quantity)
        self.assertEqual(unit,                service_line.unit)
        self.assertEqual(Decimal(discount),   service_line.discount)
        self.assertEqual(discount_unit,       service_line.discount_unit)
        self.assertIs(service_line.total_discount, False)

    @skipIfCustomProductLine
    def test_multi_save_lines02(self):
        "1 product line created on the fly and 1 deleted"
        user = self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=u'on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )
        name = 'new on the fly product'
        unit_price = '69.0'
        quantity = '2'
        unit = 'month'
        response = self.client.post('/billing/%s/multi_save_lines' % invoice.id,
                                    data={product_line.entity_type_id: json_dump({
                                                        'product_line_formset-TOTAL_FORMS':        len(invoice.product_lines) + 1,
                                                        'product_line_formset-INITIAL_FORMS':      1,
                                                        'product_line_formset-MAX_NUM_FORMS':      u'',
                                                        'product_line_formset-0-DELETE':           True,
                                                        #'product_line_formset-0-line_ptr':         product_line.id,
                                                        'product_line_formset-0-cremeentity_ptr':  product_line.id,
                                                        'product_line_formset-0-user':             user.id,
                                                        'product_line_formset-0-on_the_fly_item':  "whatever",
                                                        'product_line_formset-0-unit_price':       "whatever",
                                                        'product_line_formset-0-quantity':         "whatever",
                                                        'product_line_formset-0-discount':         "whatever",
                                                        'product_line_formset-0-discount_unit':    "whatever",
                                                        'product_line_formset-0-vat_value':        "whatever",
                                                        'product_line_formset-0-unit':             "whatever",
                                                        'product_line_formset-1-user':             self.user.id,
                                                        'product_line_formset-1-on_the_fly_item':  name,
                                                        'product_line_formset-1-unit_price':       unit_price,
                                                        'product_line_formset-1-quantity':         quantity,
                                                        'product_line_formset-1-discount':         "50.00",
                                                        'product_line_formset-1-discount_unit':    "1",
                                                        'product_line_formset-1-vat_value':        Vat.objects.all()[0].id,
                                                        'product_line_formset-1-unit':             unit,
                                                    })
                                         }
                                   )
        self.assertNoFormError(response)
        product_lines = ProductLine.objects.all()
        self.assertEqual(1, len(product_lines))

        product_line = product_lines[0]
        self.assertEqual(name,                product_line.on_the_fly_item)
        self.assertEqual(Decimal(unit_price), product_line.unit_price)
        self.assertEqual(Decimal(quantity),   product_line.quantity)
        self.assertEqual(unit,                product_line.unit)

    @skipIfCustomServiceLine
    def test_multi_save_lines03(self):
        "No creds"
        user = self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                          creatable_models=[Invoice, Contact, Organisation],
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.DELETE | EntityCredentials.LINK |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=u'on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )

        self.assertPOST403('/billing/%s/multi_save_lines' % invoice.id,
                           data={service_line.entity_type_id: json_dump({
                                                'service_line_formset-TOTAL_FORMS':        len(invoice.service_lines),
                                                'service_line_formset-INITIAL_FORMS':      1,
                                                'service_line_formset-MAX_NUM_FORMS':      u'',
                                                #'service_line_formset-0-line_ptr':         service_line.id,
                                                'service_line_formset-0-cremeentity_ptr':  service_line.id,
                                                'service_line_formset-0-user':             user.id,
                                                'service_line_formset-0-on_the_fly_item':  'on the fly service updated',
                                                'service_line_formset-0-unit_price':       '100.0',
                                                'service_line_formset-0-quantity':         '2',
                                                'service_line_formset-0-discount':         '20',
                                                'service_line_formset-0-discount_unit':    '1',
                                                'service_line_formset-0-vat_value':        Vat.objects.all()[0].id,
                                                'service_line_formset-0-unit':             'day',
                                            })
                                }
                           )

    @skipIfCustomServiceLine
    def test_multi_save_lines04(self):
        "Other type of discount: amount per line"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=u'on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )

        discount_unit = DISCOUNT_LINE_AMOUNT
        response = self.client.post('/billing/%s/multi_save_lines' % invoice.id,
                                    data={service_line.entity_type_id: json_dump({
                                                        'service_line_formset-TOTAL_FORMS':        len(invoice.service_lines),
                                                        'service_line_formset-INITIAL_FORMS':      1,
                                                        'service_line_formset-MAX_NUM_FORMS':      u'',
                                                        #'service_line_formset-0-line_ptr':         service_line.id,
                                                        'service_line_formset-0-cremeentity_ptr':  service_line.id,
                                                        'service_line_formset-0-user':             user.id,
                                                        'service_line_formset-0-on_the_fly_item':  'on the fly service updated',
                                                        'service_line_formset-0-unit_price':       '100.0',
                                                        'service_line_formset-0-quantity':         '2',
                                                        'service_line_formset-0-discount':         '20',
                                                        'service_line_formset-0-discount_unit':    discount_unit,
                                                        'service_line_formset-0-vat_value':        Vat.objects.all()[1].id,
                                                        'service_line_formset-0-unit':             'day',
                                                    })
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        service_line = self.refresh(service_line)
        self.assertEqual(discount_unit, service_line.discount_unit)
        self.assertIs(service_line.total_discount, True)

    @skipIfCustomServiceLine
    def test_multi_save_lines05(self):
        "Other type of discount: amount per item"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item=u'on the fly service',
                                                  unit_price=Decimal('50.0')
                                                 )

        response = self.client.post('/billing/%s/multi_save_lines' % invoice.id,
                                    data={service_line.entity_type_id: json_dump({
                                                        'service_line_formset-TOTAL_FORMS':        len(invoice.service_lines),
                                                        'service_line_formset-INITIAL_FORMS':      1,
                                                        'service_line_formset-MAX_NUM_FORMS':      u'',
                                                        #'service_line_formset-0-line_ptr':         service_line.id,
                                                        'service_line_formset-0-cremeentity_ptr':  service_line.id,
                                                        'service_line_formset-0-user':             user.id,
                                                        'service_line_formset-0-on_the_fly_item':  'on the fly service updated',
                                                        'service_line_formset-0-unit_price':       '100.0',
                                                        'service_line_formset-0-quantity':         '2',
                                                        'service_line_formset-0-discount':         '20',
                                                        'service_line_formset-0-discount_unit':    DISCOUNT_ITEM_AMOUNT,
                                                        'service_line_formset-0-vat_value':        Vat.objects.all()[1].id,
                                                        'service_line_formset-0-unit':             'day',
                                                    })
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        service_line = self.refresh(service_line)
        self.assertEqual(DISCOUNT_LINE_AMOUNT, service_line.discount_unit)
        self.assertIs(service_line.total_discount, False)

    @skipIfCustomProductLine
    def test_global_discount_change(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]

        ProductLine.objects.create(user=user, unit_price=Decimal("10"),
                                   vat_value=Vat.get_default_vat(),
                                   related_document=invoice, on_the_fly_item='Flyyyyy',
                                  )

        discount_zero = Decimal('0.0')
        full_discount = Decimal('100.0')

        self.assertEqual(invoice.discount, discount_zero)

        invoice.discount = full_discount
        invoice.save()

        invoice = self.refresh(invoice)

        self.assertEqual(invoice.discount, full_discount)
        self.assertEqual(invoice.total_no_vat, discount_zero)
        self.assertEqual(invoice.total_vat, discount_zero)

    @skipIfCustomProductLine
    def test_inneredit(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]
        pline = ProductLine.objects.create(user=user, unit_price=Decimal("10"),
                                           vat_value=Vat.get_default_vat(),
                                           related_document=invoice,
                                           on_the_fly_item='Flyyyyy',
                                           comment='I believe',
                                          )

        build_url = self.build_inneredit_url
        url = build_url(pline, 'comment')
        self.assertGET200(url)

        comment = pline.comment + ' I can flyyy'
        response = self.client.post(url, data={'entities_lbl': [unicode(pline)],
                                               'field_value':  comment,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(comment, self.refresh(pline).comment)

        self.assertGET(400, build_url(pline, 'on_the_fly_item'))
        self.assertGET(400, build_url(pline, 'total_discount'))
        self.assertGET(400, build_url(pline, 'discount_unit'))

#    def test_search_functionfield(self):
#        "LineTypeField"
#        user = self.login()
#        invoice = Invoice.objects.create(user=user, name='Invoice',
#                                         expiration_date=date(year=2012, month=12, day=15),
#                                         status=InvoiceStatus.objects.all()[0],
#                                        )
#
#        create_pline = partial(ProductLine.objects.create, user=user, related_document=invoice)
#        pline1 = create_pline(on_the_fly_item='Fly1')
#        pline2 = create_pline(on_the_fly_item='Fly2')
#
#        create_sline = partial(ServiceLine.objects.create, user=user, related_document=invoice)
#        sline1 = create_sline(on_the_fly_item='Fly3')
#        sline2 = create_sline(on_the_fly_item='Fly4')
#
#        func_field = Line.function_fields.get('get_verbose_type')
#
#        HeaderFilter.create(pk='test-hf_orga', name='Orga view', model=Organisation,
#                            cells_desc=[EntityCellRegularField.build(model=Organisation, name='name'),
#                                        EntityCellFunctionField(func_field),
#                                       ],
#                           )
#
#        def _get_entities_set(response):
#            with self.assertNoException():
#                entities_page = response.context['entities']
#
#            return set(entities_page.object_list)
#
#        url = Line.get_lv_absolute_url()
#        response = self.assertGET200(url)
#        ids = {l.id for l in _get_entities_set(response)}
#        self.assertIn(pline1.id, ids)
#        self.assertIn(pline2.id, ids)
#        self.assertIn(sline1.id, ids)
#        self.assertIn(sline2.id, ids)
#
#        def post(line_type):
#            return self.assertPOST200(url, data={'_search': 1,
#                                                 'regular_field-name': '',
#                                                 'function_field-%s' % func_field.name: line_type,
#                                                }
#                                     )
#
#        response = post(PRODUCT_LINE_TYPE)
#        ids = {l.id for l in _get_entities_set(response)}
#        self.assertIn(pline1.id,    ids)
#        self.assertIn(pline2.id,    ids)
#        self.assertNotIn(sline1.id, ids)
#        self.assertNotIn(sline2.id, ids)
#
#        response = post(SERVICE_LINE_TYPE)
#        ids = {l.id for l in _get_entities_set(response)}
#        self.assertNotIn(pline1.id, ids)
#        self.assertNotIn(pline2.id, ids)
#        self.assertIn(sline1.id,    ids)
#        self.assertIn(sline2.id,    ids)
