# -*- coding: utf-8 -*-

try:
    from django.db.models import fields
    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.tests.base import CremeTestCase
    from creme_core.models import CremePropertyType, CremeProperty, CremeEntity #, PreferedMenuItem
    from creme_core.utils import meta

    from persons.models import Contact

    from tickets.models import Ticket
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('MetaTestCase',)


class MetaTestCase(CremeTestCase):
    def test_get_instance_field_info(self):
        text = 'TEXT'

        user   = User.objects.create(username='name')
        ptype  = CremePropertyType.objects.create(text=text, is_custom=True)
        entity = CremeEntity.objects.create(user=user)
        prop   = CremeProperty(type=ptype, creme_entity=entity)

        self.assertEqual((fields.CharField,    text), meta.get_instance_field_info(prop, 'type__text'))
        self.assertEqual((fields.BooleanField, True), meta.get_instance_field_info(prop, 'type__is_custom'))

        self.assertEqual((None, ''), meta.get_instance_field_info(prop, 'foobar__is_custom'))
        self.assertEqual((None, ''), meta.get_instance_field_info(prop, 'type__foobar'))

        self.assertEqual(fields.CharField, meta.get_instance_field_info(prop, 'creme_entity__entity_type__name')[0])

    def test_get_model_field_info(self):
        self.assertEqual([], meta.get_model_field_info(CremeEntity, 'foobar'))
        self.assertEqual([], meta.get_model_field_info(CremeEntity, 'foo__bar'))

        #[{'field': <django.db.models.fields.related.ForeignKey object at ...>,
        #  'model': <class 'creme_core.models.creme_property.CremePropertyType'>}]
        with self.assertNoException():
            info = meta.get_model_field_info(CremeProperty, 'type')
            self.assertEqual(1, len(info))

            desc = info[0]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(CremePropertyType, desc['model'])

        #[{ 'field': <django.db.models.fields.related.ForeignKey object at ...>,
        #   'model': <class 'creme_core.models.creme_property.CremePropertyType'>},
        # {'field': <django.db.models.fields.CharField object at ...>,
        #   'model': None}]
        with self.assertNoException():
            info = meta.get_model_field_info(CremeProperty, 'type__text')
            self.assertEqual(2, len(info))

            desc = info[0]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(CremePropertyType, desc['model'])

            desc = info[1]
            self.assertIsInstance(desc['field'], fields.CharField)
            self.assertIsNone(desc['model'])

        #[{'field': <django.db.models.fields.related.ForeignKey object at 0x9d123ec>,
        #  'model': <class 'creme_core.models.entity.CremeEntity'>},
        # {'field': <django.db.models.fields.related.ForeignKey object at 0x9d0378c>,
        #  'model': <class 'django.contrib.contenttypes.models.ContentType'>},
        # {'field': <django.db.models.fields.CharField object at 0x99d302c>,
        #  'model': None}]
        with self.assertNoException():
            info = meta.get_model_field_info(CremeProperty, 'creme_entity__entity_type__name')
            self.assertEqual(3, len(info))

            desc = info[0]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(CremeEntity, desc['model'])

            desc = info[1]
            self.assertIsInstance(desc['field'], fields.related.ForeignKey)
            self.assertEqual(ContentType, desc['model'])

            desc = info[2]
            self.assertIsInstance(desc['field'], fields.CharField)
            self.assertIsNone(desc['model'])

    def test_get_date_fields(self):
        entity = CremeEntity()
        get_field = entity._meta.get_field
        self.assertTrue(meta.is_date_field(get_field('created')))
        self.assertFalse(meta.is_date_field(get_field('user')))

        datefields = meta.get_date_fields(entity)
        self.assertEqual(2, len(datefields))
        self.assertEqual(set(('created', 'modified')), set(f.name for f in datefields))

    def test_field_enumerator01(self):
        expected = [('id',                         'ID'),
                    ('created',                    _('Creation date')),
                    ('modified',                   _('Last modification')),
                    #('entity_type',                'entity type'),
                    ('header_filter_search_field', 'header filter search field'),
                    ('is_deleted',                 'is deleted'),
                    ('is_actived',                 'is actived'),
                    #('user',                       _('User')),
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).choices()
        self.assertEqual([('id',                         'ID'),
                          ('created',                    _('Creation date')),
                          ('modified',                   _('Last modification')),
                          ('entity_type',                'entity type'),
                          ('header_filter_search_field', 'header filter search field'),
                          ('is_deleted',                 'is deleted'),
                          ('is_actived',                 'is actived'),
                          ('user',                       _('User')),
                         ],
                         choices, choices
                        )

    def test_field_enumerator02(self): #filter, exclude (simple)
        expected = [('created',  _('Creation date')),
                    ('modified', _('Last modification')),
                    #('user',     _('User'))
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity).exclude(viewable=False).choices()
        self.assertEqual(expected, choices, choices)

        expected = [('created',  _('Creation date')),
                    ('modified', _('Last modification')),
                    ('user',     _('User'))
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).exclude(viewable=False).choices()
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator03(self): #deep = 1
        fs = u'[%s] - %%s' % _('User')
        expected = [('created',          _('Creation date')),
                    ('modified',         _('Last modification')),
                    #('user',             _('User')),
                    ('user__username',   fs % _('username')),
                    ('user__first_name', fs % _('first name')),
                    ('user__last_name',  fs % _('last name')),
                    ('user__email',      fs % _('e-mail address')),
                    #('user__role',       fs % _('Role')),
                    ('user__is_team',    fs % _('Is a team ?')),
                   ]
        self.assertEqual(expected, meta.ModelFieldEnumerator(CremeEntity, deep=1).filter(viewable=True).choices())
        self.assertEqual(expected, meta.ModelFieldEnumerator(CremeEntity, deep=1, only_leafs=True).filter(viewable=True).choices())
        self.assertEqual(meta.ModelFieldEnumerator(CremeEntity, deep=1, only_leafs=False).filter(viewable=True).choices(),
                         [('created',          _('Creation date')),
                          ('modified',         _('Last modification')),
                          ('user',             _('User')),
                          ('user__username',   fs % _('username')),
                          ('user__first_name', fs % _('first name')),
                          ('user__last_name',  fs % _('last name')),
                          ('user__email',      fs % _('e-mail address')),
                          ('user__role',       fs % _('Role')),
                          ('user__is_team',    fs % _('Is a team ?')),
                         ]
                        )

    def test_field_enumerator04(self): #filter with function, exclude
        self.assertEqual(meta.ModelFieldEnumerator(CremeEntity, deep=1).filter(lambda f: f.name.endswith('ied'), viewable=True).choices(),
                         [('modified', _('Last modification'))]
                        )
        self.assertEqual(meta.ModelFieldEnumerator(CremeEntity, deep=0).exclude(lambda f: f.name.endswith('ied'), viewable=False).choices(),
                         [('created',  _('Creation date')),
                          #('user',     _('User')),
                         ]
                        )

    def test_field_enumerator05(self): #other ct
        expected = [('created',     _('Creation date')),
                    ('modified',    _('Last modification')),
                    ('last_name',   _('Last name')),
                    ('first_name',  _('First name')),
                    ('description', _('Description')),
                    ('skype',       _('Skype')),
                    ('phone',       _('Phone number')),
                    ('mobile',      _('Mobile')),
                    ('fax',         _('Fax')),
                    ('email',       _('Email address')),
                    ('url_site',    _('Web Site')),
                    ('birthday',    _('Birthday')),
                   ]
        choices = meta.ModelFieldEnumerator(Contact).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(Contact, only_leafs=False) \
                      .filter((lambda f: f.get_internal_type() != 'ForeignKey'), viewable=True) \
                      .choices()
        expected.append(('language',  _('Spoken language(s)'))) #TODO: test with another model with a m2m field when this field is removed....
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator06(self): #filter/exclude : multiple conditions + field true attributes
        expected = [('user',             _('User')),
                    ('civility',         _('Civility')),
                    ('last_name',        _('Last name')),
                    ('first_name',       _('First name')),
                    ('description',      _('Description')),
                    ('skype',            _('Skype')),
                    ('phone',            _('Phone number')),
                    ('mobile',           _('Mobile')),
                    ('fax',              _('Fax')),
                    ('position',         _('Position')),
                    ('sector',           _('Line of business')),
                    ('email',            _('Email address')),
                    ('url_site',         _('Web Site')),
                    #('billing_address',  _('Billing address')),
                    #('shipping_address', _('Shipping address')),
                    #('is_user',          _('Is an user')),
                    ('birthday',         _('Birthday')),
                    ('image',            _('Photograph')),
                   ]
        choices = meta.ModelFieldEnumerator(Contact, only_leafs=False).filter(editable=True, viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(Contact, only_leafs=False).exclude(editable=False, viewable=False).choices()
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator07(self): #ordering of FKs
        choices = meta.ModelFieldEnumerator(Ticket, deep=1, only_leafs=False).filter(viewable=True).choices()
        fs = u'[%s] - %s'
        self.assertEqual([('created',           _('Creation date')),
                          ('modified',          _('Last modification')),
                          ('user',              _('User')),
                          ('title',             _('Title')),
                          ('description',       _('Description')),
                          ('status',            _('Status')),
                          ('priority',          _('Priority')),
                          ('criticity',         _('Criticity')),
                          ('solution',          _('Solution')),
                          ('closing_date',      _('Closing date')),
                          ('user__username',    fs % (_('User'), _('username'))),
                          ('user__first_name',  fs % (_('User'), _('first name'))),
                          ('user__last_name',   fs % (_('User'), _('last name'))),
                          ('user__email',       fs % (_('User'), _('e-mail address'))),
                          ('user__role',        fs % (_('User'), _('Role'))),
                          ('user__is_team',     fs % (_('User'), _('Is a team ?'))),
                          ('status__name',      fs % (_('Status'), _('Name'))),
                          ('status__is_custom', fs % (_('Status'), _('is custom'))),
                          ('priority__name',    fs % (_('Priority'), _('Name'))),
                          ('criticity__name',   fs % (_('Criticity'), _('Name'))),
                         ],
                         choices, choices
                        )

    #TODO: complete

    