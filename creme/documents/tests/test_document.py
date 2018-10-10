# -*- coding: utf-8 -*-

try:
    import filecmp
    from functools import partial
    from os.path import join, exists

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.test import override_settings
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.gui.field_printers import field_printers_registry
    from creme.creme_core.models import CremeEntity, RelationType, HeaderFilter, SetCredentials
    from creme.creme_core.tests.fake_models import FakeOrganisation

    from creme.persons.tests.base import skipIfCustomContact
    from creme.persons import get_contact_model

    from .base import (_DocumentsTestCase, skipIfCustomDocument,
            skipIfCustomFolder, Folder, Document)
    from ..constants import REL_SUB_RELATED_2_DOC, UUID_FOLDER_RELATED2ENTITIES
    from ..models import FolderCategory, DocumentCategory
    from ..utils import get_csv_folder_or_create
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomDocument
@skipIfCustomFolder
class DocumentTestCase(_DocumentsTestCase):
    def _buid_addrelated_url(self, entity):
        return reverse('documents__create_related_document', args=(entity.id,))

    def test_populate(self):
        self.get_object_or_fail(RelationType, pk=REL_SUB_RELATED_2_DOC)

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        self.assertTrue(hf_filter(entity_type=get_ct(Document)).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(Folder)).exists())

        self.assertTrue(Folder.objects.exists())
        self.assertTrue(FolderCategory.objects.exists())
        self.assertTrue(DocumentCategory.objects.exists())

    # def test_portal(self):
    #     self.login()
    #     self.assertGET200(reverse('documents__portal'))

    @override_settings(ALLOWED_EXTENSIONS=('txt', 'pdf'))
    def test_createview01(self):
        self.login()

        self.assertFalse(Document.objects.exists())

        url = self.ADD_DOC_URL
        self.assertGET200(url)

        ext = settings.ALLOWED_EXTENSIONS[0]

        title = 'Test doc'
        description = 'Test description'
        content = 'Yes I am the content (DocumentTestCase.test_createview)'
        # file_obj, file_name = self._build_filedata(content, suffix='.{}'.format(ext))
        file_obj = self._build_filedata(content, suffix='.{}'.format(ext))
        folder = Folder.objects.all()[0]
        response = self.client.post(self.ADD_DOC_URL, follow=True,
                                    data={'user':     self.user.pk,
                                          'title':    title,
                                          'filedata': file_obj,
                                          'linked_folder':   folder.id,
                                          'description': description,
                                         }
                                   )
        self.assertNoFormError(response)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.linked_folder)

        mime_type = doc.mime_type
        self.assertIsNotNone(mime_type)

        self.assertRedirects(response, doc.get_absolute_url())

        filedata = doc.filedata
        # self.assertEqual('upload/documents/' + file_name, filedata.name)
        self.assertEqual('upload/documents/' + file_obj.base_name, filedata.name)
        # filedata.open()
        filedata.open('r')
        self.assertEqual([content], filedata.readlines())
        filedata.close()

        # Download
        response = self.assertGET200(reverse('creme_core__dl_file', args=(doc.filedata,)))
        # self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('text/plain', response['Content-Type'])
        # self.assertEqual('attachment; filename=' + file_name,
        self.assertEqual('attachment; filename=' + file_obj.base_name,
                         response['Content-Disposition']
                        )

    @override_settings(ALLOWED_EXTENSIONS=('txt', 'png', 'py'))
    def test_createview02(self):
        "Forbidden extension"
        self.login()

        ext = 'php'
        self.assertNotIn(ext, settings.ALLOWED_EXTENSIONS)

        title = 'My doc'
        # file_obj, file_name = self._build_filedata('Content', suffix='.' + ext)
        file_obj = self._build_filedata('Content', suffix='.' + ext)
        doc = self._create_doc(title, file_obj)

        filedata = doc.filedata
        # self.assertEqual('upload/documents/{}.txt'.format(file_name), filedata.name)
        self.assertEqual('upload/documents/{}.txt'.format(file_obj.base_name), filedata.name)

        # Download
        response = self.assertGET200(reverse('creme_core__dl_file', args=(doc.filedata,)))
        # self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('text/plain', response['Content-Type'])
        # # self.assertEqual('attachment; filename=' + file_name,
        # self.assertEqual('attachment; filename={}.txt'.format(file_name),
        self.assertEqual('attachment; filename={}.txt'.format(file_obj.base_name),
                         response['Content-Disposition']
                        )

    @override_settings(ALLOWED_EXTENSIONS=('txt', 'png', 'py'))
    def test_createview03(self):
        "Double extension (bugfix)"
        self.login()

        ext = 'php'
        self.assertNotIn(ext, settings.ALLOWED_EXTENSIONS)

        title = 'My doc'
        # file_obj, file_name = self._build_filedata('Content', suffix='.old.' + ext)
        file_obj = self._build_filedata('Content', suffix='.old.' + ext)
        doc = self._create_doc(title, file_obj)

        filedata = doc.filedata
        # self.assertEqual('upload/documents/{}.txt'.format(file_name), filedata.name)
        self.assertEqual('upload/documents/{}.txt'.format(file_obj.base_name), filedata.name)

        # Download
        response = self.assertGET200(reverse('creme_core__dl_file', args=(doc.filedata,)))
        # self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('text/plain', response['Content-Type'])
        # # self.assertEqual('attachment; filename=' + file_name,
        # self.assertEqual('attachment; filename={}.txt'.format(file_name),
        self.assertEqual('attachment; filename={}.txt'.format(file_obj.base_name),
                         response['Content-Disposition']
                        )

    def test_createview04(self):
        "No extension"
        self.login()

        title = 'My doc'
        # file_obj, file_name = self._build_filedata('Content', suffix='')
        file_obj = self._build_filedata('Content', suffix='')
        doc = self._create_doc(title, file_obj)

        filedata = doc.filedata
        # self.assertEqual('upload/documents/{}.txt'.format(file_name), filedata.name)
        self.assertEqual('upload/documents/{}.txt'.format(file_obj.base_name), filedata.name)

        # Download
        response = self.assertGET200(reverse('creme_core__dl_file', args=(doc.filedata,)))
        # self.assertEqual('txt', response['Content-Type'])
        self.assertEqual('text/plain', response['Content-Type'])
        # self.assertEqual('attachment; filename={}.txt'.format(file_name),
        self.assertEqual('attachment; filename={}.txt'.format(file_obj.base_name),
                         response['Content-Disposition']
                        )

    def test_createview05(self):
        "No title"
        user = self.login()

        ext = settings.ALLOWED_EXTENSIONS[0]
        # file_obj, file_name = self._build_filedata('Content', suffix='.' + ext)
        file_obj = self._build_filedata('Content', suffix='.' + ext)

        folder = Folder.objects.create(user=user, title='test_createview05')
        response = self.client.post(self.ADD_DOC_URL, follow=True,
                                    data={'user':     user.pk,
                                          # 'title':    '',
                                          'filedata': file_obj,
                                          'linked_folder':   folder.id,
                                         }
                                   )

        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, linked_folder=folder)
        file_name = file_obj.base_name
        self.assertEqual('upload/documents/' + file_name, doc.filedata.name)
        self.assertEqual(file_name, doc.title)

    def test_download_error(self):
        self.login()
        self.assertGET404(reverse('creme_core__dl_file', args=('tmpLz48vy.txt',)))

    def test_editview(self):
        user = self.login()

        title       = 'Test doc'
        description = 'Test description'
        content     = 'Yes I am the content (DocumentTestCase.test_editview)'
        # doc = self._create_doc(title, self._build_filedata(content)[0], description=description)
        doc = self._create_doc(title, self._build_filedata(content), description=description)

        url = doc.get_edit_absolute_url()
        self.assertGET200(url)

        title       = title.upper()
        description = description.upper()
        # content     = content.upper() TODO: use ?
        folder      = Folder.objects.create(title='Test folder', parent_folder=None,
                                            category=FolderCategory.objects.all()[0],
                                            user=user,
                                           )

        response = self.client.post(url, follow=True,
                                    data={'user':          user.pk,
                                          'title':         title,
                                          'description':   description,
                                          'linked_folder': folder.id,
                                         }
                                   )
        self.assertNoFormError(response)

        doc = self.refresh(doc)
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.linked_folder)

        self.assertRedirects(response, doc.get_absolute_url())

    def test_add_related_document01(self):
        user = self.login()
        root_folder = self.get_object_or_fail(Folder, uuid=UUID_FOLDER_RELATED2ENTITIES)

        Folder.objects.create(user=user, title='Creme')  # Should not be used

        entity = CremeEntity.objects.create(user=user)
        url = self._buid_addrelated_url(entity)
        context = self.assertGET200(url).context
        # self.assertEqual(_('New document for «%s»') % entity, context.get('title'))
        self.assertEqual(_('New document for «{}»').format(entity), context.get('title'))
        self.assertEqual(Document.save_label,                       context.get('submit_label'))

        def post(title):
            response = self.client.post(
                url, follow=True,
                data={
                    'user': user.id,
                    'title': title,
                    'description': 'Test description',
                    'filedata': self._build_filedata(
                        'Yes I am the content (DocumentTestCase.test_add_related_document01)'
                    # )[0],
                    ),
                }
            )
            self.assertNoFormError(response)

            return self.get_object_or_fail(Document, title=title)

        doc1 = post('Related doc')
        self.assertRelationCount(1, entity, REL_SUB_RELATED_2_DOC, doc1)

        entity_folder = doc1.linked_folder
        self.assertIsNotNone(entity_folder)
        self.assertEqual('{}_{}'.format(entity.id, entity), entity_folder.title)

        ct_folder = entity_folder.parent_folder
        self.assertIsNotNone(ct_folder)
        self.assertEqual(str(CremeEntity._meta.verbose_name), ct_folder.title)
        self.assertEqual(root_folder, ct_folder.parent_folder)

        doc2 = post('Related doc #2')
        entity_folder2 = doc2.linked_folder
        self.assertEqual(entity_folder, entity_folder2)
        self.assertEqual(ct_folder,     entity_folder2.parent_folder)

    def test_add_related_document02(self):
        "Creation credentials"
        self.login(is_superuser=False, allowed_apps=['documents', 'creme_core'])

        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE |
                  EntityCredentials.LINK | EntityCredentials.UNLINK,
        )

        entity = CremeEntity.objects.create(user=self.user)
        self.assertGET403(self._buid_addrelated_url(entity))

    def test_add_related_document03(self):
        "Link credentials"
        user = self.login(is_superuser=False, allowed_apps=['documents', 'creme_core'],
                          creatable_models=[Document]
                         )

        create_sc = partial(SetCredentials.objects.create, role=self.role,
                            set_type=SetCredentials.ESET_OWN,
                           )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK,  # Not EntityCredentials.LINK
                 )

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url = self._buid_addrelated_url(orga)
        self.assertGET403(url)

        get_ct = ContentType.objects.get_for_model
        create_sc(value=EntityCredentials.LINK, ctype=get_ct(FakeOrganisation))
        self.assertGET403(url)

        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Document))
        self.assertGET200(url)

        response = self.assertPOST200(
            url, follow=True,
            data={'user': self.other_user.pk,
                  'title': 'Title',
                  'description': 'Test description',
                  'filedata':
                      self._build_filedata(
                          'Yes I am the content (DocumentTestCase.test_add_related_document03)'
                      # )[0],
                      ),
            }
        )
        self.assertFormError(response, 'form', 'user',
                             _('You are not allowed to link with the «{models}» of this user.').format(
                                     models=_('Documents'),
                                )
                            )

    def test_add_related_document04(self):
        "Link credentials with related entity are needed"
        user = self.login(is_superuser=False, allowed_apps=['documents', 'creme_core'],
                          creatable_models=[Document],
                         )

        create_sc = partial(SetCredentials.objects.create, role=self.role,
                            set_type=SetCredentials.ESET_OWN,
                           )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK,  # Not EntityCredentials.LINK
                 )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE | EntityCredentials.LINK |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK,
                  ctype=ContentType.objects.get_for_model(Document),
                 )

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url = self._buid_addrelated_url(orga)
        self.assertGET403(url)

    def test_add_related_document05(self):
        "View credentials"
        user = self.login(is_superuser=False, allowed_apps=['documents', 'creme_core'],
                          creatable_models=[Document],
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,  # Not EntityCredentials.VIEW
                                      set_type=SetCredentials.ESET_ALL
                                     )

        orga = FakeOrganisation.objects.create(user=self.other_user, name='NERV')
        self.assertTrue(user.has_perm_to_link(orga))
        self.assertFalse(user.has_perm_to_view(orga))
        self.assertGET403(self._buid_addrelated_url(orga))

    def test_add_related_document06(self):
        "The Folder containing all the Documents related to the entity has a too long name."
        user = self.login()

        MAX_LEN = 100
        self.assertEqual(MAX_LEN, Folder._meta.get_field('title').max_length)

        with self.assertNoException():
            entity = FakeOrganisation.objects.create(user=user, name='A' * MAX_LEN)

        self.assertEqual(100, len(str(entity)))

        title = 'Related doc'
        response = self.client.post(
                self._buid_addrelated_url(entity),
                follow=True,
                data={'user': user.id,
                      'title': title,
                      'description': 'Test description',
                      'filedata': self._build_filedata(
                                    'Yes I am the content (DocumentTestCase.test_add_related_document05)'
                                  # )[0],
                                  ),
                }
        )
        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, title=title)
        entity_folder = doc.linked_folder
        self.assertIsNotNone(entity_folder)

        title = entity_folder.title
        self.assertEqual(100, len(title))
        self.assertTrue(title.startswith('{}_AAAAAAA'.format(entity.id)))
        self.assertTrue(title.endswith('…'))

    def test_add_related_document07(self):
        "Collision with Folder titles"
        user = self.login()
        entity = CremeEntity.objects.create(user=user)

        creme_folder = self.get_object_or_fail(Folder, title='Creme')

        # NB : collision with folders created by the view
        create_folder = partial(Folder.objects.create, user=user)
        my_ct_folder = create_folder(title=str(entity.entity_type))
        my_entity_folder = create_folder(title='{}_{}'.format(entity.id, entity))

        title = 'Related doc'
        response = self.client.post(self._buid_addrelated_url(entity), follow=True,
                                    data={'user':         user.pk,
                                          'title':        title,
                                          'description':  'Test description',
                                          'filedata':     self._build_filedata(
                                                                'Yes I am the content '
                                                                '(DocumentTestCase.test_add_related_document06)'
                                                            # )[0],
                                                            ),
                                         }
                                )
        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, title=title)

        entity_folder = doc.linked_folder
        self.assertEqual(my_entity_folder.title, entity_folder.title)
        self.assertNotEqual(my_entity_folder, entity_folder)

        ct_folder = entity_folder.parent_folder
        self.assertIsNotNone(ct_folder)
        self.assertEqual(my_ct_folder.title, ct_folder.title)
        self.assertNotEqual(my_ct_folder, ct_folder)

        self.assertEqual(creme_folder, ct_folder.parent_folder)

    def test_listview(self):
        self.login()

        create_doc = self._create_doc
        doc1 = create_doc('Test doc #1')
        doc2 = create_doc('Test doc #2')

        response = self.assertGET200(Document.get_lv_absolute_url())

        with self.assertNoException():
            docs = response.context['entities'].object_list

        self.assertIn(doc1, docs)
        self.assertIn(doc2, docs)

    def test_delete_category(self):
        "Set to null"
        user = self.login()

        cat = FolderCategory.objects.create(name='Manga')
        folder = Folder.objects.create(user=user, title='One piece', category=cat)

        self.assertPOST200(reverse('creme_config__delete_instance', args=('documents', 'category')),
                           data={'id': cat.pk}
                          )
        self.assertDoesNotExist(cat)

        folder = self.get_object_or_fail(Folder, pk=folder.pk)
        self.assertIsNone(folder.category)

    @skipIfCustomContact
    def test_field_printers01(self):
        "Field printer with FK on Image"
        user = self.login()

        image = self._create_image()
        summary = image.get_entity_summary(user)
        self.assertHTMLEqual('<img class="entity-summary" src="%(url)s" alt="%(name)s" title="%(name)s"/>' % {
                                    'url':  image.get_dl_url(),
                                    'name': image.title,
                                },
                             summary
                            )

        casca = get_contact_model().objects.create(user=user, image=image,
                                                   first_name='Casca', last_name='Mylove',
                                                  )
        self.assertHTMLEqual('''<a onclick="creme.dialogs.image('{}').open();">{}</a>'''.format(
                                    image.get_dl_url(),
                                    summary,
                                ),
                             field_printers_registry.get_html_field_value(casca, 'image', user)
                            )
        self.assertEqual(str(casca.image),
                         field_printers_registry.get_csv_field_value(casca, 'image', user)
                        )

    @skipIfCustomContact
    def test_field_printers02(self):
        "Field printer with FK on Image + credentials"
        Contact = get_contact_model()

        user = self.login(allowed_apps=['creme_core', 'persons', 'documents'])
        other_user = self.other_user

        # self.role.exportable_ctypes = [ContentType.objects.get_for_model(Contact)]
        self.role.exportable_ctypes.set([ContentType.objects.get_for_model(Contact)])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        create_img = self._create_image
        casca_face = create_img(title='Casca face', user=user,       description="Casca's selfie")
        judo_face  = create_img(title='Judo face',  user=other_user, description="Judo's selfie")

        self.assertTrue(other_user.has_perm_to_view(judo_face))
        self.assertFalse(other_user.has_perm_to_view(casca_face))

        create_contact = partial(Contact.objects.create, user=other_user)
        casca = create_contact(first_name='Casca', last_name='Mylove', image=casca_face)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    image=judo_face)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual('''<a onclick="creme.dialogs.image('{}').open();">{}</a>'''.format(
                                judo_face.get_dl_url(),
                                judo_face.get_entity_summary(other_user),
                            ),
                         get_html_val(judo, 'image', other_user)
                        )
        self.assertEqual('<p>Judo&#39;s selfie</p>',
                         get_html_val(judo, 'image__description', other_user)
                        )

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image', other_user))
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image__description', other_user))

    # TODO: (block not yet injected in all apps)
    # def test_orga_block(self):
    #     self.login()
    #     orga = Organisation.objects.create(user=self.user, name='NERV')
    #     response = self.assertGET200(orga.get_absolute_url())
    #     self.assertTemplateUsed(response, 'documents/templatetags/block_linked_docs.html')

    # TODO: complete


