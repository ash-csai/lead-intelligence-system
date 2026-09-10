import os, sys
from pathlib import Path

sys.path.insert(0, str(Path('.').resolve()))
from app import create_app
from database.db_connection import get_db
from database.models import Lead, Interaction
from modules.scoring_engine import recalculate_and_persist_score

app = create_app()
with app.app_context():
    db = get_db()
    
    # Check if a lead with same phone exists, delete it first to avoid duplicate constraint errors
    existing = db.session.query(Lead).filter(Lead.phone == '9999999999').first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    
    # create a lead with high interest_level and no interactions
    lead = Lead(
        student_name='Test User',
        phone='9999999999',
        city='Test City',
        school_id=None,
        coaching_id=None,
        course_interest='Test Course',
        lead_source='Referral',
        interest_level='high',
        notes='Test note',
        status='new',
        lead_score=0
    )
    db.session.add(lead)
    db.session.commit()
    lead_id = lead.lead_id
    print('created lead_id=', lead_id)

    # verify score after insert via app logic
    print('lead_score before recalc=', lead.lead_score)

    score = recalculate_and_persist_score(db, lead_id)
    print('recalc score=', score)
    db.session.refresh(lead)
    print('lead_score after recalc=', lead.lead_score)

    # add a visit interaction and verify score changes
    interaction = Interaction(
        lead_id=lead_id,
        interaction_type='visit',
        notes='Visit note',
        follow_up_date=None
    )
    db.session.add(interaction)
    db.session.commit()
    print('added visit interaction')

    new_score = recalculate_and_persist_score(db, lead_id)
    print('new score after visit=', new_score)
    db.session.refresh(lead)
    print('lead_score after visit=', lead.lead_score)
