# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _ ###################################
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import * #########################
from creme_core.tests.base import CremeTestCase

from activities.models import Meeting

from persons.models import Contact, Organisation #need CremeEntity

from creme_config.models import * #################################


__all__ = ('UserRoleTestCase',)


class UserRoleTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/role/portal/').status_code)

    def test_create01(self):
        response = self.client.get('/creme_config/role/add/')
        self.assertEqual(200,  response.status_code)

        get_ct = ContentType.objects.get_for_model
        name = 'CEO'
        creatable_ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        exportable_ctypes = [get_ct(Contact).id, get_ct(Meeting).id]
        apps = ['persons']
        response = self.client.post('/creme_config/role/add/', follow=True,
                                    data={
                                            'name':                 name,
                                            'creatable_ctypes':     creatable_ctypes,
                                            'exportable_ctypes':    exportable_ctypes,
                                            'allowed_apps':         apps,
                                            'admin_4_apps':         apps,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            role = UserRole.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(set(creatable_ctypes),  set(ctype.id for ctype in role.creatable_ctypes.all()))
        self.assertEqual(set(exportable_ctypes), set(ctype.id for ctype in role.exportable_ctypes.all()))
        self.assertEqual(set(apps), role.allowed_apps)
        self.assertEqual(set(apps), role.admin_4_apps)

    def test_add_credentials01(self):
        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        other_user = User.objects.create(username='chloe', role=role)
        contact    = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assertFalse(contact.can_view(other_user))

        self.assertEqual(0, role.credentials.count())

        url = '/creme_config/role/add_credentials/%s' % role.id
        self.assertEqual(200, self.client.get(url).status_code)

        set_type = SetCredentials.ESET_ALL
        response = self.client.post(url, data={
                                                'can_view':   True,
                                                'can_change': False,
                                                'can_delete': False,
                                                'can_link':   False,
                                                'can_unlink': False,
                                                'set_type':   set_type,
                                                'ctype':      0,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(SetCredentials.CRED_VIEW, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assert_(creds.ctype is None)

        contact = Contact.objects.get(pk=contact.id) #refresh cache
        self.assert_(contact.can_view(other_user))

    def test_add_credentials02(self):
        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        set_type = SetCredentials.ESET_OWN
        ct_id = ContentType.objects.get_for_model(Contact).id
        response = self.client.post('/creme_config/role/add_credentials/%s' % role.id,
                                    data={
                                            'can_view':   True,
                                            'can_change': True,
                                            'can_delete': False,
                                            'can_link':   False,
                                            'can_unlink': False,
                                            'set_type':   set_type,
                                            'ctype':      ct_id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE, creds.value)
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)
        self.assertEqual(ct_id,                   creds.ctype_id)

    def test_edit01(self):
        role = UserRole.objects.create(name='CEO')
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        other_user = User.objects.create(username='chloe', role=role)
        contact    = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assertFalse(contact.can_view(other_user)) #role.allowed_apps does not contain 'persons'

        response = self.client.get('/creme_config/role/edit/%s' % role.id)
        self.assertEqual(200,  response.status_code)

        name   = role.name + '_edited'
        get_ct = ContentType.objects.get_for_model
        creatable_ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        exportable_ctypes = [get_ct(Contact).id, get_ct(Meeting).id]
        apps   = ['persons', 'tickets']
        admin_apps = ['persons']
        response = self.client.post('/creme_config/role/edit/%s' % role.id, follow=True,
                                    data={
                                            'name':                    name,
                                            'creatable_ctypes':        creatable_ctypes,
                                            'exportable_ctypes':       exportable_ctypes,
                                            'allowed_apps':            apps,
                                            'admin_4_apps':            admin_apps,
                                            'set_credentials_check_0': True,
                                            'set_credentials_value_0': SetCredentials.ESET_ALL,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        role = UserRole.objects.get(pk=role.id) #refresh

        self.assertEqual(set(creatable_ctypes),  set(ctype.id for ctype in role.creatable_ctypes.all()))
        self.assertEqual(set(exportable_ctypes), set(ctype.id for ctype in role.exportable_ctypes.all()))
        self.assertEqual(set(apps),       role.allowed_apps)
        self.assertEqual(set(admin_apps), role.admin_4_apps)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(SetCredentials.CRED_VIEW, creds.value)
        self.assertEqual(SetCredentials.ESET_ALL,  creds.set_type)

        contact = Contact.objects.get(pk=contact.id) #refresh cache
        self.assert_(contact.can_view(other_user)) #role.allowed_apps contains 'persons' now

    def test_edit02(self):
        apps = ['persons']

        role = UserRole(name='CEO')
        role.allowed_apps = apps
        role.save()

        create_creds = SetCredentials.objects.create
        create_creds(role=role, value=SetCredentials.CRED_VIEW, set_type=SetCredentials.ESET_ALL)
        create_creds(role=role, value=SetCredentials.CRED_VIEW, set_type=SetCredentials.ESET_OWN)

        other_user = User.objects.create(username='chloe', role=role)
        yuki   = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        altena = Contact.objects.create(user=other_user, first_name=u'Alténa', last_name='??')
        self.assert_(yuki.can_view(other_user))
        self.assert_(altena.can_view(other_user))

        response = self.client.post('/creme_config/role/edit/%s' % role.id, follow=True,
                                    data={
                                            'name':                    role.name,
                                            'allowed_apps':            apps,
                                            'admin_4_apps':            [],
                                            'set_credentials_check_1': True,
                                            'set_credentials_value_1': SetCredentials.ESET_OWN,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        role = UserRole.objects.get(pk=role.id) #refresh
        self.failIf(role.creatable_ctypes.all())
        self.failIf(role.exportable_ctypes.all())

        yuki = Contact.objects.get(pk=yuki.id) #refresh caches
        altena = Contact.objects.get(pk=altena.id)
        self.assertFalse(yuki.can_view(other_user)) #no more SetCredentials
        self.assert_(altena.can_view(other_user))

    def test_delete01(self):
        role = self.role
        role.allowed_apps = ['persons']
        role.save()
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        other_user = self.other_user
        yuki = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assert_(yuki.can_view(other_user))
        self.assertEqual(1, EntityCredentials.objects.count())

        response = self.client.post('/creme_config/role/delete', follow=True,
                                    data={'id': role.id}
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFalse(UserRole.objects.count())

        self.assertFalse(EntityCredentials.get_default_creds().can_view())
        self.assertEqual(0, EntityCredentials.objects.count())
        self.assertEqual(0, SetCredentials.objects.count())
        self.assertEqual(1, User.objects.filter(pk=other_user.id).count())

        yuki = Contact.objects.get(pk=yuki.id) #refresh caches
        self.assertFalse(yuki.can_view(other_user)) #defaultCreds are applied

    def test_set_default_creds(self):
        defcreds = EntityCredentials.get_default_creds()
        self.assertFalse(defcreds.can_view())
        self.assertFalse(defcreds.can_change())
        self.assertFalse(defcreds.can_delete())
        self.assertFalse(defcreds.can_link())
        self.assertFalse(defcreds.can_unlink())

        response = self.client.get('/creme_config/role/set_default_creds/')
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_config/role/set_default_creds/', follow=True,
                                    data={
                                            'can_view':   True,
                                            'can_change': True,
                                            'can_delete': True,
                                            'can_link':   True,
                                            'can_unlink': True,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        defcreds = EntityCredentials.get_default_creds()
        self.assert_(defcreds.can_view())
        self.assert_(defcreds.can_change())
        self.assert_(defcreds.can_delete())
        self.assert_(defcreds.can_link())
        self.assert_(defcreds.can_unlink())
