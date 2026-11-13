"""Repeatable local request benchmark on a disposable account/database."""
import argparse
import json
import sqlite3
import statistics
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


def measure(history=10000, samples=12):
    with tempfile.TemporaryDirectory() as folder:
        database = str(Path(folder)/'benchmark.sqlite3')
        app = create_app({'TESTING':True, 'DATABASE':database})
        client = app.test_client()
        client.get('/login')
        with client.session_transaction() as state:
            csrf = state['csrf']
        client.post('/register', data=dict(csrf=csrf,username='benchmark',password='Disposable benchmark password',confirmation='Disposable benchmark password'))
        with client.session_transaction() as state:
            csrf, user = state['csrf'],state['user_id']
        with closing(sqlite3.connect(database)) as db:
            db.executemany('INSERT INTO answers(user_id,run_id,position,word_id,correct,xp,day) VALUES(?,?,?,?,?,?,?)',
                           [(user,'benchmark-history',i,1,1,10,'2026-01-01') for i in range(history)])
            db.commit()
        client.post('/start',data=dict(csrf=csrf,mode='copy'))
        results = {}
        original = sqlite3.connect
        statements = []
        def tracked(*args,**kwargs):
            connection = original(*args,**kwargs)
            connection.set_trace_callback(statements.append)
            return connection
        with patch('app.sqlite3.connect',side_effect=tracked):
            for label,route,headers in [('home','/',{}),('vocabulary','/vocabulary',{}),('practice_full','/practice',{}),('practice_transition','/practice',{'X-Slovo-Transition':'1'})]:
                client.get(route,headers=headers)  # warm template compilation
                durations, counts = [], []
                for _ in range(samples):
                    statements.clear(); start=time.perf_counter()
                    response=client.get(route,headers=headers)
                    assert response.status_code==200
                    durations.append((time.perf_counter()-start)*1000)
                    counts.append(len(statements))
                results[label]=dict(median_ms=round(statistics.median(durations),2),
                                    median_sql=statistics.median(counts),html_bytes=len(response.data))
        return dict(history=history,samples=samples,routes=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=measure()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
