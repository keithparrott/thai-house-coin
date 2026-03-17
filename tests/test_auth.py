from tests.conftest import login


def test_login_page_loads(client):
    resp = client.get('/login')
    assert resp.status_code == 200
    assert b'Welcome Back' in resp.data


def test_login_success(client, admin_user):
    resp = login(client, 'admin', 'password')
    assert resp.status_code == 200
    assert b'Dashboard' in resp.data


def test_login_failure(client, admin_user):
    resp = login(client, 'admin', 'wrong')
    assert b'Invalid username or password' in resp.data


def test_login_inactive_user(client, db):
    from app.models.user import User
    user = User(username='inactive', display_name='Inactive', is_active=False, must_change_password=False)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    resp = login(client, 'inactive', 'password')
    assert b'Invalid username or password' in resp.data


def test_logout(client, admin_user):
    login(client, 'admin', 'password')
    resp = client.get('/logout', follow_redirects=True)
    assert b'logged out' in resp.data


def test_must_change_password_redirect(client, db):
    from app.models.user import User
    user = User(username='newguy', display_name='New Guy', must_change_password=True)
    user.set_password('temppass')
    db.session.add(user)
    db.session.commit()

    login(client, 'newguy', 'temppass')
    resp = client.get('/')
    assert resp.status_code == 302
    assert '/change-password' in resp.location


def test_change_password(client, db):
    from app.models.user import User
    user = User(username='newguy', display_name='New Guy', must_change_password=True)
    user.set_password('temppass')
    db.session.add(user)
    db.session.commit()

    login(client, 'newguy', 'temppass')
    resp = client.post('/change-password', data={
        'current_password': 'temppass',
        'new_password': 'newpass123',
        'confirm_password': 'newpass123'
    }, follow_redirects=True)
    assert b'Password changed' in resp.data


def test_unauthenticated_redirect(client):
    resp = client.get('/')
    assert resp.status_code == 302
    assert '/login' in resp.location
