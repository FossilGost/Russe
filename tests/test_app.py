import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from app import BY_ID, CATALOG, THEMES, WORDS, create_app, normalize
from speech import generate_audio
from data.courses import COURSES
from data.alphabet import LETTERS


class SlovoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": str(Path(self.tmp.name)/"test.sqlite3"), "PROGRESSION_ENABLED": False})
        self.client = self.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as session:
            self.csrf = session["csrf"]
        self.post("/register", username="testeur", password="Une phrase de test 123", confirmation="Une phrase de test 123")
        with self.client.session_transaction() as session:
            self.csrf = session["csrf"]

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, path, **data):
        return self.client.post(path, data={"csrf": self.csrf, **data}, follow_redirects=True)

    def run_record(self):
        import sqlite3
        with self.client.session_transaction() as session:
            run_id = session["run_id"]
        with sqlite3.connect(self.app.config["DATABASE"]) as db:
            db.row_factory = sqlite3.Row
            return dict(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())

    def test_pages_and_search(self):
        for route in ["/", "/vocabulary", "/alphabet", "/progress", "/settings", "/export"]:
            self.assertEqual(self.client.get(route).status_code, 200, route)
        response = self.client.get("/vocabulary?q=pluie")
        self.assertIn("дождь", response.get_data(as_text=True))
        self.assertNotIn("футбо́л", response.get_data(as_text=True))

    def test_courses_cover_existing_themes_and_link_to_practice(self):
        from app import CATEGORIES
        self.assertEqual({c["category"] for c in COURSES if c["category"]}, set(CATEGORIES))
        self.assertEqual(len(COURSES), len({c["slug"] for c in COURSES}))
        index = self.client.get("/courses")
        self.assertEqual(index.status_code, 200)
        index_body = index.get_data(as_text=True)
        for course in COURSES:
            path = "/courses/" + course["slug"]
            self.assertIn(path, index_body)
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            body = response.get_data(as_text=True)
            self.assertIn(course["question"], body)
            self.assertIn(course["answer"], body)
            self.assertIn('data-speech-rate="slow"', body)
            if course["category"]:
                self.assertIn('value="' + course["category"] + '"', body)
                self.post("/start", mode="mixed", category=course["category"])
                questions = json.loads(self.run_record()["questions"])
                self.assertTrue(questions)
                self.assertTrue(all(BY_ID[q["word_id"]]["category"] == course["category"] for q in questions))
        self.assertEqual(self.client.get("/courses/inconnu").status_code, 404)

    def test_catalog_is_curated_and_unique(self):
        self.assertGreater(len(WORDS), 100)
        self.assertEqual(len(WORDS), len({normalize(w["ru"]) for w in WORDS}))
        for w in WORDS:
            self.assertIn(w["source"], CATALOG["sources"])
            self.assertFalse(any("a"<=char.lower()<= "z" for char in w["ru"]), w["ru"])
        self.assertFalse(any("Tome" in s or "Cours .pdf" in s for s in CATALOG["sources"].values()))

    def test_catalog_extension_preserves_existing_ids_and_excludes_personal_work(self):
        import hashlib
        identities = json.dumps([(w["id"], w["ru"]) for w in WORDS[:164]], ensure_ascii=False)
        self.assertEqual(hashlib.sha256(identities.encode()).hexdigest(),
                         "03abf0b20d4e0039f0c761fbbbc5b1857f9d052d7507adc613c6f097754a253f")
        self.assertEqual([w["id"] for w in WORDS], list(range(1, len(WORDS)+1)))
        self.assertFalse(any("Texte_russe" in source or "Упражниние" in source
                             for source in CATALOG["sources"].values()))
        self.assertTrue({"devoirs3", "etre_avoir", "possessifs_genre", "lecon2_revision"}
                        <= {w["source"] for w in WORDS[164:]})

    def test_new_course_content_can_be_studied_in_every_mode(self):
        body = self.client.get("/vocabulary").get_data(as_text=True)
        self.assertIn('id="course-notes"', body)
        self.assertIn("Ты готов?", body)
        self.assertNotIn("Ты готовит?", body)
        for category in ("Être au présent", "Avoir au présent", "Phrases et intonation", "Les possessifs", "Les prépositions"):
            for mode in ("quiz", "type", "copy", "mixed"):
                self.assertEqual(self.post("/start", mode=mode, category=category).status_code, 200)
                run = self.run_record()
                questions = json.loads(run["questions"])
                self.assertTrue(all(BY_ID[q["word_id"]]["category"] == category for q in questions))
                question = questions[0]
                word = BY_ID[question["word_id"]]
                answer = word["fr"] if question["kind"] == "quiz" else word["ru"]
                response = self.post("/answer", answer=answer, run_id=run["id"], position=0)
                self.assertEqual(self.run_record()["correct"], 1)
                self.assertIn('data-speech-rate="slow"', response.get_data(as_text=True))

    def test_normalization_preserves_russian_letters(self):
        self.assertEqual(normalize("  КО́ФЕ! "), normalize("кофе"))
        self.assertEqual(normalize("моё"), normalize("мое"))
        self.assertNotEqual(normalize("моё", True), normalize("мое", True))
        self.assertNotEqual(normalize("мой"), normalize("мои"))

    def test_listening_hides_hints_and_reveals_illustrated_correction(self):
        for mode in ("dictation", "listen_quiz"):
            body = self.post("/start", mode=mode).get_data(as_text=True)
            run = self.run_record()
            word = BY_ID[json.loads(run["questions"])[0]["word_id"]]
            self.assertNotIn('class="question-word"', body)
            self.assertNotIn('class="word-illustration"', body)
            self.assertNotIn('data-speak="'+word["ru"]+'"', body)
            self.assertIn('data-auto-listen="1"', body)
            self.assertIn('data-speech-rate="slow"', body)
            path = f'/listening/{run["id"]}/0/text'
            self.assertEqual(self.client.get(path).get_json(), {"text":word["ru"]})
            self.assertEqual(self.client.get('/listening/other/0/text').status_code, 404)
            self.assertEqual(self.client.get(f'/listening/{run["id"]}/1/text').status_code, 404)
            data = dict(run_id=run["id"], position=0, answer=normalize(word["ru"]))
            match = self.post('/check-answer', **data).get_json()
            self.assertEqual(match['matches'], mode == 'dictation')
            # Empty dictation is an unknown answer; wrong QCM is scored once.
            answer = '' if mode=='dictation' else next(v for v in json.loads(run['questions'])[0]['options'] if v != word['ru'])
            body = self.post('/answer', run_id=run['id'], position=0, answer=answer).get_data(as_text=True)
            self.assertEqual(self.run_record()['correct'], 0)
            self.assertIn('class="word-illustration"', body)
            self.assertIn('data-auto-speak=', body)
            self.assertIn(word['fr'], body)
            self.post('/next', run_id=run['id'], position=0)
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_all_illustrations_exist_and_are_local_valid_svg(self):
        import xml.etree.ElementTree as ET
        from app import ILLUSTRATIONS, ROOT
        self.assertEqual(set(ILLUSTRATIONS), {str(w['id']) for w in WORDS})
        for word in WORDS:
            path = ROOT / 'static' / 'illustrations' / f'{word["id"]}.svg'
            tree = ET.fromstring(path.read_text(encoding='utf-8'))
            self.assertEqual(tree.attrib['viewBox'], '0 0 320 160')
            self.assertFalse(any(el.tag.endswith('script') or el.tag.endswith('image') for el in tree.iter()))
        body = self.client.get('/vocabulary').get_data(as_text=True)
        self.assertEqual(body.count('class="word-illustration"'), 36)

    def test_vocabulary_pagination_covers_every_word_and_preserves_filters(self):
        import re
        ids = []
        for page in range(1,10):
            body = self.client.get(f'/vocabulary?page={page}').get_data(as_text=True)
            current = [int(value) for value in re.findall(r'illustrations/(\d+)\.svg',body)]
            self.assertLessEqual(len(current),36)
            if page<=9: ids.extend(current)
        # Page 9 clamps to the final page, which is page 9 for this catalog.
        self.assertEqual(ids,[word['id'] for word in WORDS])
        filtered = self.client.get('/vocabulary?category=Les+possessifs&page=2').get_data(as_text=True)
        self.assertIn('category=Les+possessifs',filtered)
        self.assertNotIn('illustrations/1.svg',filtered)
        self.assertIn('Page 1',self.client.get('/vocabulary?page=invalid').get_data(as_text=True))

    def test_practice_fragments_and_static_cache_remain_private_and_fresh(self):
        import re
        self.post('/start',mode='copy')
        full = self.client.get('/practice').get_data(as_text=True)
        response = self.client.get('/practice',headers={'X-Slovo-Transition':'1'})
        fragment = response.get_data(as_text=True)
        self.assertNotIn('<header',fragment)
        self.assertNotIn('<script',fragment)
        for content in ('class="practice-card"','class="top-stats"','id="main"','name="csrf"'):
            self.assertIn(content,fragment)
        self.assertLess(len(fragment),len(full)*.75)
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        asset = re.search(r'href="([^"]*style.css\?v=[^"]+)"',full).group(1)
        with self.client.get(asset) as response:
            self.assertIn('immutable',response.headers['Cache-Control'])
            self.assertNotIn('Set-Cookie',response.headers)
        with self.client.get('/static/style.css?v=outdated') as response:
            self.assertNotIn('immutable',response.headers['Cache-Control'])

    def test_every_mode_scores_and_finishes_without_duplicates(self):
        self.post("/settings", name="Test", goal=50, length=5)
        for mode in ["quiz", "type", "copy", "mixed", "dictation", "listen_quiz"]:
            self.assertEqual(self.post("/start", mode=mode).status_code, 200)
            for index in range(5):
                run = self.run_record()
                q = json.loads(run["questions"])[index]
                word = BY_ID[q["word_id"]]
                if q["kind"] == "quiz":
                    self.assertEqual(len(set(q["options"])), 4)
                    self.assertEqual(q["options"].count(word["fr"]), 1)
                if q["kind"] == "listen_quiz":
                    self.assertEqual(len({normalize(option) for option in q["options"]}), 4)
                    self.assertEqual(q["options"].count(word["ru"]), 1)
                answer = word["fr"] if q["kind"] == "quiz" else (word["ru"] if q["kind"] == "listen_quiz" else normalize(word["ru"], True))
                data = dict(answer=answer, run_id=run["id"], position=index)
                self.assertEqual(self.post("/answer", **data).status_code, 200)
                scored = self.run_record()
                self.assertEqual(scored["correct"], index+1)
                self.post("/answer", **data)
                self.assertEqual(self.run_record()["xp"], scored["xp"])
                correction = self.client.get("/practice").get_data(as_text=True)
                self.assertIn("Bien joué", correction)
                self.assertIn('data-auto-speak=', correction)
                self.assertIn('data-speak="'+word["ru"]+'"', correction)
                self.post("/next", run_id=run["id"], position=index)
                self.post("/next", run_id=run["id"], position=index)
                self.assertEqual(self.run_record()["position"], index+1)
            self.assertIsNotNone(self.run_record()["finished"])
            self.assertIn("Sans faute", self.client.get("/practice").get_data(as_text=True))
        self.assertEqual(self.client.get("/progress").status_code, 200)

    def test_combo_reward_and_interruption_keep_earned_xp(self):
        self.post("/start", mode="quiz")
        for index in range(2):
            run = self.run_record()
            word = BY_ID[json.loads(run["questions"])[index]["word_id"]]
            response = self.post("/answer", answer=word["fr"], run_id=run["id"], position=index)
            self.assertIn(f'data-feedback-id="{run["id"]}:{index}"', response.get_data(as_text=True))
            self.post("/next", run_id=run["id"], position=index)
        self.assertIn("Bonus +2 XP", response.get_data(as_text=True))
        earned = self.run_record()["xp"]
        response = self.post("/answer", answer="wrong", run_id=run["id"], position=2)
        self.assertIn("Série de 2 interrompue", response.get_data(as_text=True))
        run = self.run_record()
        self.assertEqual(run["combo"], 0)
        self.assertEqual(run["xp"], earned)
        self.assertEqual(json.loads(run["feedback"])["lost_combo"], 2)

    def test_review_and_answer_not_exposed(self):
        self.assertIn("Aucun mot", self.post("/start", mode="review").get_data(as_text=True))
        self.post("/start", mode="type")
        run = self.run_record()
        word = BY_ID[json.loads(run["questions"])[0]["word_id"]]
        body = self.client.get("/practice").get_data(as_text=True)
        self.assertNotIn('data-speak="'+word["ru"]+'"', body)
        self.post("/answer", answer="неправильно", run_id=run["id"], position=0)
        correction = self.client.get("/practice").get_data(as_text=True)
        self.assertIn('data-auto-speak=', correction)
        self.assertIn('data-speak="'+word["ru"]+'"', correction)
        review = self.post("/start", mode="review")
        self.assertEqual(review.status_code, 200)
        questions = json.loads(self.run_record()["questions"])
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["word_id"], word["id"])

    def test_csrf_settings_favorites_and_stale_form(self):
        self.assertEqual(self.client.post("/start", data={"mode":"quiz"}).status_code, 400)
        self.assertEqual(self.post("/settings", goal=9999, length=10).status_code, 400)
        self.post("/settings", name="<script>alert(1)</script>", goal=100, length=5, strict="on")
        self.assertIn("&lt;script&gt;", self.client.get("/").get_data(as_text=True))
        self.post("/favorite/1")
        self.assertIn("дом", self.client.get("/vocabulary?status=favorites").get_data(as_text=True))
        self.post("/favorite/1")
        self.assertIn("Aucun mot", self.client.get("/vocabulary?status=favorites").get_data(as_text=True))
        self.post("/start", mode="quiz")
        run = self.run_record()
        self.post("/answer", run_id="old", position=0, answer="oops")
        self.assertEqual(self.run_record()["correct"], 0)
        exported = self.client.get("/export").get_json()
        self.assertEqual(exported["settings"]["goal"], 100)
        self.assertEqual(exported["settings"]["strict"], 1)

    def test_themes_and_voice_preferences_survive_reload(self):
        for theme in THEMES:
            response = self.post("/settings", name="Test", goal=50, length=10,
                                 theme=theme, voice="dmitry", speech_rate="slow", browser_voice="Russian voice")
            self.assertEqual(response.status_code, 200)
            self.assertIn(f'data-theme="{theme}"', response.get_data(as_text=True))
            for route in ("/", "/vocabulary", "/alphabet", "/progress"):
                self.assertIn(f'data-theme="{theme}"', self.client.get(route).get_data(as_text=True))
        self.assertEqual(self.post("/settings", goal=50, length=10, theme="invalid").status_code, 400)
        self.assertEqual(self.post("/settings", goal=50, length=10, voice="invalid").status_code, 400)
        exported = self.client.get("/export").get_json()["settings"]
        self.assertEqual(exported["voice"], "dmitry")
        self.assertEqual(exported["speech_rate"], "slow")
        self.assertEqual(exported["browser_voice"], "Russian voice")

    def test_partial_preferences_save_immediately_and_preserve_other_values(self):
        import sqlite3
        from contextlib import closing
        initial = self.client.get('/export').get_json()['settings']
        values = dict(name='Camille', goal=100, length=15, strict=1, sound=0,
                      theme='full-dark', voice='dmitry', speech_rate='slow', browser_voice='Russian A')
        expected = dict(initial)
        for field,value in values.items():
            response = self.post('/settings/interface', **{field:value})
            self.assertEqual(response.get_json(), {'saved':True})
            expected[field] = value
            with closing(sqlite3.connect(self.app.config['DATABASE'])) as connection:
                connection.row_factory = sqlite3.Row
                stored = dict(connection.execute('SELECT * FROM settings WHERE id=?', (initial['id'],)).fetchone())
            self.assertEqual(stored, expected)
        self.assertIn('data-theme="full-dark"', self.client.get('/settings').get_data(as_text=True))
        self.post('/settings/interface', strict=0, sound=1, browser_voice='')
        saved = self.client.get('/export').get_json()['settings']
        self.assertEqual((saved['strict'],saved['sound'],saved['browser_voice']), (0,1,''))
        for values in [dict(goal=31),dict(length=6),dict(strict=2),dict(sound='on'),dict(theme='bad'),dict(voice='bad'),dict(speech_rate='bad'),dict(name='Changed',goal=999)]:
            response = self.post('/settings/interface', **values)
            self.assertEqual(response.status_code,400)
        self.assertEqual(self.client.get('/export').get_json()['settings']['name'], 'Camille')

    def test_logout_is_in_header_and_settings_are_automatic(self):
        from html.parser import HTMLParser
        class HeaderForms(HTMLParser):
            def __init__(self):
                super().__init__(); self.header=False; self.logout=False; self.csrf=False
            def handle_starttag(self,tag,attributes):
                attrs=dict(attributes)
                if tag=='header': self.header=True
                if self.header and tag=='form' and attrs.get('action')=='/logout':
                    self.logout=attrs.get('method')=='post'
                if self.header and tag=='input' and attrs.get('name')=='csrf': self.csrf=True
            def handle_endtag(self,tag):
                if tag=='header': self.header=False
        body = self.client.get('/settings').get_data(as_text=True)
        parser = HeaderForms(); parser.feed(body)
        self.assertTrue(parser.logout and parser.csrf)
        self.assertIn('id="settings-save-status"',body)
        self.assertIn('data-autosave="1"',body)
        self.assertNotIn('Enregistrer mes préférences',body)
        self.assertNotIn('puis enregistre',body)

    def test_live_writing_check_does_not_score_or_reveal_answer(self):
        self.post("/start", mode="type")
        run = self.run_record()
        word = BY_ID[json.loads(run["questions"])[0]["word_id"]]
        data = dict(run_id=run["id"], position=0)
        for answer, matches in [("", False), ("неправильно", False), (normalize(word["ru"], True), True)]:
            response = self.post("/check-answer", answer=answer, **data)
            self.assertEqual(response.get_json(), {"matches": matches})
        self.assertEqual(self.run_record()["xp"], 0)
        self.assertIsNone(self.run_record()["feedback"])
        self.post("/answer", answer=word["ru"], auto_advance=1, **data)
        self.assertIn('data-auto-next="1"', self.client.get("/practice").get_data(as_text=True))
        self.assertTrue(self.post("/check-answer", answer=word["ru"], **data).get_json()["stale"])

    def test_empty_enter_answer_is_corrected_spoken_and_can_advance(self):
        self.post("/start", mode="copy")
        run = self.run_record()
        word = BY_ID[json.loads(run["questions"])[0]["word_id"]]
        response = self.post("/answer", answer="", run_id=run["id"], position=0, auto_advance=1)
        body = response.get_data(as_text=True)
        self.assertIn("Je ne sais pas", body)
        self.assertIn('data-speak="'+word["ru"]+'"', body)
        self.assertIn('data-auto-next="1"', body)
        self.assertEqual(self.run_record()["correct"], 0)
        self.assertEqual(self.run_record()["xp"], 0)
        self.post("/next", run_id=run["id"], position=0)
        self.assertEqual(self.run_record()["position"], 1)
        self.assertIn('id="russian-input"', self.client.get("/practice").get_data(as_text=True))

    def test_seamless_session_returns_each_view_without_redirects(self):
        self.post("/settings", name="Test", goal=50, length=5)
        self.post("/start", mode="copy")
        for position in range(5):
            run = self.run_record()
            word = BY_ID[json.loads(run["questions"])[position]["word_id"]]
            data = dict(csrf=self.csrf, run_id=run["id"], position=position, answer=word["ru"], auto_advance="1")
            response = self.client.post("/answer", data=data, headers={"X-Slovo-Transition": "1"})
            self.assertEqual(response.status_code, 200)
            self.assertIn('data-auto-next="1"', response.get_data(as_text=True))
            response = self.client.post("/next", data=data, headers={"X-Slovo-Transition": "1"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.run_record()["position"], position+1)
            self.assertIn('class="result-card"' if position == 4 else 'id="russian-input"',
                          response.get_data(as_text=True))
        self.assertEqual(self.run_record()["correct"], 5)

    def test_existing_database_is_migrated_without_data_loss(self):
        import sqlite3
        old_path = Path(self.tmp.name) / "old.sqlite3"
        with sqlite3.connect(old_path) as db:
            db.executescript("""CREATE TABLE settings(id INTEGER PRIMARY KEY,name TEXT,goal INTEGER,
                length INTEGER,strict INTEGER,sound INTEGER);
                INSERT INTO settings VALUES(1,'Ancien profil',100,5,1,0);
                CREATE TABLE mastery(word_id INTEGER PRIMARY KEY,attempts INTEGER DEFAULT 0,
                correct INTEGER DEFAULT 0,chain INTEGER DEFAULT 0,due TEXT,favorite INTEGER DEFAULT 0);
                INSERT INTO mastery(word_id,attempts,correct,chain,favorite) VALUES(1,3,3,3,1);""")
        db.close()
        app = create_app({"TESTING":True,"DATABASE":str(old_path)})
        client = app.test_client()
        self.assertEqual(client.get("/export").status_code, 302)
        result = app.test_cli_runner().invoke(args=["claim-local", "ancien"], input="Mon ancien mot de passe\nMon ancien mot de passe\n")
        self.assertEqual(result.exit_code, 0, result.output)
        client.get("/login")
        with client.session_transaction() as state:
            token = state["csrf"]
        client.post("/login", data={"csrf": token, "username": "ancien", "password": "Mon ancien mot de passe"})
        profile = client.get("/export").get_json()
        self.assertEqual(profile["settings"]["name"], "Ancien profil")
        self.assertEqual(profile["settings"]["goal"], 100)
        self.assertEqual(profile["settings"]["theme"], "normal")
        self.assertEqual(profile["words"][0]["chain"], 3)
        self.assertEqual(profile["words"][0]["favorite"], 1)
        self.assertEqual(len(list(Path(self.tmp.name).glob("old.pre-accounts-*.sqlite3"))), 1)
        create_app({"TESTING":True,"DATABASE":str(old_path)})  # migration is repeatable

    def test_alphabet_letter_and_word_audio(self):
        from html.parser import HTMLParser

        class Buttons(HTMLParser):
            def __init__(self):
                super().__init__()
                self.audio = []

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == "button" and "data-speak" in attributes:
                    self.audio.append(attributes)

        self.assertEqual(len(LETTERS), 33)
        self.assertEqual(len({item["letter"] for item in LETTERS}), 33)
        body = self.client.get("/alphabet").get_data(as_text=True)
        parser = Buttons()
        parser.feed(body)
        self.assertEqual(len(parser.audio), 33 * 4)
        self.assertEqual(sum(b.get("data-speech-rate") == "slow" for b in parser.audio), 66)
        self.assertIn("Ce signe ne se prononce pas seul.", body)
        fixture = Path(self.tmp.name) / "letters.mp3"
        fixture.write_bytes(b"ID3-letter-fixture")
        with patch("app.generate_audio", return_value=fixture) as generate:
            for item in LETTERS:
                self.assertIn(item["letter"].lower(), item["example"].lower())
                for kind in ("name", "example"):
                    with self.client.get(f'/audio/letter/{item["letter"]}/{kind}?voice=dmitry&rate=slow') as response:
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.mimetype, "audio/mpeg")
                        self.assertEqual(generate.call_args.args[:3], (item[kind], "dmitry", "slow"))
            for button in parser.audio:
                with self.client.get(button["data-audio-url"]) as response:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(generate.call_args.args[0], button["data-speak"])
        for path in ("/audio/letter/A/name", "/audio/letter/Б/invalid"):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get("/audio/letter/Б/name?voice=invalid").status_code, 400)
        self.assertEqual(self.client.get("/audio/letter/Б/name?rate=invalid").status_code, 400)
        with patch("app.generate_audio", side_effect=RuntimeError("offline")):
            self.assertEqual(self.client.get("/audio/letter/Б/name").status_code, 503)

    def test_audio_routes_validate_and_handle_service_failure(self):
        self.assertEqual(self.client.get("/audio/999999").status_code, 404)
        self.assertEqual(self.client.get("/audio/1?voice=invalid").status_code, 400)
        self.assertEqual(self.client.get("/audio/sample?rate=invalid").status_code, 400)
        fixture = Path(self.tmp.name) / "sample.mp3"
        fixture.write_bytes(b"ID3-audio-fixture")
        with patch("app.generate_audio", return_value=fixture) as generate:
            with self.client.get("/audio/1?voice=dmitry&rate=slow") as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "audio/mpeg")
                self.assertEqual(response.data, b"ID3-audio-fixture")
            self.assertEqual(generate.call_args.args[:3], (BY_ID[1]["ru"], "dmitry", "slow"))
        with patch("app.generate_audio", side_effect=RuntimeError("offline")):
            self.assertEqual(self.client.get("/audio/sample").status_code, 503)

    def test_speech_cache_is_complete_and_reused(self):
        cache = Path(self.tmp.name) / "audio"
        async def save(temporary):
            Path(temporary).write_bytes(b"ID3-generated")
        with patch("edge_tts.Communicate") as communicate:
            communicate.return_value.save.side_effect = save
            one = generate_audio("ко́фе", "svetlana", "normal", cache)
            two = generate_audio("кофе", "svetlana", "normal", cache)
            self.assertEqual(one, two)
            self.assertEqual(one.read_bytes(), b"ID3-generated")
            communicate.assert_called_once_with("кофе", "ru-RU-SvetlanaNeural", rate="-10%")
        self.assertEqual(len(list(cache.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
