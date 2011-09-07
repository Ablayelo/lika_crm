# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import RelationType
    from creme_core.models.block import *
    from creme_core import autodiscover
    from creme_core.gui.block import block_registry, Block, SpecificRelationsBlock
    from creme_core.blocks import history_block
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact  #need CremeEntity
except Exception, e:
    print 'Error:', e


__all__ = ('BlocksConfigTestCase',)


class BlocksConfigTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

        autodiscover()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/blocks/portal/').status_code)

    def test_add_detailview(self):
        url = '/creme_config/blocks/detailview/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        ct = ContentType.objects.get_for_model(Contact)
        self.assertEqual(0, BlockDetailviewLocation.objects.filter(content_type=ct).count())

        response = self.client.post(url, data={'ct_id': ct.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)
        self.assertEqual([('', 1)] * 4, [(bl.block_id, bl.order) for bl in b_locs])
        self.assertEqual(set([BlockDetailviewLocation.TOP, BlockDetailviewLocation.LEFT, BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM]),
                         set(bl.zone for bl in b_locs)
                        )

        response = self.client.get(url)

        try:
            choices = response.context['form'].fields['ct_id'].choices
        except Exception, e:
            self.fail(str(e))

        self.assert_(ct.id not in (ct_id for ct_id, ctype in choices))

    def _find_field_index(self, formfield, name):
        for i, (fname, fvname) in enumerate(formfield.choices):
            if fname == name:
                return i

        self.fail('No "%s" field' % name)

    def _assertNoInChoices(self, formfield, id_, error_msg):
        for fid, fvname in formfield.choices:
            if fid == id_:
                self.fail(error_msg + ' -> should not be in choices.')

    def _find_location(self, block_id, locations):
        for location in locations:
            if location.block_id == block_id:
                return location

        self.fail('No "%s" in locations' % block_id)

    def test_edit_detailview01(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.assertEqual(404, self.client.get('/creme_config/blocks/detailview/edit/%s' % ct.id).status_code)

    def test_edit_detailview02(self):
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post('/creme_config/blocks/detailview/add/', data={'ct_id': ct.id})
        self.assertEqual(4, BlockDetailviewLocation.objects.filter(content_type=ct).count())

        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_detailview02_1')
            verbose_name  = u'Testing purpose'

            def detailview_display(self, context):     return self._render(self.get_block_template_context(context))
            def home_display(self, context):           return '<table id="%s"></table>' % self.id_
            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_

        class FoobarBlock2(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_detailview02_2')
            verbose_name  = u'Testing purpose'

            #def detailview_display(self, context):    NO
            def home_display(self, context):           return '<table id="%s"></table>' % self.id_
            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_

        foobar_block1 = FoobarBlock1()
        foobar_block2 = FoobarBlock2()
        block_registry.register(foobar_block1, foobar_block2)

        url = '/creme_config/blocks/detailview/edit/%s' % ct.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            fields = response.context['form'].fields
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']
        except KeyError, e:
            self.fail(str(e))

        blocks = list(block_registry.get_compatible_blocks(model)) #TODO test get_compatible_blocks() in creme_core
        self.assert_(len(blocks) >= 5)
        self._find_field_index(top_field, foobar_block1.id_)
        self._assertNoInChoices(top_field, foobar_block2.id_, 'Block has no detailview_display() method')

        block_top_id1   = blocks[0].id_
        block_top_id2   = blocks[1].id_
        block_left_id   = blocks[2].id_
        block_right_id  = blocks[3].id_
        block_bottom_id = blocks[4].id_

        block_top_index1 = self._find_field_index(top_field, block_top_id1)
        block_top_index2 = self._find_field_index(top_field, block_top_id2)
        block_left_index = self._find_field_index(left_field, block_left_id)
        block_right_index = self._find_field_index(right_field, block_right_id)
        block_bottom_index = self._find_field_index(bottom_field, block_bottom_id)

        response = self.client.post(url,
                                    data={
                                            'top_check_%s' % block_top_index1: 'on',
                                            'top_value_%s' % block_top_index1: block_top_id1,
                                            'top_order_%s' % block_top_index1: 1,

                                            'top_check_%s' % block_top_index2: 'on',
                                            'top_value_%s' % block_top_index2: block_top_id2,
                                            'top_order_%s' % block_top_index2: 2,

                                            'left_check_%s' % block_left_index: 'on',
                                            'left_value_%s' % block_left_index: block_left_id,
                                            'left_order_%s' % block_left_index: 1,

                                            'right_check_%s' % block_right_index: 'on',
                                            'right_value_%s' % block_right_index: block_right_id,
                                            'right_order_%s' % block_right_index: 1,

                                            'bottom_check_%s' % block_bottom_index: 'on',
                                            'bottom_value_%s' % block_bottom_index: block_bottom_id,
                                            'bottom_order_%s' % block_bottom_index: 1,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)

        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.TOP]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(block_top_id1, locations).order)
        self.assertEqual(2, self._find_location(block_top_id2, locations).order)

        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.LEFT]
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(block_left_id, locations).order)

        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.RIGHT]
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(block_right_id, locations).order)

        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.BOTTOM]
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(block_bottom_id, locations).order)

    def test_edit_detailview03(self): #when no block -> fake block
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        blocks = list(block_registry.get_compatible_blocks(model))
        self.assert_(len(blocks) >= 5, blocks)

        create_loc = BlockDetailviewLocation.objects.create
        create_loc(content_type=ct, block_id=blocks[0].id_, order=1, zone=BlockDetailviewLocation.TOP)
        create_loc(content_type=ct, block_id=blocks[1].id_, order=1, zone=BlockDetailviewLocation.LEFT)
        create_loc(content_type=ct, block_id=blocks[2].id_, order=1, zone=BlockDetailviewLocation.RIGHT)
        create_loc(content_type=ct, block_id=blocks[3].id_, order=1, zone=BlockDetailviewLocation.BOTTOM)

        url = '/creme_config/blocks/detailview/edit/%s' % ct.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            fields = response.context['form'].fields
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']
        except KeyError, e:
            self.fail(str(e))

        block_top_id1   = blocks[0].id_
        block_top_id2   = blocks[1].id_

        self.assertEqual([block_top_id1], top_field.initial)
        self.assertEqual([block_top_id2], left_field.initial)
        self.assertEqual([blocks[2].id_], right_field.initial)
        self.assertEqual([blocks[3].id_], bottom_field.initial)

        block_top_index1 = self._find_field_index(top_field, block_top_id1)
        block_top_index2 = self._find_field_index(top_field, block_top_id2)

        response = self.client.post(url,
                                    data={
                                            'top_check_%s' % block_top_index1: 'on',
                                            'top_value_%s' % block_top_index1: block_top_id1,
                                            'top_order_%s' % block_top_index1: 1,

                                            'top_check_%s' % block_top_index2: 'on',
                                            'top_value_%s' % block_top_index2: block_top_id2,
                                            'top_order_%s' % block_top_index2: 2,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)
        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.TOP]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(block_top_id1, locations).order)
        self.assertEqual(2, self._find_location(block_top_id2, locations).order)

        self.assertEqual([('', 1)], [(bl.block_id, bl.order) for bl in b_locs if bl.zone == BlockDetailviewLocation.LEFT])
        self.assertEqual([('', 1)], [(bl.block_id, bl.order) for bl in b_locs if bl.zone == BlockDetailviewLocation.RIGHT])
        self.assertEqual([('', 1)], [(bl.block_id, bl.order) for bl in b_locs if bl.zone == BlockDetailviewLocation.BOTTOM])

    def test_edit_detailview04(self): #default conf
        BlockDetailviewLocation.objects.filter(content_type=None).delete()
        url = '/creme_config/blocks/detailview/edit/0'
        self.assertEqual(404, self.client.get(url).status_code)

        blocks = list(block_registry.get_compatible_blocks(model=None))
        self.assert_(len(blocks) >= 5, blocks)

        create_loc = BlockDetailviewLocation.objects.create
        create_loc(block_id=blocks[0].id_, order=1, zone=BlockDetailviewLocation.TOP)
        create_loc(block_id=blocks[1].id_, order=1, zone=BlockDetailviewLocation.LEFT)
        create_loc(block_id=blocks[2].id_, order=1, zone=BlockDetailviewLocation.RIGHT)
        create_loc(block_id=blocks[3].id_, order=1, zone=BlockDetailviewLocation.BOTTOM)

        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=None)
        self.assertEqual([('', 1)] * 4, [(bl.block_id, bl.order) for bl in b_locs])
        self.assertEqual(set([BlockDetailviewLocation.TOP, BlockDetailviewLocation.LEFT, BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM]),
                         set(bl.zone for bl in b_locs)
                        )

    def test_edit_detailview05(self): #post one block several times -> validation error
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post('/creme_config/blocks/detailview/add/', data={'ct_id': ct.id})
        self.assertEqual(4, BlockDetailviewLocation.objects.filter(content_type=ct).count())

        url = '/creme_config/blocks/detailview/edit/%s' % ct.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            fields = response.context['form'].fields
            left_field  = fields['left']
            right_field = fields['right']
        except KeyError, e:
            self.fail(str(e))

        blocks = list(block_registry.get_compatible_blocks(model))
        self.assert_(len(blocks))

        evil_block = blocks[0]

        block_left_id = block_right_id = evil_block.id_ # <= same block !!
        block_left_index  = self._find_field_index(left_field,  block_left_id)
        block_right_index = self._find_field_index(right_field, block_right_id)

        response = self.client.post(url,
                                    data={
                                            'right_check_%s' % block_right_index: 'on',
                                            'right_value_%s' % block_right_index: block_right_id,
                                            'right_order_%s' % block_right_index: 1,

                                            'left_check_%s' % block_left_index: 'on',
                                            'left_value_%s' % block_left_index: block_left_id,
                                            'left_order_%s' % block_left_index: 1,
                                         }
                                   )
        self.assertFormError(response, 'form', field=None,
                             errors=[_(u'The following block should be displayed only once: <%s>') % evil_block.verbose_name]
                            )

    def test_edit_detailview06(self): #instance block, relationtype block
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post('/creme_config/blocks/detailview/add/', data={'ct_id': ct.id})

        rtype = RelationType.objects.all()[0]
        rtype_block_id = SpecificRelationsBlock.generate_id('test', 'foobar')
        RelationBlockItem.objects.create(block_id=rtype_block_id, relation_type=rtype)

        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')
        instance_block_id = InstanceBlockConfigItem.generate_id('test__blocks__FoobarBlock', 'test', 'foobar')
        InstanceBlockConfigItem.objects.create(block_id=instance_block_id, entity=naru, verbose='All stuffes')

        response = self.client.get('/creme_config/blocks/detailview/edit/%s' % ct.id)
        self.assertEqual(200, response.status_code)

        try:
            top_field = response.context['form'].fields['top']
        except KeyError, e:
            self.fail(str(e))

        choices = [block_id for block_id, block_name in top_field.choices]
        self.assert_(rtype_block_id in choices, choices)
        self.assert_(instance_block_id in choices, choices)

    def test_delete_detailview01(self): #can not delete default conf
        response = self.client.post('/creme_config/blocks/detailview/delete', data={'id': 0})
        self.assertEqual(404, response.status_code)

    def test_delete_detailview02(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.client.post('/creme_config/blocks/detailview/add/', data={'ct_id': ct.id})

        response = self.client.post('/creme_config/blocks/detailview/delete', data={'id': ct.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, BlockDetailviewLocation.objects.filter(content_type=ct).count())

    def test_add_portal(self):
        url = '/creme_config/blocks/portal/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        app_name = 'persons'
        self.assertEqual(0, BlockPortalLocation.objects.filter(app_name=app_name).count())

        response = self.client.post(url, data={'app_name': app_name})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[-1]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

        response = self.client.get(url)

        try:
            choices = response.context['form'].fields['app_name'].choices
        except Exception, e:
            self.fail(str(e))

        names = set(name for name, vname in choices)
        self.assert_(app_name not in names, names)
        self.assert_('creme_core' not in names, names)
        self.assert_('creme_config' not in names, names)

    def test_edit_portal01(self):
        self.assertEqual(404, self.client.get('/creme_config/blocks/portal/edit/persons').status_code)

    def test_edit_portal02(self):
        app_name = 'persons'

        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal02_1')
            verbose_name  = u'Testing purpose'

            ##NB: only portal_display() method
            #def detailview_display(self, context): return self._render(self.get_block_template_context(context))
            #def home_display(self, context): return '<table id="%s"></table>' % self.id_

            def portal_display(self, context, ct_ids):
                return '<table id="%s"></table>' % self.id_

        class FoobarBlock2(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal02_2')
            verbose_name  = u'Testing purpose'
            configurable  = False # <----

            def portal_display(self, context, ct_ids):
                return '<table id="%s"></table>' % self.id_

        class FoobarBlock3(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal02_3')
            verbose_name  = u'Testing purpose'
            target_apps   = (app_name, 'billing') # <-- OK

            def portal_display(self, context, ct_ids):
                return '<table id="%s"></table>' % self.id_

        class FoobarBlock4(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal02_4')
            verbose_name  = u'Testing purpose'
            target_apps   = ('billing', 'documents') # <-- KO

            def portal_display(self, context, ct_ids):
                return '<table id="%s"></table>' % self.id_


        foobar_block1 = FoobarBlock1()
        foobar_block2 = FoobarBlock2()
        foobar_block3 = FoobarBlock3()
        foobar_block4 = FoobarBlock4()
        block_registry.register(foobar_block1, foobar_block2, foobar_block3, foobar_block4)

        self.client.post('/creme_config/blocks/portal/add/', data={'app_name': app_name})
        self.assertEqual(1, BlockPortalLocation.objects.filter(app_name=app_name).count())

        url = '/creme_config/blocks/portal/edit/%s' % app_name
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        choices = blocks_field.choices
        self.assert_(len(choices) >= 2)
        self._find_field_index(blocks_field, foobar_block1.id_)
        self._assertNoInChoices(blocks_field, foobar_block2.id_, 'Block is not configurable')
        self._find_field_index(blocks_field, foobar_block3.id_)
        self._assertNoInChoices(blocks_field, foobar_block4.id_, 'Block is not compatible with this app')

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url,
                                    data={
                                            'blocks_check_%s' % index1: 'on',
                                            'blocks_value_%s' % index1: block_id1,
                                            'blocks_order_%s' % index1: 1,

                                            'blocks_check_%s' % index2: 'on',
                                            'blocks_value_%s' % index2: block_id2,
                                            'blocks_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def _get_blocks_4_portal(self):
        blocks = list(block for block_id, block in  block_registry if hasattr(block, 'portal_display'))
        self.assert_(len(blocks) >= 2, blocks)

        return blocks

    def test_edit_portal03(self): #set no block -> fake blocks
        app_name = 'persons'
        blocks = self._get_blocks_4_portal()

        create_loc = BlockPortalLocation.objects.create
        create_loc(app_name=app_name, block_id=blocks[0].id_, order=1)
        create_loc(app_name=app_name, block_id=blocks[1].id_, order=2)

        url = '/creme_config/blocks/portal/edit/%s' % app_name
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        self.assertEqual([blocks[0].id_, blocks[1].id_], blocks_field.initial)

        response = self.client.post(url, data={})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[0]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

    def test_edit_portal04(self): #default conf
        BlockPortalLocation.objects.filter(app_name='').delete()
        url = '/creme_config/blocks/portal/edit/default'
        self.assertEqual(404, self.client.get(url).status_code)

        blocks = self._get_blocks_4_portal()
        create_loc = BlockPortalLocation.objects.create
        create_loc(app_name='', block_id=blocks[0].id_, order=1)
        create_loc(app_name='', block_id=blocks[1].id_, order=2)

        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=''))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[0]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

    def test_edit_portal05(self): #home -> use 'home_display' method
        app_name = 'creme_core'

        self.assert_(BlockPortalLocation.objects.filter(app_name=app_name).exists())

        class FoobarBlock(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal05')
            verbose_name  = u'Testing purpose'

            ##NB: only 'home_display' method
            #def detailview_display(self, context): return self._render(self.get_block_template_context(context))
            #def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_

            def home_display(self, context):
                return '<table id="%s"></table>' % self.id_

        foobar_block = FoobarBlock()
        block_registry.register(foobar_block)

        url = '/creme_config/blocks/portal/edit/%s' % app_name
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        self._find_field_index(blocks_field, foobar_block.id_)

    def test_delete_portal(self):
        app_name = 'persons'
        self.client.post('/creme_config/blocks/portal/add/', data={'app_name': app_name})

        response = self.client.post('/creme_config/blocks/portal/delete', data={'id': app_name})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   BlockPortalLocation.objects.filter(app_name=app_name).count())

    def test_delete_home(self): #can not delete home conf
        #TODO: use a helper method ??
        app_name = 'creme_core'
        blocks = list(block for block_id, block in  block_registry if hasattr(block, 'home_display'))
        self.assert_(len(blocks) >= 1, blocks)

        BlockPortalLocation.objects.create(app_name=app_name, block_id=blocks[0].id_, order=1)

        response = self.client.post('/creme_config/blocks/portal/delete', data={'id': app_name})
        self.assertEqual(404, response.status_code)

    def test_edit_default_mypage(self):
        url = '/creme_config/blocks/mypage/edit/default'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        choices = blocks_field.choices
        self.assert_(len(choices) >= 2)
        self.assertEqual(list(BlockMypageLocation.objects.filter(user=None).values_list('block_id', flat=True)),
                        blocks_field.initial
                        )

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url,
                                    data={
                                            'blocks_check_%s' % index1: 'on',
                                            'blocks_value_%s' % index1: block_id1,
                                            'blocks_order_%s' % index1: 1,

                                            'blocks_check_%s' % index2: 'on',
                                            'blocks_value_%s' % index2: block_id2,
                                            'blocks_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockMypageLocation.objects.filter(user=None))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def test_edit_mypage(self):
        user = self.user
        url = '/creme_config/blocks/mypage/edit'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        choices = blocks_field.choices
        self.assert_(len(choices) >= 2)
        self.assertEqual(list(BlockMypageLocation.objects.filter(user=None).values_list('block_id', flat=True)),
                         blocks_field.initial
                        )

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url,
                                    data={
                                            'blocks_check_%s' % index1: 'on',
                                            'blocks_value_%s' % index1: block_id1,
                                            'blocks_order_%s' % index1: 1,

                                            'blocks_check_%s' % index2: 'on',
                                            'blocks_value_%s' % index2: block_id2,
                                            'blocks_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockMypageLocation.objects.filter(user=user))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def test_delete_default_mypage01(self):
        loc = BlockMypageLocation.objects.create(user=None, block_id=history_block.id_, order=1)
        response = self.client.post('/creme_config/blocks/mypage/default/delete', data={'id': loc.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   BlockMypageLocation.objects.filter(pk=loc.pk).count())

    def test_delete_default_mypage02(self): #'user' must be 'None'
        loc = BlockMypageLocation.objects.create(user=self.user, block_id=history_block.id_, order=1)
        response = self.client.post('/creme_config/blocks/mypage/default/delete', data={'id': loc.id})
        self.assertEqual(404, response.status_code)
        self.assertEqual(1,   BlockMypageLocation.objects.filter(pk=loc.pk).count())

    def test_delete_mypage01(self):
        loc = BlockMypageLocation.objects.create(user=self.user, block_id=history_block.id_, order=1)
        response = self.client.post('/creme_config/blocks/mypage/delete', data={'id': loc.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   BlockMypageLocation.objects.filter(pk=loc.pk).count())

    def test_delete_mypage02(self): #BlockMypageLocation must belong to the user
        loc = BlockMypageLocation.objects.create(user=self.other_user, block_id=history_block.id_, order=1)
        response = self.client.post('/creme_config/blocks/mypage/delete', data={'id': loc.id})
        self.assertEqual(404, response.status_code)
        self.assertEqual(1,   BlockMypageLocation.objects.filter(pk=loc.pk).count())

    def test_add_relationblock(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'), is_custom=False
                                     )
        self.assertFalse(RelationBlockItem.objects.count())

        url = '/creme_config/relation_block/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'relation_type': rt.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rbi = RelationBlockItem.objects.all()
        self.assertEqual(1,     len(rbi))
        self.assertEqual(rt.id, rbi[0].relation_type.id)

    def test_delete_relationblock(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'), is_custom=False
                                     )
        rbi = RelationBlockItem.objects.create(block_id='foobarid', relation_type=rt)
        loc = BlockDetailviewLocation.create(block_id=rbi.block_id, order=5, zone=BlockDetailviewLocation.RIGHT, model=Contact)

        self.assertEqual(200, self.client.post('/creme_config/relation_block/delete', data={'id': rbi.id}).status_code)
        self.assertFalse(RelationBlockItem.objects.filter(pk=rbi.pk).count())
        self.assertFalse(BlockDetailviewLocation.objects.filter(pk=loc.pk).count())

    def test_delete_instanceblock(self): ##(r'^instance_block/delete$',  'blocks.delete_instance_block')
        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')
        instance_block_id = InstanceBlockConfigItem.generate_id('test__blocks__FoobarBlock', 'test', 'foobar')
        ibi = InstanceBlockConfigItem.objects.create(block_id=instance_block_id, entity=naru, verbose='All stuffes')
        loc = BlockDetailviewLocation.create(block_id=ibi.block_id, order=5, zone=BlockDetailviewLocation.RIGHT, model=Contact)

        self.assertEqual(200, self.client.post('/creme_config/instance_block/delete', data={'id': ibi.id}).status_code)
        self.assertFalse(InstanceBlockConfigItem.objects.filter(pk=ibi.pk).count())
        self.assertFalse(BlockDetailviewLocation.objects.filter(pk=loc.pk).count())
