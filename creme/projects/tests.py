# -*- coding: utf-8 -*-

from datetime import datetime, date, time

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, SetCredentials
from creme_core.tests.base import CremeTestCase

from persons.models import Contact

from projects.models import *
from projects.constants import *


class ProjectsTestCase(CremeTestCase):
    def login(self, is_superuser=True):
        super(ProjectsTestCase, self).login(is_superuser, allowed_apps=['projects'])

    def setUp(self):
        self.populate('creme_core', 'projects')

    def test_populate(self):
        rtypes = RelationType.objects.filter(pk=REL_SUB_PROJECT_MANAGER)
        self.assertEqual(1, rtypes.count())

        rtype  = rtypes[0]
        get_ct = ContentType.objects.get_for_model
        self.assertEqual([get_ct(Contact)], list(rtype.subject_ctypes.all()))
        self.assertEqual([get_ct(Project)], list(rtype.object_ctypes.all()))

        self.assert_(TaskStatus.objects.exists())
        self.assert_(ProjectStatus.objects.exists())

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/projects/').status_code)

    def create_project(self, name):
        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        response = self.client.post('/projects/project/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         name,
                                            'status':       ProjectStatus.objects.all()[0].id,
                                            'start_date':   '2010-10-11',
                                            'end_date':     '2010-12-31',
                                            'responsibles': manager.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            project = Project.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        return project, manager

    def test_project_createview01(self):
        self.login()

        response = self.client.get('/projects/project/add')
        self.assertEqual(200, response.status_code)

        project, manager = self.create_project('Eva00')
        self.assertEqual(1, Relation.objects.filter(subject_entity=project, type=REL_OBJ_PROJECT_MANAGER, object_entity=manager).count())

    def test_project_createview02(self):
        self.login(is_superuser=False)

        role = self.user.role
        create_sc = SetCredentials.objects.create
        create_sc(role=role,
                  value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE | SetCredentials.CRED_UNLINK, #no CRED_LINK
                  set_type=SetCredentials.ESET_ALL
                 )
        create_sc(role=role,
                  value=SetCredentials.CRED_VIEW | SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                  set_type=SetCredentials.ESET_OWN
                 )
        role.creatable_ctypes = [ContentType.objects.get_for_model(Project)]

        manager = Contact.objects.create(user=self.user, first_name='Gendo', last_name='Ikari')
        self.failIf(manager.can_link(self.user))

        response = self.client.post('/projects/project/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         'Eva00',
                                            'status':       ProjectStatus.objects.all()[0].id,
                                            'start_date':   '2011-10-11',
                                            'end_date':     '2011-12-31',
                                            'responsibles': manager.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            errors = response.context['form'].errors
        except Exception, e:
            self.fail(str(e))

        self.assert_(errors)
        self.assert_('responsibles' in errors)

    def test_project_lisview(self):
        self.login()

        self.create_project('Eva00')
        self.create_project('Eva01')

        self.assertEqual(200, self.client.get('/projects/projects').status_code)

    def test_task_createview01(self):
        self.login()

        project = self.create_project('Eva01')[0]

        url = '/projects/project/%s/task/add' % project.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, follow=True,
                                    data={
                                        'user':     self.user.id,
                                        'title':    'head',
                                        'start':    '2010-10-11',
                                        'end':      '2010-10-30',
                                        'duration': 50,
                                        'tstatus':   TaskStatus.objects.all()[0].id,
                                    })
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(1, tasks.count())

        task1 = tasks[0]
        self.assertEqual(1, task1.order)

        response = self.client.post(url, follow=True,
                                    data={
                                        'user':         self.user.id,
                                        'title':        'torso',
                                        'start':        '2010-10-30',
                                        'end':          '2010-11-20',
                                        'duration':     180,
                                        'tstatus':       TaskStatus.objects.all()[0].id,
                                        'parents_task': task1.id,
                                    })
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        tasks = ProjectTask.objects.filter(project=project)
        self.assertEqual(2, tasks.count())

        tasks2 = filter(lambda t: t.id != task1.id, tasks)
        self.assertEqual(1,          len(tasks2))
        self.assertEqual([task1.id], [t.id for t in tasks2[0].parents_task.all()])

        self.assertEqual(list(tasks), list(project.get_tasks()))
        self.assertEqual(180 + 50,    project.get_expected_duration())

    def test_task_createview02(self): #can be parented with task of an other project
        self.login()

        project01 = self.create_project('Eva01')[0]
        project02 = self.create_project('Eva02')[0]

        task01 = self.create_task(project01, 'Title')
        response = self.client.post('/projects/project/%s/task/add' % project02.id, #follow=True,
                                    data={
                                        'user':         self.user.id,
                                        'title':        'head',
                                        'start':        '2010-10-11',
                                        'end':          '2010-10-30',
                                        'duration':     50,
                                        'tstatus':      TaskStatus.objects.all()[0].id,
                                        'parents_task': task01.id,
                                    })
        self.assertFormError(response, 'form', 'parents_task',
                             [_(u'Select a valid choice. %(value)s is not an available choice.') % {'value': task01.id}]
                            )

    def test_task_editview01(self):
        self.login()

        project = self.create_project('Eva01')[0]
        task = self.create_task(project, 'Title')
        url = '/projects/task/edit/%s' % task.id
        self.assertEqual(200, self.client.get(url).status_code)

        title = 'Head'
        duration = 55
        response = self.client.post(url, follow=True,
                                    data={
                                        'user':     self.user.id,
                                        'title':    title,
                                        'start':    '2011-5-16',
                                        'end':      '2012-6-17',
                                        'duration': duration,
                                        'tstatus':  TaskStatus.objects.all()[0].id,
                                    })
        self.assertNoFormError(response)

        task = ProjectTask.objects.get(pk=task.id) #refresh
        self.assertEqual(title,    task.title)
        self.assertEqual(duration, task.duration)

        start = task.start
        self.assertEqual(2011, start.year)
        self.assertEqual(5,    start.month)
        self.assertEqual(16,   start.day)

        end = task.end
        self.assertEqual(2012, end.year)
        self.assertEqual(6,    end.month)
        self.assertEqual(17,   end.day)

    def test_task_add_parent01(self):
        self.login()

        project = self.create_project('Eva01')[0]
        task01 = self.create_task(project, 'Parent01')
        task02 = self.create_task(project, 'Parent02')
        task03 = self.create_task(project, 'Task')

        url = '/projects/task/%s/parent/add' % task03.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'parents': '%s,%s' % (task01.id, task02.id)})
        self.assertNoFormError(response)
        self.assertEqual(set([task01.id, task02.id]), set(t.id for t in task03.parents_task.all()))

        response = self.client.post('/projects/task/parent/delete', data={'id': task03.id, 'parent_id': task01.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(set([task02.id]), set(t.id for t in task03.parents_task.all()))

        #Error: already parent
        self.assertFormError(self.client.post(url, data={'parents': task02.id}),
                             'form', 'parents',
                             [_(u'Select a valid choice. %(value)s is not an available choice.') % {'value': task02.id}]
                            )

    def test_task_add_parent02(self): #error task that belong to another project
        self.login()

        project01 = self.create_project('Eva01')[0]
        project02 = self.create_project('Eva02')[0]

        task01 = self.create_task(project01, 'Task01')
        task02 = self.create_task(project02, 'Task02')

        response = self.client.post('/projects/task/%s/parent/add' % task02.id,
                                    data={'parents': task01.id}
                                   )
        self.assertFormError(response, 'form', 'parents',
                             [_(u'Select a valid choice. %(value)s is not an available choice.') % {'value': task01.id}]
                            )

    def test_task_add_parent03(self): #cycle error
        self.login()

        project = self.create_project('Eva01')[0]
        task01 = self.create_task(project, 'Task01')
        task02 = self.create_task(project, 'Task02')
        task03 = self.create_task(project, 'Task03')

        self.assertEqual(set([task01.id]), set(t.id for t in task01.get_subtasks()))

        self.assertNoFormError(self.client.post('/projects/task/%s/parent/add' % task02.id, data={'parents': task01.id}))
        self.assertEqual(set([task01.id, task02.id]), set(t.id for t in task01.get_subtasks()))

        self.assertNoFormError(self.client.post('/projects/task/%s/parent/add' % task03.id, data={'parents': task02.id}))
        self.assertEqual(set([task01.id, task02.id, task03.id]), set(t.id for t in task01.get_subtasks()))

        response = self.client.post('/projects/task/%s/parent/add' % task01.id, data={'parents': task03.id})
        self.assertFormError(response, 'form', 'parents',
                             [_(u'Select a valid choice. %(value)s is not an available choice.') % {'value': task03.id}]
                            )

    def create_task(self, project, title):
        response = self.client.post('/projects/project/%s/task/add' % project.id, follow=True,
                                    data={
                                        'user':     self.user.id,
                                        'title':    title,
                                        'start':    '2010-10-11',
                                        'end':      '2010-10-30',
                                        'duration': 50,
                                        'tstatus':  TaskStatus.objects.all()[0].id,
                                    })
        self.assertEqual(200, response.status_code)

        try:
            task = ProjectTask.objects.get(project=project, title=title)
        except Exception, e:
            self.fail(str(e))

        return task

    def test_resource_n_period01(self): #createviews
        self.login()

        project = self.create_project('Eva02')[0]
        task    = self.create_task(project, 'legs')
        self.failIf(task.resources_set.all())

        worker   = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        response = self.client.post('/projects/task/%s/resource/add' % task.id, follow=True,
                                    data={
                                        'user':           self.user.id,
                                        'linked_contact': worker.id,
                                        'hourly_cost':    100,
                                    })
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        resources = list(task.resources_set.all())
        self.assertEqual(1, len(resources))

        resource = resources[0]
        self.failIf(resource.workingperiod_set.all())

        response = self.client.post('/projects/task/%s/period/add' % task.id, follow=True,
                                    data={
                                        'resource':   resource.id,
                                        'start_date': '2010-10-11',
                                        'end_date':   '2010-10-12',
                                        'duration':   8,
                                    })
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertEqual(1, resource.workingperiod_set.count())

        self.assertEqual(8,   task.get_effective_duration())
        self.assertEqual(800, task.get_task_cost()) #8 * 100
        self.assertEqual(-42, task.get_delay()) # 8 - 50
        self.assert_(task.is_alive())

        self.assertEqual(8,   project.get_effective_duration())
        self.assertEqual(800, project.get_project_cost()) #8 * 100
        self.assertEqual(0,   project.get_delay())

    def test_resource_n_period02(self): #editviews
        self.login()

        project  = self.create_project('Eva02')[0]
        task     = self.create_task(project, 'arms')
        worker   = Contact.objects.create(user=self.user, first_name='Yui', last_name='Ikari')
        response = self.client.post('/projects/task/%s/resource/add' % task.id, follow=True,
                                    data={
                                        'user':           self.user.id,
                                        'linked_contact': worker.id,
                                        'hourly_cost':    100,
                                    })
        resource = task.resources_set.all()[0]
        response = self.client.post('/projects/task/%s/period/add' % task.id, follow=True,
                                    data={
                                        'resource':   resource.id,
                                        'start_date': '2010-10-11',
                                        'end_date':   '2010-10-12',
                                        'duration':   8,
                                    })

        response = self.client.get('/projects/resource/edit/%s' % resource.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/projects/resource/edit/%s' % resource.id, follow=True,
                                    data={
                                        'user':           self.user.id,
                                        'linked_contact': worker.id,
                                        'hourly_cost':    200,
                                    })
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)

        resource = Resource.objects.get(pk=resource.id) #refresh
        self.assertEqual(200, resource.hourly_cost)


        wperiods = list(resource.workingperiod_set.all())
        self.assertEqual(1, len(wperiods))

        wperiod = wperiods[0]
        response = self.client.get('/projects/period/edit/%s' % wperiod.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/projects/period/edit/%s' % wperiod.id, follow=True,
                                    data={
                                        'resource':   resource.id,
                                        'start_date': '2010-10-11',
                                        'end_date':   '2010-10-12',
                                        'duration':   10,
                                    })
        self.assertEqual(200, response.status_code)
        self.failIf(response.context['form'].errors)

        wperiod = WorkingPeriod.objects.get(pk=wperiod.id) #refresh
        self.assertEqual(10, wperiod.duration)

    def test_project_close(self):
        self.login()

        project = self.create_project('Eva01')[0]
        self.assert_(not project.is_closed)
        self.assert_(not project.effective_end_date)

        url = '/projects/project/%s/close' % project.id
        self.assertEqual(404, self.client.get(url).status_code)
        self.assertEqual(200, self.client.post(url, follow=True).status_code)

        project = Project.objects.get(pk=project.id) #refresh
        self.assert_(project.is_closed)
        self.assert_(project.effective_end_date)

        delta = datetime.combine(date.today(), time()) - project.effective_end_date
        self.assert_(delta.seconds < 10)

        #already closed
        self.assertEqual(404, self.client.post(url, follow=True).status_code)

    #TODO: test better get_project_cost(), get_effective_duration(), get_delay()
