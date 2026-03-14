-- Institutions table
CREATE TABLE institutions (
    institution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('school','coaching_center')),
    city TEXT,
    contact_person TEXT,
    contact_phone TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leads table
CREATE TABLE leads (
    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    phone TEXT,
    city TEXT,
    school_id INTEGER,
    coaching_id INTEGER,
    course_interest TEXT,
    lead_source TEXT,
    interest_level TEXT,
    lead_score INTEGER DEFAULT 0,
    status TEXT CHECK(status IN (
        'new',
        'contacted',
        'interested',
        'applied',
        'admitted',
        'lost'
    )) DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    FOREIGN KEY (school_id) REFERENCES institutions(institution_id),
    FOREIGN KEY (coaching_id) REFERENCES institutions(institution_id)
);

-- Interactions table
CREATE TABLE interactions (
    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    interaction_type TEXT,
    interaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    next_followup_date DATE,

    FOREIGN KEY (lead_id) REFERENCES leads(lead_id)
);

-- Users table (future expansion)
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    role TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);