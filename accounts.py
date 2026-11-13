"""Accounts, revocable sessions, bounded sign-in attempts and operator commands."""
import re
import secrets
import sqlite3
import time

import click
from flask import abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from security import PASSWORD_METHOD, MIN_PASSWORD_LENGTH, password_slot, rate_limit

USERNAME = re.compile(r"[a-z0-9][a-z0-9_.-]{2,39}\Z")


def valid_credentials(username, password):
    return bool(USERNAME.fullmatch(username)) and MIN_PASSWORD_LENGTH <= len(password) <= 128


def install_accounts(app, db):
    dummy_hash = generate_password_hash(secrets.token_urlsafe(32), method=PASSWORD_METHOD)

    def sign_in(user):
        session.clear()
        session.permanent = True
        session.update(user_id=user["id"], auth_version=user["auth_version"],
                       auth_started=int(time.time()), csrf=secrets.token_hex(24))

    def throttle(scope, identity, limit, seconds):
        rate_limit(db(), app.secret_key, scope, identity, limit, seconds)

    @app.before_request
    def identify():
        g.user = None
        # Public assets and the readiness probe never create or refresh sessions.
        if request.endpoint in ("static", "health"):
            return
        user_id = session.get("user_id")
        if user_id:
            user = db().execute("SELECT * FROM users WHERE id=? AND password_hash IS NOT NULL", (user_id,)).fetchone()
            started = session.get("auth_started")
            valid_age = (isinstance(started, int) and 0 <= time.time() - started
                         <= app.permanent_session_lifetime.total_seconds())
            if user and valid_age and user["auth_version"] == session.get("auth_version"):
                g.user = dict(user)
            else:
                session.clear()
        session.setdefault("csrf", secrets.token_hex(24))
        if request.endpoint is None:
            return
        if request.endpoint not in ("login", "register", "static", "health") and not g.user:
            if request.headers.get("X-Slovo-Transition") == "1" or request.endpoint in ("check_answer", "save_interface"):
                return {"error": "Connexion requise. Recharge la page pour te reconnecter."}, 401
            return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("home"))
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()[:200]
            password = request.form.get("password", "")
            throttle("login-ip", request.remote_addr, 50, 900)
            throttle("login-user", username, 10, 900)
            user = db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            candidate = password if len(password) <= 128 else ""
            throttle("password-global", "all", 120, 60)
            with password_slot():
                correct = check_password_hash(user["password_hash"] if user and user["password_hash"] else dummy_hash, candidate)
                # Upgrade old hashes only after verifying the original password.
                if user and user["password_hash"] and correct and not user["password_hash"].startswith(PASSWORD_METHOD + "$"):
                    db().execute("UPDATE users SET password_hash=? WHERE id=? AND password_hash=?",
                                 (generate_password_hash(password, method=PASSWORD_METHOD), user["id"], user["password_hash"]))
                    db().commit()
            if user and user["password_hash"] and correct:
                sign_in(user)
                return redirect(url_for("home"))
            error = "Identifiant ou mot de passe incorrect."
        return render_template("auth.html", registering=False, error=error)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if g.user:
            return redirect(url_for("home"))
        if not app.config["ALLOW_REGISTRATION"]:
            abort(403, "Les inscriptions sont fermées.")
        error = None
        if request.method == "POST":
            throttle("register-ip", request.remote_addr, 10, 3600)
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            if not valid_credentials(username, password):
                error = "Choisis un identifiant de 3 à 40 caractères (a–z, chiffres, point, tiret ou _), et un mot de passe de 15 à 128 caractères."
            elif password != request.form.get("confirmation"):
                error = "Les deux mots de passe ne correspondent pas."
            else:
                try:
                    throttle("password-global", "all", 120, 60)
                    with password_slot():
                        hashed = generate_password_hash(password, method=PASSWORD_METHOD)
                    cursor = db().execute("INSERT INTO users(username,password_hash,created) VALUES(?,?,datetime('now'))",
                                          (username, hashed))
                    db().execute("INSERT INTO settings(id,name) VALUES(?,?)", (cursor.lastrowid, username))
                    db().commit()
                except sqlite3.IntegrityError:
                    db().rollback()
                    error = "Cet identifiant n’est pas disponible."
                else:
                    sign_in(db().execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone())
                    flash("Ton compte est créé. Tes progrès seront enregistrés automatiquement.")
                    return redirect(url_for("home"))
        return render_template("auth.html", registering=True, error=error)

    @app.post("/logout")
    def logout():
        # Incrementing the version also invalidates any copied old signed cookie.
        db().execute("UPDATE users SET auth_version=auth_version+1 WHERE id=?", (g.user["id"],))
        db().commit()
        session.clear()
        return redirect(url_for("login"))

    @app.post("/account/password")
    def change_password():
        throttle("password-user", g.user["id"], 10, 900)
        current = request.form.get("current_password", "")
        password = request.form.get("password", "")
        throttle("password-global", "all", 120, 60)
        with password_slot():
            correct = len(current) <= 128 and check_password_hash(g.user["password_hash"], current)
        if not correct:
            flash("Le mot de passe actuel est incorrect.")
        elif not MIN_PASSWORD_LENGTH <= len(password) <= 128 or password != request.form.get("confirmation"):
            flash("Choisis un mot de passe de 15 à 128 caractères et confirme-le à l’identique.")
        else:
            with password_slot():
                hashed = generate_password_hash(password, method=PASSWORD_METHOD)
            changed = db().execute("UPDATE users SET password_hash=?,auth_version=auth_version+1 WHERE id=? AND auth_version=?",
                                   (hashed, g.user["id"], g.user["auth_version"]))
            if not changed.rowcount:
                db().rollback()
                session.clear()
                return redirect(url_for("login"))
            db().commit()
            sign_in(db().execute("SELECT * FROM users WHERE id=?", (g.user["id"],)).fetchone())
            flash("Mot de passe modifié. Les autres sessions ont été déconnectées.")
        return redirect(url_for("preferences"))

    @app.cli.command("claim-local")
    @click.argument("username")
    @click.password_option(confirmation_prompt=True)
    def claim_local(username, password):
        """Attach the preserved local profile to an operator-created account."""
        username = username.strip().lower()
        if not valid_credentials(username, password):
            raise click.ClickException("Identifiant invalide ou mot de passe trop court (15 caractères minimum).")
        try:
            cursor = db().execute("UPDATE users SET username=?,password_hash=? WHERE id=1 AND username IS NULL",
                                  (username, generate_password_hash(password, method=PASSWORD_METHOD)))
            if not cursor.rowcount:
                raise click.ClickException("Le profil local est déjà rattaché à un compte.")
            db().commit()
        except sqlite3.IntegrityError:
            db().rollback()
            raise click.ClickException("Cet identifiant est déjà utilisé.")
        click.echo("Profil local rattaché. Connecte-toi avec cet identifiant : tes progrès sont conservés.")

    @app.cli.command("reset-password")
    @click.argument("username")
    @click.password_option(confirmation_prompt=True)
    def reset_password(username, password):
        """Operator-only password recovery; never exposed as a public route."""
        if not MIN_PASSWORD_LENGTH <= len(password) <= 128:
            raise click.ClickException("Le mot de passe doit contenir 15 à 128 caractères.")
        cursor = db().execute("UPDATE users SET password_hash=?,auth_version=auth_version+1 WHERE username=?",
                              (generate_password_hash(password, method=PASSWORD_METHOD), username.strip().lower()))
        if not cursor.rowcount:
            raise click.ClickException("Compte introuvable.")
        db().commit()
        click.echo("Mot de passe modifié et sessions révoquées.")
