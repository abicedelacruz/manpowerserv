ABIC Manpower - Payroll App (Minimal Flask)
===========================================

What this contains
- Flask app with SQLite database
- Admin dashboard: add/remove employees, create payrolls, view payroll history
- Auto-generate username/password for each employee (password hashed in DB)
- Employee login to view their own payslips only
- Payslip layout (prettified with Bootstrap)
- Payroll computation using the formulas you provided for Mali Lending Corp (best-effort)
- Ability to load previous payroll inputs when creating a new payroll for an employee

How to run locally
1. Ensure Python 3.10+ is installed.
2. Create virtualenv and install requirements:
   python -m venv venv
   source venv/bin/activate  (or venv\Scripts\activate on Windows)
   pip install -r requirements.txt
3. Initialize DB (first run will auto-create db with an admin user):
   flask --app app.py run --host=0.0.0.0 --port=5000
4. Default admin login: username: admin@example.com password: AdminPass123
   Please change it immediately from the Admin > Settings page (simple implementation).

Deployment notes
- For remote 24/7 hosting you can deploy to Render, Fly.io, Railway, or use a VPS.
- For quick remote exposure you can use ngrok for development (not production).

Project files description:
- app.py: main Flask app
- templates/: Jinja2 HTML templates
- static/: CSS and simple client assets
- abic_payroll.db: SQLite DB (created at first run)


## Deploying to Render (quick)

1. Create a new GitHub repo and push the project.
2. Go to https://render.com -> New -> Web Service -> Connect your GitHub repo.
3. For Environment choose **Docker**, Render will detect the Dockerfile. (Alternatively choose Python and set Build Command: `pip install -r requirements.txt` and Start Command: `gunicorn app:app -b 0.0.0.0:$PORT`)
4. Set the port in the Dockerfile (above we used 10000). If you choose the Python environment instead of Docker, set Start Command: `gunicorn app:app -w 4 -b 0.0.0.0:$PORT` and Render will set $PORT automatically.
5. Set environment variables on Render: `FLASK_SECRET` (strong secret) and optionally `DATABASE_URL` if you switch to a managed DB.

