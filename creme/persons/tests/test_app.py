# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse

    from creme.creme_core.models import HeaderFilter, EntityFilter
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.views.base import BrickTestCaseMixin

    from .. import constants, bricks
    from .base import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class PersonsAppTestCase(CremeTestCase, BrickTestCaseMixin):
    def test_populate(self):
        self.get_relationtype_or_fail(constants.REL_SUB_EMPLOYED_BY,       [Contact],               [Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_CUSTOMER_SUPPLIER, [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_MANAGES,           [Contact],               [Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_PROSPECT,          [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_SUSPECT,           [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_PARTNER,           [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_INACTIVE,          [Contact, Organisation], [Contact, Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_SUBSIDIARY,        [Organisation],          [Organisation])
        self.get_relationtype_or_fail(constants.REL_SUB_COMPETITOR,        [Contact, Organisation], [Contact, Organisation])

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        self.assertTrue(hf_filter(entity_type=get_ct(Contact)).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(Organisation)).exists())

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.FILTER_MANAGED_ORGA)
        self.assertFalse(efilter.is_custom)
        self.assertEqual(Organisation, efilter.entity_type.model_class())
        self.assertQuerysetSQLEqual(Organisation.objects.filter(is_managed=True),
                                    efilter.filter(Organisation.objects.all())
                                   )

    def test_portal(self):
        self.login()
        self.assertGET200(reverse('persons__portal'))

    def test_config_portal(self):
        self.login()
        response = self.assertGET200(reverse('creme_config__portal'))
        self.get_brick_node(self.get_html_tree(response.content), bricks.ManagedOrganisationsBrick.id_)
