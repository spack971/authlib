from flask import json
from authlib.flask.oauth2.sqla import create_revocation_endpoint
from .oauth2_server import db, User, Client, Token
from .oauth2_server import TestCase
from .oauth2_server import create_authorization_server


RevocationEndpoint = create_revocation_endpoint(db.session, Token)


class RevokeTokenTest(TestCase):
    def prepare_data(self):
        server = create_authorization_server(self.app)
        server.register_revoke_token_endpoint(RevocationEndpoint)

        user = User(username='foo')
        db.session.add(user)
        db.session.commit()
        client = Client(
            user_id=user.id,
            client_id='revoke-client',
            client_secret='revoke-secret',
            default_redirect_uri='http://localhost/authorized',
            scope='profile',
        )
        db.session.add(client)
        db.session.commit()

    def create_token(self):
        token = Token(
            user_id=1,
            client_id='revoke-client',
            token_type='bearer',
            access_token='a1',
            refresh_token='r1',
            scope='profile',
            expires_in=3600,
        )
        db.session.add(token)
        db.session.commit()

    def test_invalid_client(self):
        self.prepare_data()
        rv = self.client.post('/oauth/revoke')
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'invalid_client')

        headers = {'Authorization': 'invalid token_string'}
        rv = self.client.post('/oauth/revoke', headers=headers)
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'invalid_client')

        headers = self.create_basic_header(
            'invalid-client', 'revoke-secret'
        )
        rv = self.client.post('/oauth/revoke', headers=headers)
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'invalid_client')

        headers = self.create_basic_header(
            'revoke-client', 'invalid-secret'
        )
        rv = self.client.post('/oauth/revoke', headers=headers)
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'invalid_client')

    def test_invalid_token(self):
        self.prepare_data()
        headers = self.create_basic_header(
            'revoke-client', 'revoke-secret'
        )
        rv = self.client.post('/oauth/revoke', headers=headers)
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'invalid_request')

        rv = self.client.post('/oauth/revoke', data={
            'token': 'invalid-token',
        }, headers=headers)
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'invalid_request')

        rv = self.client.post('/oauth/revoke', data={
            'token': 'a1',
            'token_type_hint': 'unsupported_token_type',
        }, headers=headers)
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'unsupported_token_type')

        rv = self.client.post('/oauth/revoke', data={
            'token': 'a1',
            'token_type_hint': 'refresh_token',
        }, headers=headers)
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'invalid_request')

    def test_revoke_token_with_hint(self):
        self.prepare_data()
        self.create_token()
        headers = self.create_basic_header(
            'revoke-client', 'revoke-secret'
        )
        rv = self.client.post('/oauth/revoke', data={
            'token': 'a1',
            'token_type_hint': 'access_token',
        }, headers=headers)
        self.assertEqual(rv.status_code, 200)

        rv = self.client.post('/oauth/revoke', data={
            'token': 'a1',
            'token_type_hint': 'access_token',
        }, headers=headers)
        resp = json.loads(rv.data)
        self.assertEqual(resp['error'], 'invalid_request')

    def test_revoke_token_without_hint(self):
        self.prepare_data()
        self.create_token()
        headers = self.create_basic_header(
            'revoke-client', 'revoke-secret'
        )
        rv = self.client.post('/oauth/revoke', data={
            'token': 'a1',
        }, headers=headers)
        self.assertEqual(rv.status_code, 200)
