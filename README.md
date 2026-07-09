
# Lead Intelligence System (LIS)

> A modular Lead Intelligence & CRM platform built with **Python**, **Flask**, and **SQLite** to help educational institutions manage enquiries, follow-ups, interactions, and admissions through an intelligent lead pipeline.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue)
![Bootstrap](https://img.shields.io/badge/UI-Bootstrap-purple)
![Status](https://img.shields.io/badge/Project-Active-success)

---

## Overview

Lead Intelligence System (LIS) was designed as a lightweight yet scalable CRM for university marketing and admissions teams.

Instead of acting as a simple contact manager, LIS focuses on the **complete lead lifecycle**—from the first enquiry to admission—while providing insights through lead scoring, follow-up tracking, interaction history, institutional relationships, and dashboard analytics.

The project has been intentionally structured so it can grow into a larger ERP or AI-assisted admissions platform.

---

# Key Features

## Lead Management
- Add, view and search leads
- Edit lead details
- Lead status pipeline
- Duplicate detection
- Lead validation

## CRM Pipeline
- New
- Contacted
- Interested
- Applied
- Admitted
- Lost

## Interaction Tracking
- Record calls, meetings, emails, visits and WhatsApp conversations
- Maintain complete interaction timeline
- Follow-up scheduling

## Lead Intelligence
- Rule-based lead scoring
- Priority identification
- Recommendation engine
- Hot/Warm/Cold lead categorization

## Institution Management
- Schools
- Coaching Centres
- Institution profiles
- Institution-linked leads

## Dashboard
- Pipeline overview
- Priority actions
- Analytics cards
- Follow-up monitoring

---

# Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python |
| Framework | Flask |
| Database | SQLite |
| Frontend | HTML, CSS, Bootstrap |
| Templates | Jinja2 |
| Version Control | Git & GitHub |

---

# Project Structure

```text
Lead Intelligence System/
│
├── app.py
├── database/
│   ├── schema.sql
│   ├── db_connection.py
│   └── init_db.py
├── modules/
├── templates/
├── static/
├── lead_system.db
├── requirements.txt
└── README.md
```

---

# Database

Core entities include:

- Leads
- Institutions
- Interactions
- Users (prepared for future multi-user expansion)

---

# Installation

```bash
git clone <repository-url>
cd Lead-Intelligence-System
```

Install dependencies

```bash
pip install -r requirements.txt
```

Initialize the database

```bash
python database/init_db.py
```

Run the application

```bash
python app.py
```

Open:

```
http://127.0.0.1:5000
```

---

# Current Capabilities

- Lead lifecycle management
- Intelligent scoring
- Institution management
- Interaction timeline
- Follow-up scheduling
- Dashboard analytics
- Search & filtering
- Modular Flask architecture

---

# Future Roadmap

- User authentication
- Role-based access control
- AI-assisted lead prioritization
- Predictive admission probability
- WhatsApp integration
- Email automation
- Excel/PDF exports
- Regional Market Intelligence (RMI)
- ERP expansion
- REST API

---

# Why this project?

The objective of this project was not only to build a CRM, but to design a maintainable system capable of evolving into an intelligent admissions platform. The emphasis throughout development has been on modularity, scalability, and clean software engineering practices rather than building a one-off academic project.

---

# Contributing

Contributions, suggestions, and improvements are welcome. Feel free to fork the repository, open issues, or submit pull requests.

---

## Author

**ASH**

Designed and developed as a portfolio project demonstrating backend development, database design, and software engineering using Python and Flask.
