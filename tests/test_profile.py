from tests.conftest import login, mint_thc


def test_profile_page_loads(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.get(f'/user/{regular_user.id}')
    assert resp.status_code == 200
    assert b'Alice' in resp.data
    assert b'@alice' in resp.data


def test_edit_display_name_does_not_change_username(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.post('/user/edit', data={
        'display_name': 'Alicia',
        'email': '',
    }, follow_redirects=True)
    assert b'Profile updated' in resp.data

    from app.models.user import User
    user = User.query.filter_by(username='alice').first()
    assert user is not None, 'username must be unchanged by a display-name edit'
    assert user.display_name == 'Alicia'

    # The old display name must not still be usable as a login, and the
    # username must still work.
    resp = login(client, 'alice', 'password')
    assert b'Invalid username or password' not in resp.data


def test_duplicate_display_name_rejected(client, regular_user, second_user):
    login(client, 'alice', 'password')
    resp = client.post('/user/edit', data={
        'display_name': 'Bob',
        'email': '',
    }, follow_redirects=True)
    assert b'display name is already in use' in resp.data

    from app.models.user import User
    assert User.query.filter_by(username='alice').first().display_name == 'Alice'


def test_duplicate_display_name_is_case_insensitive(client, regular_user, second_user):
    login(client, 'alice', 'password')
    resp = client.post('/user/edit', data={
        'display_name': 'bOb',
        'email': '',
    }, follow_redirects=True)
    assert b'display name is already in use' in resp.data


def test_keeping_own_display_name_is_allowed(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.post('/user/edit', data={
        'display_name': 'Alice',
        'email': 'alice@example.com',
    }, follow_redirects=True)
    assert b'Profile updated' in resp.data

    from app.models.user import User
    assert User.query.filter_by(username='alice').first().email == 'alice@example.com'


def test_duplicate_email_rejected(client, regular_user, second_user):
    login(client, 'alice', 'password')
    client.post('/user/edit', data={'display_name': 'Alice', 'email': 'shared@example.com'})

    login(client, 'bob', 'password')
    resp = client.post('/user/edit', data={
        'display_name': 'Bob',
        'email': 'shared@example.com',
    }, follow_redirects=True)
    assert b'email address is already in use' in resp.data


def test_invalid_email_rejected(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.post('/user/edit', data={
        'display_name': 'Alice',
        'email': 'not-an-email',
    }, follow_redirects=True)
    assert b'valid email address' in resp.data

    from app.models.user import User
    assert User.query.filter_by(username='alice').first().email is None


def test_email_hidden_from_other_users(client, regular_user, second_user):
    login(client, 'alice', 'password')
    client.post('/user/edit', data={'display_name': 'Alice', 'email': 'alice@example.com'})

    resp = client.get(f'/user/{regular_user.id}')
    assert b'alice@example.com' in resp.data, 'own email should be visible to self'

    login(client, 'bob', 'password')
    resp = client.get(f'/user/{regular_user.id}')
    assert resp.status_code == 200
    assert b'alice@example.com' not in resp.data, 'email must not leak to other users'


def test_admin_cannot_create_duplicate_display_name(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    resp = client.post('/admin/create-user', data={
        'username': 'alice2',
        'display_name': 'Alice',
        'password': 'password',
    }, follow_redirects=True)
    assert b'display name is already in use' in resp.data

    from app.models.user import User
    assert User.query.filter_by(username='alice2').first() is None


def test_profile_shows_both_directions_of_relationship(client, regular_user, second_user):
    # Alice posts a bounty Bob completes, so Bob holds 2.0 THC sourced from Alice.
    mint_thc(client, 'alice', 'bob', 2.0)

    login(client, 'bob', 'password')
    resp = client.get(f'/user/{regular_user.id}')
    assert resp.status_code == 200
    assert b'They owe you' in resp.data
    assert b'2.00 THC' in resp.data
