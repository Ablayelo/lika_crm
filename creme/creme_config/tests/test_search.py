# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import SearchConfigItem
    from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
    from creme.creme_core.tests.fake_models import (FakeContact as Contact,
            FakeOrganisation as Organisation, FakeInvoice, FakeInvoiceLine)
    from creme.creme_core.utils import creme_entity_content_types
    from creme.creme_core.utils.unicode_collation import collator

    from ..blocks import SearchConfigBlock
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class SearchConfigTestCase(CremeTestCase):
    PORTAL_URL = '/creme_config/search/portal/'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()

        SearchConfigItem.objects.all().delete() # TODO: backup ?
        cls.populate('creme_core')

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(Contact)
        cls.ct_orga    = get_ct(Organisation)

    def setUp(self):
        self.login()

    def _build_add_url(self, ctype):
        return '/creme_config/search/add/%s' % ctype.id

    def _build_edit_url(self, sci):
        return '/creme_config/search/edit/%s' % sci.id

    def _get_first_entity_ctype(self):
        ctypes = list(creme_entity_content_types())
        ctypes.sort(key=lambda ct: collator.sort_key(unicode(ct)))

        return ctypes[0]

    def test_portal01(self):
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/search_portal.html')
        self.assertContains(response, ' id="%s"' % SearchConfigBlock.id_)

        self.assertContains(response, unicode(ctype))

        # Missing default configurations are built
        sci = self.get_object_or_fail(SearchConfigItem, content_type=ctype)
        self.assertIsNone(sci.user)
        self.assertTrue(sci.all_fields)

    def test_portal02(self):
        "Missing default configurations are built, even when configs for users exist"
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        SearchConfigItem.objects.create(content_type=ctype, user=self.user)

        self.assertGET200(self.PORTAL_URL)
        self.get_object_or_fail(SearchConfigItem, content_type=ctype, user=None)

    def test_add01(self):
        user = self.user
        ct = self.ct_contact
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ct, user=user))

        url = self._build_add_url(ct)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'user': user.id}))

        sc_items = SearchConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(sc_items))

        sc_item = sc_items[0]
        self.assertEqual(user, sc_item.user)
        self.assertFalse(sc_item.disabled)

    def test_add02(self):
        "Other CT, other user"
        ct = self.ct_orga
        other_user = self.other_user
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ct, user=other_user))

        self.assertNoFormError(self.client.post(self._build_add_url(ct),
                                                data={'user': other_user.id},
                                               )
                              )
        self.get_object_or_fail(SearchConfigItem, content_type=ct, user=other_user)

    def test_add03(self):
        "Unique configuration"
        user = self.user
        ct = self.ct_contact
        SearchConfigItem.objects.create(content_type=ct, user=user)

        response = self.assertGET200(self._build_add_url(ct))

        with self.assertNoException():
            user_f = response.context['form'].fields['user']
            choices = user_f.choices

        self.assertIsNone(user_f.empty_label)

        user_ids = {c[0] for c in choices}
        self.assertIn(self.other_user.id, user_ids)
        self.assertNotIn(user.id, user_ids)

    def _find_field_index(self, formfield, field_name):
        for i, (f_field_name, f_field_vname) in enumerate(formfield.choices):
            if f_field_name == field_name:
                return i

        self.fail('No "%s" in field' % field_name)

    def assertNoChoice(self, formfield, field_name):
        for i, (f_field_name, f_field_vname) in enumerate(formfield.choices):
            if f_field_name == field_name:
                self.fail(field_name + ' in choices')

    def _edit_config(self, url, sci, names_indexes, disabled=''):
        data = {'disabled': disabled}
        names = []

        for order, (name, index) in enumerate(names_indexes, start=1):
            data['fields_check_%s' % index] = 'on'
            data['fields_value_%s' % index] = name
            data['fields_order_%s' % index] = order

            names.append(name)

        response = self.client.post(url, data=data)
        self.assertNoFormError(response)

        sci = self.refresh(sci)
        self.assertEqual(names, [sf.name for sf in sci.searchfields])

        return sci

    def test_edit01(self):
        sci = SearchConfigItem.objects.create(content_type=self.ct_contact, user=None)
        url = self._build_edit_url(sci)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        fname1 = 'first_name'
        index1 = self._find_field_index(fields, fname1)

        fname2 = 'last_name'
        index2 = self._find_field_index(fields, fname2)

        self._find_field_index(fields, 'civility__title')
        self.assertNoChoice(fields, 'birthday')

        sci = self._edit_config(url, sci, ((fname1, index1), (fname2, index2)))
        self.assertFalse(sci.disabled)

    def test_edit02(self):
        "Other CT + user + exclude BooleanField"
        sci = SearchConfigItem.objects.create(content_type=self.ct_orga, user=self.user)
        url = self._build_edit_url(sci)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        fname1 = 'name'
        index1 = self._find_field_index(fields, fname1)

        fname2 = 'description'
        index2 = self._find_field_index(fields, fname2)

        self.assertNoChoice(fields, 'subject_to_vat')

        self._edit_config(url, sci, ((fname1, index1), (fname2, index2)))

    def test_edit03(self):
        "Disabled"
        sci = SearchConfigItem.objects.create(content_type=self.ct_contact, user=None)
        url = self._build_edit_url(sci)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        fname1 = 'first_name'
        index1 = self._find_field_index(fields, fname1)
        sci = self._edit_config(url, sci, [(fname1, index1)], disabled='on')
        self.assertTrue(sci.disabled)

    def test_edit04(self):
        "Fields with 'choices' are not valid"
        fname = 'discount_unit'
        mfield = FakeInvoiceLine._meta.get_field(fname)
        self.assertTrue(mfield.choices)

        sci = SearchConfigItem.objects.create(content_type=ContentType.objects.get_for_model(FakeInvoiceLine))
        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        self._find_field_index(fields, 'item')
        self.assertNoChoice(fields, fname)

    def test_edit05(self):
        "Exclude DateperiodField"
        sci = SearchConfigItem.objects.create(content_type=ContentType.objects.get_for_model(FakeInvoice))
        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        self._find_field_index(fields, 'name')
        self.assertNoChoice(fields, 'periodicity')

    def test_delete01(self):
        sci = SearchConfigItem.create_if_needed(Contact, user=self.user,
                                                fields=['first_name', 'last_name'],
                                               )
        self.assertPOST200('/creme_config/search/delete', data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete02(self):
        "Cannot delete the default configuration"
        sci = SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])
        self.assertPOST409('/creme_config/search/delete', data={'id': sci.id})
        self.assertStillExists(sci)
