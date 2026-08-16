from app.extensions import db
from app.models.admin_action import AdminAction

# Human-readable labels for the public log.
ACTION_LABELS = {
    'create_user': 'created an account',
    'reset_password': 'reset a password',
    'activate_user': 'reactivated an account',
    'deactivate_user': 'deactivated an account',
    'grant_admin': 'granted admin rights',
    'revoke_admin': 'revoked admin rights',
    'rename_user': 'changed a display name',
    'remove_bounty': 'removed a bounty',
    'remove_claim': 'removed a claim',
    'invalidate_transaction': 'invalidated a transaction',
}


def record(admin_id, action, target_type=None, target_id=None, target_user_id=None, detail=''):
    """Append an entry to the audit trail.

    `detail` is shown publicly, so never pass user-written text through it
    (bounty titles, claim messages, old display names) — removing that content
    is often the whole point of the action being logged.
    """
    entry = AdminAction(
        admin_user_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_user_id=target_user_id,
        detail=detail or ''
    )
    db.session.add(entry)
    db.session.flush()
    return entry


def label_for(action):
    return ACTION_LABELS.get(action, action.replace('_', ' '))