@skipIfCustomDocument
@skipIfCustomFolder
class DocumentQuickFormTestCase(_DocumentsTestCase):
    def quickform_data(self, count):
        return {'form-INITIAL_FORMS': '0',
                'form-MAX_NUM_FORMS': '',
                'form-TOTAL_FORMS':   str(count),
               }

    def quickform_data_append(self, data, id, user='', filedata='', folder_id=''):
        return data.update({'form-{}-user'.format(id):          user,
                            'form-{}-filedata'.format(id):      filedata,
                            'form-{}-linked_folder'.format(id): folder_id,
                           }
                          )

    def test_create_legacy(self):
        user = self.login()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = reverse('creme_core__quick_forms', args=(ContentType.objects.get_for_model(Document).id, 1))
        self.assertGET200(url)

        content = 'Yes I am the content (DocumentQuickFormTestCase.test_create_legacy)'
        # file_obj, file_name = self._build_filedata(content)
        file_obj = self._build_filedata(content)
        folder = Folder.objects.all()[0]

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, user=user.pk, filedata=file_obj, folder_id=folder.id)

        self.assertNoFormError(self.client.post(url, follow=True, data=data))

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        # self.assertEqual('upload/documents/' + file_name, doc.filedata.name)
        self.assertEqual('upload/documents/' + file_obj.base_name, doc.filedata.name)
        self.assertEqual('', doc.description)
        self.assertEqual(folder, doc.linked_folder)

        filedata = doc.filedata
        # filedata.open()
        filedata.open('r')
        self.assertEqual([content], filedata.readlines())
        filedata.close()

    def test_create(self):
        user = self.login()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = reverse('creme_core__quick_form', args=(ContentType.objects.get_for_model(Document).id,))
        self.assertGET200(url)

        content = 'Yes I am the content (DocumentQuickFormTestCase.test_create)'
        file_obj = self._build_filedata(content)
        folder = Folder.objects.all()[0]

        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={
                'user':          user.id,
                'filedata':      file_obj,
                'linked_folder': folder.id,
            }

        ))

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual('upload/documents/' + file_obj.base_name, doc.filedata.name)
        self.assertEqual('', doc.description)
        self.assertEqual(folder, doc.linked_folder)

        filedata = doc.filedata
        filedata.open('r')
        self.assertEqual([content], filedata.readlines())
        filedata.close()


