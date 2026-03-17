def register_blueprints(app):
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    from app.routes.bounty import bounty_bp
    from app.routes.wallet import wallet_bp
    from app.routes.ledger import ledger_bp
    from app.routes.redemption import redemption_bp
    from app.routes.leaderboard import leaderboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(bounty_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(ledger_bp)
    app.register_blueprint(redemption_bp)
    app.register_blueprint(leaderboard_bp)
