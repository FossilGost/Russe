"""Unlock enforcement, earned XP, boundaries and persisted existing progress."""
import json
import sqlite3
import unittest
import test_app
from app import BY_ID, CATEGORIES, MODES, create_app
from data.learning import TOPIC_XP, MODE_XP


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_app.SlovoTests()
        self.fixture.setUp()
        self.app = self.fixture.app
        self.app.config['PROGRESSION_ENABLED'] = True
        self.client = self.fixture.client
        self.post = self.fixture.post

    def tearDown(self):
        self.fixture.tearDown()

    def seed_existing_xp(self, xp):
        with self.client.session_transaction() as session:
            user = session['user_id']
        with sqlite3.connect(self.app.config['DATABASE']) as db:
            db.execute("DELETE FROM answers WHERE run_id='historical-fixture' AND user_id=?", (user,))
            db.execute("INSERT INTO answers(user_id,run_id,position,word_id,correct,xp,day) VALUES(?,'historical-fixture',0,1,1,?,'2026-01-01')", (user,xp))

    def test_basics_and_server_side_locks(self):
        self.assertEqual(set(TOPIC_XP), set(CATEGORIES))
        self.assertEqual(set(MODE_XP), set(MODES))
        home = self.client.get('/').get_data(as_text=True)
        self.assertIn('Palier 1', home)
        self.assertIn('Encore <strong>60 XP</strong>', home)
        self.assertIn('quiz-locked', home)
        for mode,category in [('dictation',''),('type',''),('quiz','Les prépositions'),('copy','Les pronoms'),('mixed','Au quotidien')]:
            self.assertIn('Ce quiz se débloque', self.post('/start', mode=mode, category=category).get_data(as_text=True))
            self.assertEqual(self.client.get('/export').get_json()['runs'], [])
        self.post('/start', mode='quiz')
        run = self.fixture.run_record()
        for question in json.loads(run['questions']):
            self.assertEqual(TOPIC_XP[BY_ID[question['word_id']]['category']], 0)
            allowed = {w['fr'] for w in BY_ID.values() if TOPIC_XP[w['category']]==0}
            self.assertTrue(set(question['options']) <= allowed)
        self.assertEqual(self.client.get('/courses').status_code, 200)
        self.assertEqual(self.client.get('/vocabulary').status_code, 200)

    def test_unlocks_are_earned_and_errors_do_not_remove_them(self):
        self.seed_existing_xp(50)
        self.post('/start', mode='quiz')
        run = self.fixture.run_record()
        question = json.loads(run['questions'])[0]
        word = BY_ID[question['word_id']]
        data = dict(run_id=run['id'],position=0,answer=word['fr'])
        response = self.client.post('/answer', data={'csrf':self.fixture.csrf,**data}, headers={'X-Slovo-Transition':'1'})
        self.assertIn('Nouveau contenu débloqué', response.get_data(as_text=True))
        self.assertIn('Écoute et choisis', response.get_data(as_text=True))
        self.post('/answer', **data)  # repeated answers must not multiply XP
        self.assertEqual(self.client.get('/export').get_json()['stats']['xp'], 60)
        self.post('/start', mode='listen_quiz', category='Les personnes')
        run = self.fixture.run_record()
        self.assertEqual(run['mode'], 'listen_quiz')
        question = json.loads(run['questions'])[0]
        wrong = next(v for v in question['options'] if v != BY_ID[question['word_id']]['ru'])
        self.post('/answer',run_id=run['id'],position=0,answer=wrong)
        self.assertEqual(self.client.get('/export').get_json()['stats']['xp'], 60)
        self.post('/start',mode='listen_quiz')
        self.assertEqual(self.fixture.run_record()['mode'],'listen_quiz')

    def test_historical_xp_unlock_boundaries_persist_and_are_per_account(self):
        for mode,threshold in [('listen_quiz',60),('type',150),('mixed',300),('dictation',500)]:
            self.seed_existing_xp(threshold-1)
            before = len(self.client.get('/export').get_json()['runs'])
            self.post('/start',mode=mode)
            self.assertEqual(len(self.client.get('/export').get_json()['runs']), before)
            self.seed_existing_xp(threshold)
            self.post('/start',mode=mode)
            self.assertEqual(self.fixture.run_record()['mode'],mode)
        self.seed_existing_xp(750)
        self.post('/start',mode='dictation',category='Les prépositions')
        self.assertEqual(self.fixture.run_record()['category'],'Les prépositions')
        restarted = create_app({'TESTING':True,'DATABASE':self.app.config['DATABASE']}).test_client()
        restarted.get('/login')
        with restarted.session_transaction() as state:
            token = state['csrf']
        restarted.post('/login',data={'csrf':token,'username':'testeur','password':'Une phrase de test 123'})
        self.assertIn('Tous les quiz sont débloqués',restarted.get('/').get_data(as_text=True))
        self.post('/logout')
        with self.client.session_transaction() as state:
            self.fixture.csrf = state['csrf']
        self.post('/register',username='debutant',password='Une phrase de test 123',confirmation='Une phrase de test 123')
        self.assertIn('Palier 1',self.client.get('/').get_data(as_text=True))
        self.assertEqual(self.client.get('/export').get_json()['stats']['xp'],0)


if __name__ == '__main__':
    unittest.main()