@skipIfCustomDocument
@skipIfCustomFolder
# class CSVDocumentQuickWidgetTestCase(_DocumentsTestCase):
class DocumentQuickWidgetTestCase(_DocumentsTestCase):
    # def test_add_from_widget(self):
    def test_add_csv_doc01(self):
        user = self.login()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = reverse('documents__create_document_from_widget')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add_innerpopup.html')

        context = response.context
        self.assertEqual(_('Create a document'), context.get('title'))
        self.assertEqual(_('Save the document'), context.get('submit_label'))

        # ---
        content = 'Content (DocumentQuickWidgetTestCase.test_add_csv_doc)'
        # file_obj, file_name = self._build_filedata(content)
        file_obj= self._build_filedata(content)
        response = self.client.post(url, follow=True,
                                    data={'user':     user.pk,
                                          'filedata': file_obj,
                                         },
                                   )
        self.assertNoFormError(response)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        folder = get_csv_folder_or_create(user)
        # self.assertEqual('upload/documents/' + file_name, doc.filedata.name)
        self.assertEqual('upload/documents/' + file_obj.base_name, doc.filedata.name)
        self.assertEqual('', doc.description)
        self.assertEqual(folder, doc.linked_folder)

        self.assertEqual({'added': [[doc.id, str(doc)]],
                          'value': doc.id,
                         },
                         response.json()
                        )

        filedata = doc.filedata
        # filedata.open()
        filedata.open('r')
        self.assertEqual([content], filedata.readlines())
        filedata.close()

    def test_add_csv_doc02(self):
        "Not super-user"
        self.login(is_superuser=False,
                   allowed_apps=['documents'],
                   creatable_models=[Document],
                  )
        self.assertGET200(reverse('documents__create_document_from_widget'))

    def test_add_csv_doc03(self):
        "Creation permission needed."
        self.login(is_superuser=False,
                   allowed_apps=['documents'],
                   # creatable_models=[Document],
                  )
        self.assertGET403(reverse('documents__create_document_from_widget'))

    @override_settings(ALLOWED_EXTENSIONS=('png', 'pdf'))
    def test_add_image_doc01(self):
        user = self.login()

        url = reverse('documents__create_image_popup')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add_innerpopup.html')

        context = response.context
        self.assertEqual(_('Create an image'), context.get('title'))
        self.assertEqual(_('Save the image'),  context.get('submit_label'))

        # ---
        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
        self.assertTrue(exists(path))

        folder = Folder.objects.all()[0]
        with open(path, 'rb') as image_file:
            response = self.client.post(url, follow=True,
                                        data={'user':   user.pk,
                                              'image':  image_file,
                                              'linked_folder': folder.id,
                                             },
                                       )
        self.assertNoFormError(response)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        title = doc.title
        self.assertTrue(title.startswith('creme_22'))
        self.assertTrue(title.endswith('.png'))

        self.assertEqual('',         doc.description)
        self.assertEqual(folder,     doc.linked_folder)
        self.assertTrue('image/png', doc.mime_type.name)

        self.assertTrue(filecmp.cmp(path, doc.filedata.path))

        self.assertEqual({'added': [[doc.id, str(doc)]],
                          'value': doc.id,
                         },
                         response.json()
                        )

    @override_settings(ALLOWED_EXTENSIONS=('png', 'pdf'))
    def test_add_image_doc02(self):
        "Not an image file"
        user = self.login()

        folder = Folder.objects.all()[0]
        content = '<xml>Content (DocumentQuickWidgetTestCase.test_add_image_doc02)</xml>'
        # file_obj, file_name = self._build_filedata(content, suffix='.xml')
        file_obj = self._build_filedata(content, suffix='.xml')
        response = self.assertPOST200(reverse('documents__create_image_popup'),
                                      follow=True,
                                      data={'user':   user.pk,
                                            'image':  file_obj,
                                            'linked_folder': folder.id,
                                           },
                                     )
        self.assertFormError(response, 'form', 'image',
                             _('Upload a valid image. '
                               'The file you uploaded was either not an image or a corrupted image.'
                              )
                            )

