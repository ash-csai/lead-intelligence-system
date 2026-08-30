import os, sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path('.').resolve()))
from app import create_app

DB_PATH = Path('lead_system.db')
if not DB_PATH.exists():
    print('Database file lead_system.db not found')
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# create a lead with high interest_level and no interactions
cur.execute("INSERT INTO leads (student_name, phone, city, school_id, coaching_id, course_interest, lead_source, interest_level, notes, status, lead_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" ,
            ('Test User', '9999999999', 'Test City', None, None, 'Test Course', 'Referral', 'high', 'Test note', 'new', 0))
lead_id = cur.lastrowid
conn.commit()
print('created lead_id=', lead_id)

# verify score after insert via app logic
from database.db_connection import get_db
from modules.scoring_engine import recalculate_and_persist_score

# use sqlite connection directly for verification
cur.execute('SELECT lead_score FROM leads WHERE lead_id = ?', (lead_id,))
print('lead_score before recalc=', cur.fetchone()[0])

score = recalculate_and_persist_score(conn, lead_id)
print('recalc score=', score)
cur.execute('SELECT lead_score FROM leads WHERE lead_id = ?', (lead_id,))
print('lead_score after recalc=', cur.fetchone()[0])
conn.commit()

# add a visit interaction and verify score changes
cur.execute('INSERT INTO interactions (lead_id, interaction_type, notes, follow_up_date) VALUES (?, ?, ?, ?)', (lead_id, 'visit', 'Visit note', None))
conn.commit()
print('added visit interaction')

new_score = recalculate_and_persist_score(conn, lead_id)
print('new score after visit=', new_score)
cur.execute('SELECT lead_score FROM leads WHERE lead_id = ?', (lead_id,))
print('lead_score after visit=', cur.fetchone()[0])
conn.close()
