from django.contrib.auth import get_user_model
from django.urls import reverse

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.persons import get_contact_model

CremeUser = get_user_model()
Contact = get_contact_model()


class CreateTeamTestCase(CremeAPITestCase):
    url_name = 'creme_api__teams-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={})
        self.assertValidationErrors(response, {
            'name': ['required'],
            'teammates': ['required'],
        })

    def test_validation__name_max_length(self):
        data = {'name': "a" * (CremeUser._meta.get_field('username').max_length + 1)}
        response = self.make_request(data=data)
        self.assertValidationError(response, 'name', ['max_length'])

    def test_validation__name_invalid_chars(self):
        data = {'name': "*********"}
        response = self.make_request(data=data)
        self.assertValidationError(response, 'name', ['invalid'])

    def test_validation__teammates(self):
        data = {'name': "TEAM", 'teammates': [9999]}
        response = self.make_request(data=data)
        self.assertValidationError(response, 'teammates', ['does_not_exist'])

    def test_create_team(self):
        user1 = self.factory.user(username="user1")
        user2 = self.factory.user(username="user2")

        data = {'name': "creme-team", 'teammates': [user1.id, user2.id]}
        response = self.make_request(data=data)
        team = CremeUser.objects.get(id=response.data['id'])

        self.assertResponseEqual(response, 201, {
            'id': team.id,
            'teammates': [user1.id, user2.id],
            'name': "creme-team",
        })

        self.assertTrue(team.is_team)
        self.assertEqual(team.username, "creme-team")
        self.assertEqual(team.teammates, {user1.id: user1, user2.id: user2})


class RetrieveTeamTestCase(CremeAPITestCase):
    url_name = 'creme_api__teams-detail'
    method = 'get'

    def test_get_team(self):
        user = self.factory.user()
        team = self.factory.team(teammates=[user])

        response = self.make_request(to=team.id)
        self.assertResponseEqual(response, 200, {
            'id': team.id,
            'teammates': [user.id],
            'name': 'Team #1',
        })


class UpdateTeamTestCase(CremeAPITestCase):
    url_name = 'creme_api__teams-detail'
    method = 'put'

    def test_validation__required(self):
        team = self.factory.team()
        response = self.make_request(to=team.id, data={})
        self.assertValidationErrors(response, {
            'name': ['required'],
            'teammates': ['required'],
        })

    def test_update_team(self):
        user = self.factory.user()
        team = self.factory.team(teammates=[user])

        user2 = self.factory.user(username="user2")
        data = {'name': "Sales", 'teammates': [user2.id]}
        response = self.make_request(to=team.id, data=data)

        self.assertResponseEqual(response, 200, {
            'id': team.id,
            'teammates': [user2.id],
            'name': 'Sales',
        })

        team.refresh_from_db()
        self.assertTrue(team.is_team)
        self.assertEqual(team.username, "Sales")
        self.assertEqual(team.teammates, {user2.id: user2})


class PartialUpdateTeamTestCase(CremeAPITestCase):
    url_name = 'creme_api__teams-detail'
    method = 'patch'

    def test_partial_update_team__name(self):
        user = self.factory.user()
        team = self.factory.team(teammates=[user])

        data = {'name': "Sales"}
        response = self.make_request(to=team.id, data=data)
        self.assertResponseEqual(response, 200, {
            'id': team.id,
            'teammates': [user.id],
            'name': 'Sales',
        })

        team.refresh_from_db()
        self.assertTrue(team.is_team)
        self.assertEqual(team.username, "Sales")
        self.assertEqual(team.teammates, {user.id: user})

    def test_partial_update_team__teammates(self):
        user = self.factory.user()
        team = self.factory.team(teammates=[user])

        # change
        user2 = self.factory.user(username='user2')
        data = {'teammates': [user2.id]}
        response = self.make_request(to=team.id, data=data)
        self.assertResponseEqual(response, 200, {
            'id': team.id,
            'teammates': [user2.id],
            'name': 'Team #1',
        })

        team.refresh_from_db()
        self.assertTrue(team.is_team)
        self.assertEqual(team.username, "Team #1")
        self.assertEqual(team.teammates, {user2.id: user2})

        # empty
        data = {'teammates': []}
        response = self.make_request(to=team.id, data=data)
        self.assertResponseEqual(response, 200, {
            'id': team.id,
            'teammates': [],
            'name': 'Team #1',
        })

        team.refresh_from_db()
        self.assertTrue(team.is_team)
        self.assertEqual(team.username, "Team #1")
        self.assertEqual(team.teammates, {})


class ListTeamTestCase(CremeAPITestCase):
    url_name = 'creme_api__teams-list'
    method = 'get'

    def test_list_teams(self):
        user1 = self.factory.user(username="user1")
        team1 = self.factory.team(name='test1', teammates=[user1])
        user2 = self.factory.user(username="user2")
        team2 = self.factory.team(name='test2', teammates=[user1, user2])
        teams = CremeUser.objects.filter(is_team=True)
        self.assertEqual(teams.count(), 2, teams)

        response = self.make_request()
        self.assertResponseEqual(response, 200, [
            {
                'id': team1.id,
                'teammates': [user1.id],
                'name': 'test1',
            },
            {
                'id': team2.id,
                'teammates': [user1.id, user2.id],
                'name': 'test2',
            },
        ])


class DeleteTeamTestCase(CremeAPITestCase):
    url_name = 'creme_api__teams-delete'
    method = 'post'

    def test_delete(self):
        url = reverse('creme_api__teams-detail', args=[1])
        response = self.client.delete(url, format='json')
        self.assertResponseEqual(response, 405)

    def test_delete_team(self):
        user = self.factory.user()
        team1 = self.factory.team(name='team1')
        team2 = self.factory.team(name='team2')
        contact = self.factory.contact(user=team2)

        data = {'transfer_to': team1.id}
        response = self.make_request(to=team2.id, data=data)
        self.assertResponseEqual(response, 204)

        self.assertFalse(CremeUser.objects.filter(username='team2').exists())
        contact.refresh_from_db()
        self.assertEqual(contact.user, team1)

        data = {'transfer_to': user.id}
        response = self.make_request(to=team1.id, data=data)
        self.assertResponseEqual(response, 204)

        self.assertFalse(CremeUser.objects.filter(username='team1').exists())
        contact.refresh_from_db()
        self.assertEqual(contact.user, user)
