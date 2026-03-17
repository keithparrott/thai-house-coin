from tests.conftest import login


def test_admin_panel_requires_admin(client, regular_user):
    login(client, 'alice', 'password')
    resp = client.get('/admin/', follow_redirects=True)
    assert b'Admin access required' in resp.data


def test_admin_panel_loads(client, admin_user):
    login(client, 'admin', 'password')
    resp = client.get('/admin/')
    assert resp.status_code == 200
    assert b'Users' in resp.data


def test_create_user(client, admin_user):
    login(client, 'admin', 'password')
    resp = client.post('/admin/create-user', data={
        'username': 'newuser',
        'display_name': 'New User',
        'password': 'temppass',
        'is_admin': False,
    }, follow_redirects=True)
    assert b'newuser' in resp.data
    assert b'created' in resp.data


def test_create_duplicate_user(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    resp = client.post('/admin/create-user', data={
        'username': 'alice',
        'display_name': 'Alice 2',
        'password': 'temppass',
    }, follow_redirects=True)
    assert b'already exists' in resp.data


def test_reset_password(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    resp = client.post(f'/admin/reset-password/{regular_user.id}', data={
        'new_password': 'newtemp123'
    }, follow_redirects=True)
    assert b'Password reset' in resp.data


def test_toggle_active(client, admin_user, regular_user):
    login(client, 'admin', 'password')
    resp = client.post(f'/admin/toggle-active/{regular_user.id}', follow_redirects=True)
    assert b'deactivated' in resp.data

    resp = client.post(f'/admin/toggle-active/{regular_user.id}', follow_redirects=True)
    assert b'activated' in resp.data


def test_cannot_deactivate_self(client, admin_user):
    login(client, 'admin', 'password')
    resp = client.post(f'/admin/toggle-active/{admin_user.id}', follow_redirects=True)
    assert b'cannot deactivate yourself' in resp.data
