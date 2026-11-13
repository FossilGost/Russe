"""Slovo — local Russian practice, Flask/Jinja + SQLite."""
import json
import os
import random
import re
import secrets
import sqlite3
import unicodedata
import click
from functools import lru_cache
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, session, url_for

from speech import generate_audio
from data.courses import COURSES
from data.alphabet import LETTERS, BY_LETTER
from data.learning import learning_state
from storage import initialize, backup_database
from accounts import install_accounts
from werkzeug.middleware.proxy_fix import ProxyFix
from security import private_directory, create_private_file, rate_limit

ROOT = Path(__file__).parent
CATALOG = json.loads((ROOT / "data/vocabulary.json").read_text(encoding="utf-8"))
WORDS = CATALOG["words"]
ILLUSTRATIONS = json.loads((ROOT / "data/illustrations.json").read_text(encoding="utf-8"))
BY_ID = {w["id"]: w for w in WORDS}
CATEGORIES = sorted({w["category"] for w in WORDS})
MODES = {"mixed": "Parcours mixte", "quiz": "Le bon mot", "dictation": "Dictée sonore", "listen_quiz": "Écoute et choisis", "type": "À toi d’écrire", "copy": "Copie active", "review": "Révision ciblée"}
THEMES = {"light": "Clair", "semi-light": "Semi-clair", "normal": "Normal", "semi-dark": "Semi-sombre", "full-dark": "Sombre intégral"}
VOICES = {"svetlana": "Svetlana · voix naturelle féminine", "dmitry": "Dmitry · voix naturelle masculine", "browser": "Voix du navigateur"}
SPEECH_RATES = {"slow": "Lent · pour décomposer", "normal": "Posé · recommandé", "fast": "Naturel · conversation"}


def normalize(value, strict=False):
    value = unicodedata.normalize("NFC", value.lower()).replace("\u0301", "")
    if not strict:
        value = value.replace("ё", "е")
    return " ".join(re.sub(r"[^\w\s]", "", value).split())


NORMALIZED_WORDS = {normalize(word["ru"]): word for word in WORDS}
WORD_SEARCH = {word["id"]: normalize(word["ru"]+" "+word["fr"]) for word in WORDS}
WORDS_BY_CATEGORY = {category: [word for word in WORDS if word["category"] == category] for category in CATEGORIES}


@lru_cache(maxsize=512)
def asset_version(filename):
    path = ROOT / "static" / filename
    try:
        stat = path.stat()
        return f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
    except OSError:
        return None


def create_app(test_config=None):
    app = Flask(__name__)
    production = os.environ.get("SLOVO_ENV") == "production"
    data_dir = Path(os.environ.get("SLOVO_DATA_DIR", ROOT / "instance"))
    app.config.update(DATABASE=str(data_dir / "slovo.sqlite3"), SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=production,
                      PERMANENT_SESSION_LIFETIME=timedelta(days=7), SESSION_REFRESH_EACH_REQUEST=False,
                      MAX_CONTENT_LENGTH=16384, MAX_FORM_MEMORY_SIZE=16384, MAX_FORM_PARTS=30,
                      SECRET_KEY=os.environ.get("SECRET_KEY"), PRODUCTION=production,
                      ALLOW_REGISTRATION=os.environ.get("ALLOW_REGISTRATION", "1") == "1", PROGRESSION_ENABLED=True,
                      TRUSTED_HOSTS=[host.strip() for host in os.environ.get("SLOVO_HOSTS", "").split(",") if host.strip()] or None)
    if test_config:
        app.config.update(test_config)
    app.jinja_env.auto_reload = app.debug

    @app.url_defaults
    def version_assets(endpoint, values):
        if endpoint == "static" and "filename" in values:
            values.setdefault("v", asset_version(values["filename"]))
    if app.config["PRODUCTION"]:
        app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_NAME="__Host-slovo",
                          SESSION_COOKIE_DOMAIN=None, SESSION_COOKIE_PATH="/", DEBUG=False)
        if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
            raise RuntimeError("Production : définis SECRET_KEY avec au moins 32 caractères aléatoires.")
        if not app.config["TRUSTED_HOSTS"]:
            raise RuntimeError("Production : définis SLOVO_HOSTS avec le nom de domaine autorisé.")
        if any(not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*(?::[0-9]{1,5})?", host)
               for host in app.config["TRUSTED_HOSTS"]):
            raise RuntimeError("Production : seuls des noms d’hôtes exacts sont autorisés.")
    if os.environ.get("SLOVO_PROXY") == "1":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    instance = Path(app.config["DATABASE"]).parent
    private_directory(instance)
    key_path = instance / "secret.key"
    if not app.config["SECRET_KEY"] and not key_path.exists():
        try:
            with os.fdopen(create_private_file(key_path), "wb") as key_file:
                key_file.write(secrets.token_bytes(32))
        except FileExistsError:
            pass  # Another local process created the private key first.
    app.secret_key = app.config["SECRET_KEY"] or key_path.read_bytes()
    if os.name == "posix" and key_path.exists():
        key_path.chmod(0o600)

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"], timeout=15)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys=ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        connection = g.pop("db", None)
        if connection:
            connection.close()

    with app.app_context():
        initialize(db(), app.config["DATABASE"])
    if os.name == "posix":
        Path(app.config["DATABASE"]).chmod(0o600)

    @app.before_request
    def require_secure_transport():
        if app.config["PRODUCTION"] and not request.is_secure and request.endpoint != "health":
            abort(400, "Une connexion HTTPS est requise.")

    install_accounts(app, db)

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
            response.vary.add("Cookie")
        elif response.status_code in (200, 304) and request.args.get("v") == asset_version(request.view_args["filename"]):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        if app.config["PRODUCTION"] and request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if response.status_code == 429 and "Retry-After" not in response.headers:
            response.headers["Retry-After"] = "900"
        return response

    @app.get("/health")
    def health():
        db().execute("SELECT 1").fetchone()
        return {"status": "ok"}

    @app.cli.command("backup")
    @click.argument("destination", type=click.Path(path_type=Path))
    def backup(destination):
        """Create a consistent, verified database backup (all accounts)."""
        try:
            backup_database(db(), destination)
        except (OSError, RuntimeError) as error:
            raise click.ClickException(str(error))
        click.echo("Sauvegarde vérifiée : " + str(destination))

    def user_id():
        return g.user["id"]

    def settings():
        if not g.get("user"):
            return dict(name="Visiteur", theme="normal", sound=0, voice="svetlana", speech_rate="normal", browser_voice="", volume=100, keyboard_open=0)
        if "profile" not in g:
            g.profile = dict(db().execute("SELECT * FROM settings WHERE id=?", (user_id(),)).fetchone())
        return g.profile

    def totals():
        if "totals" not in g:
            g.totals = dict(db().execute("""SELECT COALESCE(SUM(xp),0) xp,COUNT(*) n,
                COALESCE(SUM(correct),0) good, COALESCE(SUM(CASE WHEN day=? THEN xp ELSE 0 END),0) today
                FROM answers WHERE user_id=?""", (date.today().isoformat(),user_id())).fetchone())
        return g.totals

    def stats():
        if not g.get("user"):
            return dict(xp=0, streak=0, level=1)
        if "stats" in g:
            return g.stats
        today = date.today().isoformat()
        total = totals()
        days = {r[0] for r in db().execute("SELECT DISTINCT day FROM answers WHERE user_id=?", (user_id(),))}
        streak, d = 0, date.today()
        if d.isoformat() not in days:
            d -= timedelta(days=1)
        while d.isoformat() in days:
            streak += 1
            d -= timedelta(days=1)
        mastery = db().execute("""SELECT COALESCE(SUM(chain>=3),0) learned,
            COALESCE(SUM(attempts>0 AND due<=?),0) due FROM mastery WHERE user_id=?""",(today,user_id())).fetchone()
        g.stats = dict(xp=total["xp"], count=total["n"], accuracy=round(total["good"] / total["n"] * 100) if total["n"] else 0,
                    level=1+total["xp"]//250, level_progress=total["xp"]%250, streak=streak,
                    today=total["today"], mastered=mastery["learned"], due=mastery["due"],
                    sessions=db().execute("SELECT COUNT(*) FROM runs WHERE user_id=? AND finished IS NOT NULL", (user_id(),)).fetchone()[0])
        return g.stats

    @app.before_request
    def csrf():
        if request.endpoint in ("static", "health"):
            return
        session.setdefault("csrf", secrets.token_hex(24))
        if request.method == "POST" and not secrets.compare_digest(session["csrf"].encode(), request.form.get("csrf", "").encode()):
            abort(400, "Formulaire expiré. Rechargez la page puis réessayez.")

    @app.before_request
    def limit_account_work():
        if not g.get("user") or request.endpoint in (None, "static", "health"):
            return
        policies = {"start": (30, 600), "audio": (240, 60), "letter_audio": (240, 60),
                    "export": (10, 60), "check_answer": (600, 60),
                    "answer": (180, 60), "next_question": (180, 60)}
        if request.method == "POST" or request.endpoint in policies:
            limit, seconds = policies.get(request.endpoint, (120, 60))
            scope = "audio" if request.endpoint in ("audio", "letter_audio") else request.endpoint
            rate_limit(db(), app.secret_key, "account-" + scope, user_id(), limit, seconds)

    @app.context_processor
    def common():
        learning = progression()
        return dict(profile=settings(), stats=stats(), categories=CATEGORIES, modes=MODES,
                    account=g.get("user"), allow_registration=app.config["ALLOW_REGISTRATION"],
                    csrf_token=session.get("csrf"), total_words=len(WORDS), sources=CATALOG["sources"],
                    themes=THEMES, voices=VOICES, speech_rates=SPEECH_RATES, illustrations=ILLUSTRATIONS,
                    learning=learning, practice_mode="mixed" if learning["modes"]["mixed"]["unlocked"] else "quiz")

    def progression():
        if "learning" not in g:
            xp = totals()["xp"] if g.get("user") else 0
            g.learning = learning_state(xp, app.config["PROGRESSION_ENABLED"])
        return g.learning

    @app.get("/")
    def home():
        category_stats = []
        mastery = {r["word_id"]: r["chain"] for r in db().execute("SELECT * FROM mastery WHERE user_id=?", (user_id(),))}
        for category in CATEGORIES:
            group = WORDS_BY_CATEGORY[category]
            category_stats.append(dict(name=category, count=len(group), mastered=sum(mastery.get(w["id"], 0)>=3 for w in group)))
        category_stats.sort(key=lambda group: (progression()["topics"][group["name"]]["xp"], group["name"]))
        active_run = db().execute("SELECT id FROM runs WHERE user_id=? AND finished IS NULL ORDER BY started DESC LIMIT 1", (user_id(),)).fetchone()
        return render_template("home.html", groups=category_stats, active_run=active_run)

    @app.get("/courses")
    def courses():
        completed = {r[0] for r in db().execute("SELECT slug FROM course_progress WHERE user_id=?", (user_id(),))}
        return render_template("courses.html", courses=COURSES, completed=completed)

    @app.get("/courses/<slug>")
    def course(slug):
        index = next((i for i, item in enumerate(COURSES) if item["slug"] == slug), None)
        if index is None:
            abort(404)
        item = COURSES[index]
        examples = [NORMALIZED_WORDS[normalize(value)] for value in item["examples"]]
        return render_template("course.html", course=item, examples=examples,
                               completed=db().execute("SELECT 1 FROM course_progress WHERE user_id=? AND slug=?", (user_id(), slug)).fetchone() is not None,
                               number=index + 1, count=len(COURSES),
                               previous=COURSES[index - 1] if index else None,
                               following=COURSES[index + 1] if index + 1 < len(COURSES) else None)

    @app.post("/courses/<slug>/complete")
    def complete_course(slug):
        if slug not in {item["slug"] for item in COURSES}:
            abort(404)
        db().execute("INSERT OR IGNORE INTO course_progress(user_id,slug,completed) VALUES(?,?,?)",
                     (user_id(), slug, datetime.now().isoformat()))
        db().commit()
        flash("Cours marqué comme terminé. Tu peux le relire à tout moment.")
        return redirect(url_for("course", slug=slug))

    @app.post("/settings/interface")
    def save_interface():
        changes = {}
        for field, minimum, maximum in (("volume", 0, 100), ("keyboard_open", 0, 1), ("strict", 0, 1), ("sound", 0, 1), ("goal", 30, 150), ("length", 5, 20)):
            if field in request.form:
                try:
                    value = int(request.form[field])
                except ValueError:
                    abort(400)
                if not minimum <= value <= maximum:
                    abort(400)
                if field == "goal" and value not in (30, 50, 100, 150) or field == "length" and value not in (5, 10, 15, 20):
                    abort(400)
                changes[field] = value
        for field, choices in (("theme", THEMES), ("voice", VOICES), ("speech_rate", SPEECH_RATES)):
            if field in request.form:
                if request.form[field] not in choices:
                    abort(400)
                changes[field] = request.form[field]
        if "name" in request.form:
            changes["name"] = request.form["name"].strip()[:40] or "Explorateur"
        if "browser_voice" in request.form:
            changes["browser_voice"] = request.form["browser_voice"][:300]
        if not changes:
            abort(400)
        db().execute("""UPDATE settings SET volume=COALESCE(?,volume),keyboard_open=COALESCE(?,keyboard_open),
                     name=COALESCE(?,name),goal=COALESCE(?,goal),length=COALESCE(?,length),strict=COALESCE(?,strict),
                     sound=COALESCE(?,sound),theme=COALESCE(?,theme),voice=COALESCE(?,voice),
                     speech_rate=COALESCE(?,speech_rate),browser_voice=COALESCE(?,browser_voice) WHERE id=?""",
                     tuple(changes.get(field) for field in ("volume", "keyboard_open", "name", "goal", "length", "strict", "sound", "theme", "voice", "speech_rate", "browser_voice")) + (user_id(),))
        db().commit()
        return {"saved": True}

    @app.post("/start")
    def start():
        mode = request.form.get("mode", "mixed")
        category = request.form.get("category", "")
        if mode not in MODES or category and category not in CATEGORIES:
            abort(400)
        learning = progression()
        locks = [learning["modes"][mode]] + ([learning["topics"][category]] if category else [])
        if any(not item["unlocked"] for item in locks):
            required = max(item["xp"] for item in locks)
            flash(f"Ce quiz se débloque à {required} XP. Encore {required-learning['xp']} XP à gagner sur les exercices disponibles !")
            return redirect(url_for("home"))
        unlocked_words = [w for w in WORDS if learning["topics"][w["category"]]["unlocked"]]
        pool = [w for w in unlocked_words if not category or w["category"] == category]
        records = {r["word_id"]: dict(r) for r in db().execute("SELECT * FROM mastery WHERE user_id=?", (user_id(),))}
        if mode == "review":
            pool = [w for w in pool if w["id"] in records and records[w["id"]]["due"] and records[w["id"]]["due"] <= date.today().isoformat()]
            if not pool:
                flash("Aucun mot à réviser pour le moment. Lance un parcours pour commencer !")
                return redirect(url_for("home"))
        random.shuffle(pool)
        # Prioritize due words, then unseen words, then already learned words.
        pool.sort(key=lambda w: 0 if (records.get(w["id"], {}).get("due") or "9999") <= date.today().isoformat() else (1 if not records.get(w["id"], {}).get("attempts") else 2))
        questions = []
        for i, word in enumerate(pool[:settings()["length"]]):
            # Exercise variety is not a security decision; run IDs use secrets.
            kind = random.choice(["quiz", "type"]) if mode in ("mixed", "review") else mode  # nosec B311
            options = []
            if kind == "quiz":
                distractors = [w for w in unlocked_words if w["fr"] != word["fr"]]
                near = [w for w in distractors if w["category"] == word["category"]]
                random.shuffle(near)
                random.shuffle(distractors)
                labels = [word["fr"]]
                for w in near + distractors:
                    if w["fr"] not in labels:
                        labels.append(w["fr"])
                    if len(labels) == 4:
                        break
                random.shuffle(labels)
                options = labels
            elif kind == "listen_quiz":
                near = [w for w in unlocked_words if w["id"] != word["id"] and w["category"] == word["category"]]
                rest = [w for w in unlocked_words if w["id"] != word["id"]]
                random.shuffle(near)
                random.shuffle(rest)
                options = [word["ru"]]
                for candidate in near + rest:
                    if normalize(candidate["ru"]) not in {normalize(label) for label in options}:
                        options.append(candidate["ru"])
                    if len(options) == 4:
                        break
                random.shuffle(options)
            questions.append(dict(word_id=word["id"], kind=kind, options=options))
        run_id = secrets.token_hex(16)
        db().execute("INSERT INTO runs(id,user_id,mode,category,questions,started) VALUES(?,?,?,?,?,?)",
                     (run_id, user_id(), mode, category, json.dumps(questions), datetime.now().isoformat()))
        db().commit()
        session["run_id"] = run_id
        return redirect(url_for("practice"))

    def get_run():
        run = db().execute("SELECT * FROM runs WHERE id=? AND user_id=?", (session.get("run_id", ""), user_id())).fetchone()
        if not run:
            run = db().execute("SELECT * FROM runs WHERE user_id=? AND finished IS NULL ORDER BY started DESC LIMIT 1", (user_id(),)).fetchone()
            if run:
                session["run_id"] = run["id"]
        if not run:
            return None
        return dict(run)

    @app.get("/practice")
    def practice():
        run = get_run()
        if not run:
            return redirect(url_for("home"))
        questions = json.loads(run["questions"])
        if run["finished"]:
            return render_template("result.html", run=run, length=len(questions))
        question = questions[run["position"]]
        word = BY_ID[question["word_id"]]
        feedback = json.loads(run["feedback"]) if run["feedback"] else None
        # Do not expose the answer for translation exercises before submission.
        public_word = dict(word) if question["kind"] != "type" or feedback else {"fr": word["fr"], "category": word["category"]}
        if question["kind"] in ("dictation", "listen_quiz") and not feedback:
            public_word = {"id": word["id"]}
        return render_template("practice.html", run=run, question=question, word=public_word, feedback=feedback, length=len(questions))

    @app.get("/listening/<run_id>/<int:position>/text")
    def listening_text(run_id, position):
        """Supply text only on demand for the explicitly selected browser voice."""
        run = get_run()
        if not run or run["id"] != run_id or run["position"] != position or run["finished"]:
            abort(404)
        question = json.loads(run["questions"])[position]
        if question["kind"] not in ("dictation", "listen_quiz"):
            abort(404)
        return {"text": BY_ID[question["word_id"]]["ru"]}

    @app.post("/check-answer")
    def check_answer():
        """Check a draft without scoring it or revealing the expected answer."""
        run = get_run()
        if not run or run["finished"] or run["feedback"] or request.form.get("run_id") != run["id"] or request.form.get("position") != str(run["position"]):
            return {"matches": False, "stale": True}
        question = json.loads(run["questions"])[run["position"]]
        if question["kind"] not in ("type", "copy", "dictation"):
            return {"matches": False}
        value = request.form.get("answer", "").strip()[:500]
        expected = BY_ID[question["word_id"]]["ru"]
        strict = settings()["strict"]
        response = app.json.response({"matches": bool(value) and normalize(value, strict) == normalize(expected, strict)})
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/answer")
    def answer():
        # A transaction serializes duplicate tabs / repeated submissions.
        db().execute("BEGIN IMMEDIATE")
        run = get_run()
        if not run or run["finished"] or run["feedback"]:
            return redirect(url_for("practice"))
        if request.form.get("position") != str(run["position"]) or request.form.get("run_id") != run["id"]:
            return redirect(url_for("practice"))
        question = json.loads(run["questions"])[run["position"]]
        word = BY_ID[question["word_id"]]
        value = request.form.get("answer", "").strip()[:500]
        if not value and question["kind"] in ("quiz", "listen_quiz"):
            flash("Choisis une réponse ou saisis le mot en russe.")
            return redirect(url_for("practice"))
        correct = value == word["fr"] if question["kind"] == "quiz" else normalize(value, settings()["strict"]) == normalize(word["ru"], settings()["strict"])
        combo = run["combo"]+1 if correct else 0
        if question["kind"] == "listen_quiz":
            correct = value in question["options"] and value == word["ru"]
        xp = (10 if question["kind"] in ("quiz", "listen_quiz") else 15) + min(combo-1, 5)*2 if correct else 0
        old = db().execute("SELECT * FROM mastery WHERE user_id=? AND word_id=?", (user_id(), word["id"])).fetchone()
        chain = (old["chain"] if old else 0)+1 if correct else 0
        due = (date.today()+timedelta(days=[0,1,3,7,14,30][min(chain,5)])).isoformat()
        db().execute("""INSERT INTO mastery(user_id,word_id,attempts,correct,chain,due) VALUES(?,?,1,?,?,?)
            ON CONFLICT(user_id,word_id) DO UPDATE SET attempts=attempts+1, correct=correct+excluded.correct,chain=excluded.chain,due=excluded.due""",
            (user_id(), word["id"], int(correct), chain, due))
        auto_advance = bool(question["kind"] in ("type", "copy", "dictation") and request.form.get("auto_advance") == "1")
        learning = progression()
        unlocks = [stage["title"] for stage in learning["stages"] if learning["xp"] < stage["xp"] <= learning["xp"]+xp]
        unlocks += [MODES[mode] for mode, access in learning["modes"].items() if learning["xp"] < access["xp"] <= learning["xp"]+xp]
        feedback = json.dumps(dict(correct=correct, answer=word["ru"], french=word["fr"], input=value, xp=xp, auto_advance=auto_advance, lost_combo=run["combo"] if not correct else 0, unlocks=unlocks))
        db().execute("INSERT INTO answers(user_id,run_id,position,word_id,correct,xp,day) VALUES(?,?,?,?,?,?,?)",
                     (user_id(),run["id"],run["position"],word["id"],int(correct),xp,date.today().isoformat()))
        db().execute("UPDATE runs SET xp=xp+?,correct=correct+?,combo=?,feedback=? WHERE id=? AND user_id=?", (xp,int(correct),combo,feedback,run["id"],user_id()))
        db().commit()
        g.pop("learning", None)
        g.pop("totals", None)
        g.pop("stats", None)
        return practice() if request.headers.get("X-Slovo-Transition") == "1" else redirect(url_for("practice"))

    @app.post("/next")
    def next_question():
        db().execute("BEGIN IMMEDIATE")
        run = get_run()
        if run and run["feedback"] and request.form.get("position") == str(run["position"]) and request.form.get("run_id") == run["id"]:
            position = run["position"]+1
            finished = datetime.now().isoformat() if position >= len(json.loads(run["questions"])) else None
            db().execute("UPDATE runs SET position=?,feedback=NULL,finished=? WHERE id=? AND user_id=?", (position,finished,run["id"],user_id()))
            db().commit()
        return practice() if request.headers.get("X-Slovo-Transition") == "1" else redirect(url_for("practice"))

    @app.get("/vocabulary")
    def vocabulary():
        query = request.args.get("q", "").strip()[:100]
        category = request.args.get("category", "")
        status = request.args.get("status", "")
        search = normalize(query)
        progress = {r["word_id"]: dict(r) for r in db().execute("SELECT * FROM mastery WHERE user_id=?", (user_id(),))}
        words = []
        for w in WORDS:
            p = progress.get(w["id"], {})
            if category and w["category"] != category:
                continue
            if search and search not in WORD_SEARCH[w["id"]]:
                continue
            if status == "favorites" and not p.get("favorite"):
                continue
            if status == "mastered" and p.get("chain", 0)<3:
                continue
            if status == "review" and not (p.get("due") and p["due"] <= date.today().isoformat()):
                continue
            words.append(dict(**w, progress=p))
        count = len(words)
        pages = max(1, (count+35)//36)
        page = max(1, min(pages, request.args.get("page", 1, type=int) or 1))
        offset = (page-1)*36
        return render_template("vocabulary.html", words=words[offset:offset+36], query=query, category=category,
                               status=status, result_count=count, page=page, pages=pages, offset=offset)

    @app.post("/favorite/<int:word_id>")
    def favorite(word_id):
        if word_id not in BY_ID:
            abort(404)
        db().execute("INSERT INTO mastery(user_id,word_id,favorite) VALUES(?,?,1) ON CONFLICT(user_id,word_id) DO UPDATE SET favorite=1-favorite", (user_id(),word_id))
        db().commit()
        return redirect(url_for("vocabulary", q=request.form.get("q", ""), category=request.form.get("category", ""), status=request.form.get("status", ""), page=request.form.get("page", 1, type=int)))

    @app.get("/progress")
    def progress():
        activity = []
        first = (date.today()-timedelta(days=6)).isoformat()
        daily = dict(db().execute("SELECT day,SUM(xp) FROM answers WHERE user_id=? AND day>=? GROUP BY day", (user_id(),first)))
        for offset in reversed(range(7)):
            day = date.today()-timedelta(days=offset)
            xp = daily.get(day.isoformat(),0)
            activity.append(dict(label=["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"][day.weekday()], xp=xp, date=day.strftime("%d/%m")))
        maximum = max(50, max(a["xp"] for a in activity))
        history = [dict(r) for r in db().execute("SELECT * FROM runs WHERE user_id=? AND finished IS NOT NULL ORDER BY finished DESC LIMIT 10", (user_id(),))]
        for run in history:
            run["length"] = len(json.loads(run["questions"]))
        return render_template("progress.html", activity=activity, maximum=maximum, history=history)

    @app.route("/settings", methods=["GET", "POST"])
    def preferences():
        if request.method == "POST":
            try:
                goal, length = int(request.form.get("goal", 50)), int(request.form.get("length", 10))
            except ValueError:
                abort(400)
            if goal not in (30,50,100,150) or length not in (5,10,15,20):
                abort(400)
            current = settings()
            theme = request.form.get("theme", current["theme"])
            voice = request.form.get("voice", current["voice"])
            speech_rate = request.form.get("speech_rate", current["speech_rate"])
            if theme not in THEMES or voice not in VOICES or speech_rate not in SPEECH_RATES:
                abort(400)
            browser_voice = request.form.get("browser_voice", current["browser_voice"])[:300]
            name = request.form.get("name", "").strip()[:40] or "Explorateur"
            db().execute("UPDATE settings SET name=?,goal=?,length=?,strict=?,sound=?,theme=?,voice=?,speech_rate=?,browser_voice=? WHERE id=?",
                         (name,goal,length,int("strict" in request.form),int("sound" in request.form),theme,voice,speech_rate,browser_voice,user_id()))
            db().commit()
            flash("Tes préférences sont enregistrées.")
            return redirect(url_for("preferences"))
        return render_template("settings.html")

    @app.get("/audio/<int:word_id>")
    @app.get("/audio/sample", defaults={"word_id": None})
    def audio(word_id):
        if word_id is not None and word_id not in BY_ID:
            abort(404)
        profile = settings()
        voice = request.args.get("voice", profile["voice"])
        rate = request.args.get("rate", profile["speech_rate"])
        if voice not in ("svetlana", "dmitry") or rate not in SPEECH_RATES:
            abort(400)
        text = BY_ID[word_id]["ru"] if word_id is not None else "Привет! Как дела? Я люблю русский язык."
        return serve_audio(text, voice, rate)

    def serve_audio(text, voice, rate):
        try:
            path = generate_audio(text, voice, rate, Path(app.config.get("AUDIO_CACHE", instance / "audio")))
        except Exception:
            app.logger.warning("Russian online speech unavailable; browser fallback can be used.")
            return {"error": "La voix naturelle est momentanément indisponible. Essaie la voix du navigateur."}, 503
        return send_file(path, mimetype="audio/mpeg", conditional=True, max_age=86400)

    @app.get("/audio/letter/<letter>/<kind>")
    def letter_audio(letter, kind):
        entry = BY_LETTER.get(letter.upper())
        if entry is None or kind not in ("name", "example"):
            abort(404)
        profile = settings()
        voice = request.args.get("voice", profile["voice"])
        rate = request.args.get("rate", profile["speech_rate"])
        if voice not in ("svetlana", "dmitry") or rate not in SPEECH_RATES:
            abort(400)
        return serve_audio(entry[kind], voice, rate)

    @app.get("/alphabet")
    def alphabet():
        catalog_words = NORMALIZED_WORDS
        letters = []
        for entry in LETTERS:
            word = catalog_words.get(normalize(entry["example"]))
            text = entry["example"]
            # Keep the accent attached to the highlighted letter.
            parts = []
            for char in text:
                if char == "\u0301" and parts:
                    parts[-1]["text"] += char
                else:
                    parts.append(dict(text=char, highlight=char.upper() == entry["letter"]))
            letters.append(dict(entry, parts=parts, word=word))
        return render_template("alphabet.html", letters=letters)

    @app.get("/export")
    def export():
        payload = dict(version=2, exported=datetime.now().isoformat(), username=g.user["username"], settings=settings(), stats=stats(),
                       words=[dict(r) for r in db().execute("SELECT * FROM mastery WHERE user_id=?", (user_id(),))],
                       answers=[dict(r) for r in db().execute("SELECT * FROM answers WHERE user_id=?", (user_id(),))],
                       runs=[dict(r) for r in db().execute("SELECT * FROM runs WHERE user_id=?", (user_id(),))],
                       courses=[dict(r) for r in db().execute("SELECT * FROM course_progress WHERE user_id=?", (user_id(),))])
        return app.response_class(json.dumps(payload,ensure_ascii=False,indent=2),mimetype="application/json",
                                  headers={"Content-Disposition": "attachment; filename=slovo-progression.json"})

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
