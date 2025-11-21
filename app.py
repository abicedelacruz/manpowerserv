import os, sqlite3, secrets, datetime, math
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'abic_payroll.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'dev-secret-please-change')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    c = db.cursor()
    # create tables
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT CHECK(role IN ('admin','employee')) DEFAULT 'employee'
    );
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        client TEXT,
        username TEXT UNIQUE,
        rest_day TEXT, -- e.g. Monday
        schedule_start TEXT, -- e.g. 09:00
        schedule_end TEXT, -- e.g. 18:00
        monthly_salary REAL
    );
    CREATE TABLE IF NOT EXISTS payrolls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        pay_period TEXT,
        pay_out TEXT,
        payment_terms TEXT,
        monthly_base REAL,
        daily_rate REAL,
        hourly_rate REAL,
        pay_rate_per_cutoff REAL,
        incentives REAL,
        regular_ot_hrs REAL,
        night_diff_hrs REAL,
        night_diff_ot_hrs REAL,
        restday_f8 REAL,
        restday_e8 REAL,
        restday_nightdiff REAL,
        restday_nd_ot REAL,
        adjustment REAL,
        special_hol_hrs REAL,
        special_hol_ot REAL,
        holiday_r_hrs REAL,
        rd_sh_ot REAL,
        special_hol_nd REAL,
        special_hol_nd_ot REAL,
        legal_hol_hrs REAL,
        legal_hol_ot REAL,
        rd_legal_hol_hrs REAL,
        nd_on_lh REAL,
        ndot_on_lh REAL,
        others REAL,
        tardiness_hrs REAL,
        undertime_hrs REAL,
        absences INTEGER,
        sss REAL,
        sss_loan REAL,
        philhealth REAL,
        pagibig REAL,
        pagibig_loan REAL,
        income_tax REAL,
        total_earnings REAL,
        total_deductions REAL,
        netpay REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    );
    ''')
    db.commit()

    # create default admin if none exists
    c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
    if not c.fetchone():
        password = 'AdminPass123'
        c.execute('INSERT INTO users (name,email,username,password_hash,role) VALUES (?,?,?,?,?)',
                  ('Administrator','admin@abic.local','admin',generate_password_hash(password),'admin'))
        db.commit()
        print('Created default admin: username=admin password=', password)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def exec_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid

# --- Authentication ---
@app.route('/')
def index():
    if 'user_id' in session:
        user = query_db('SELECT * FROM users WHERE id=?', (session['user_id'],), one=True)
        if user and user['role']=='admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('employee_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        user = query_db('SELECT * FROM users WHERE username=?', (username,), one=True)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            flash('Logged in successfully','success')
            if user['role']=='admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('employee_dashboard'))
        flash('Invalid credentials','danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- Admin Pages ---
def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*a, **k):
        if session.get('role')!='admin':
            flash('Admin access required','danger')
            return redirect(url_for('login'))
        return fn(*a, **k)
    return wrapper

@app.route('/admin')
@admin_required
def admin_dashboard():
    employees = query_db('SELECT * FROM employees ORDER BY id DESC')
    return render_template('admin.html', employees=employees)

@app.route('/admin/employee/add', methods=['GET','POST'])
@admin_required
def add_employee():
    if request.method=='POST':
        name = request.form['name']
        client = request.form.get('client','')
        rest_day = request.form.get('rest_day','Sunday')
        schedule_start = request.form.get('schedule_start','09:00')
        schedule_end = request.form.get('schedule_end','18:00')
        monthly_salary = float(request.form.get('monthly_salary') or 0)
        # generate username and random password
        username = (name.split()[0] + str(secrets.randbelow(9999))).lower()
        password = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789') for _ in range(10))
        password_hash = generate_password_hash(password)
        try:
            emp_id = exec_db('INSERT INTO employees (name,client,username,rest_day,schedule_start,schedule_end,monthly_salary) VALUES (?,?,?,?,?,?,?)',
                             (name,client,username,rest_day,schedule_start,schedule_end,monthly_salary))
            # create user account for employee
            exec_db('INSERT INTO users (name,email,username,password_hash,role) VALUES (?,?,?,?,?)',
                    (name,f'{username}@abic.local',username,password_hash,'employee'))
            flash(f'Employee {name} added. Username: {username} | Password (showing once): {password}', 'success')
        except Exception as e:
            flash('Error adding employee: '+str(e),'danger')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_employee.html')

@app.route('/admin/employee/delete/<int:eid>', methods=['POST'])
@admin_required
def delete_employee(eid):
    # remove employee and its user account and payrolls
    emp = query_db('SELECT * FROM employees WHERE id=?', (eid,), one=True)
    if not emp:
        flash('Employee not found','danger')
        return redirect(url_for('admin_dashboard'))
    exec_db('DELETE FROM payrolls WHERE employee_id=?', (eid,))
    exec_db('DELETE FROM users WHERE username=?', (emp['username'],))
    exec_db('DELETE FROM employees WHERE id=?', (eid,))
    flash('Employee removed','success')
    return redirect(url_for('admin_dashboard'))

# --- Payroll creation ---
def parse_time(s):
    return datetime.datetime.strptime(s,'%H:%M').time()

def time_diff_hours(t1, t2):
    # return hours difference t2 - t1 as float in hours
    dt1 = datetime.datetime.combine(datetime.date.today(), t1)
    dt2 = datetime.datetime.combine(datetime.date.today(), t2)
    diff = (dt2 - dt1).total_seconds()/3600
    return diff

@app.route('/admin/payroll/add/<int:employee_id>', methods=['GET','POST'])
@admin_required
def add_payroll(employee_id):
    emp = query_db('SELECT * FROM employees WHERE id=?', (employee_id,), one=True)
    if not emp:
        flash('Employee not found','danger')
        return redirect(url_for('admin_dashboard'))

    # load previous payroll to prefill if exists
    last = query_db('SELECT * FROM payrolls WHERE employee_id=? ORDER BY created_at DESC LIMIT 1', (employee_id,), one=True)

    if request.method=='POST':
        form = request.form
        # minimal safe parsing of many fields; missing fields default 0
        def f(name): 
            v = form.get(name,'0').strip() 
            return float(v) if v!='' else 0.0
        monthly_base = f('monthly_base')
        # derive daily/hourly if not provided
        daily_rate = f('daily_rate') or (monthly_base/2/ ( (26) )) # heuristic
        hourly_rate = f('hourly_rate') or (daily_rate/8.0)
        incentives = f('incentives')

        # times: assume admin will input counts for OT etc. For convenience we accept numeric hours fields
        regular_ot_hrs = f('regular_ot_hrs')
        night_diff_hrs = f('night_diff_hrs')
        night_diff_ot_hrs = f('night_diff_ot_hrs')
        restday_f8 = f('restday_f8')
        restday_e8 = f('restday_e8')
        restday_nightdiff = f('restday_nightdiff')
        restday_nd_ot = f('restday_nd_ot')
        adjustment = f('adjustment')
        special_hol_hrs = f('special_hol_hrs')
        special_hol_ot = f('special_hol_ot')
        holiday_r_hrs = f('holiday_r_hrs')
        rd_sh_ot = f('rd_sh_ot')
        special_hol_nd = f('special_hol_nd')
        special_hol_nd_ot = f('special_hol_nd_ot')
        legal_hol_hrs = f('legal_hol_hrs')
        legal_hol_ot = f('legal_hol_ot')
        rd_legal_hol_hrs = f('rd_legal_hol_hrs')
        nd_on_lh = f('nd_on_lh')
        ndot_on_lh = f('ndot_on_lh')
        others = f('others')
        tardiness_hrs = f('tardiness_hrs')
        undertime_hrs = f('undertime_hrs')
        absences = int(form.get('absences','0') or 0)

        # Deductions & contributions
        sss = f('sss')
        sss_loan = f('sss_loan')
        philhealth = f('philhealth')
        pagibig = f('pagibig')
        pagibig_loan = f('pagibig_loan')
        income_tax = f('income_tax')

        # Compute earnings per given formula (Mali Lending Corp)
        # Regular OT = hourly_rate * 1.25 * hrs
        regular_ot_pay = hourly_rate * 1.25 * regular_ot_hrs
        # Restday rate: hourly * 1.30 * hrs
        restday_pay = hourly_rate * 1.30 * (restday_f8 + restday_e8)
        restday_ot_pay = hourly_rate * 1.69 * restday_nd_ot if restday_nd_ot else 0
        night_diff_pay = hourly_rate * 1.10 * night_diff_hrs
        night_diff_ot_pay = hourly_rate * 1.375 * night_diff_ot_hrs
        special_hol_pay = hourly_rate * 1.30 * special_hol_hrs
        special_hol_ot_pay = hourly_rate * 1.69 * special_hol_ot
        legal_hol_pay = hourly_rate * 2.00 * legal_hol_hrs
        legal_hol_ot_pay = hourly_rate * 2.60 * legal_hol_ot

        gross_earnings = monthly_base + incentives + regular_ot_pay + restday_pay + restday_ot_pay + night_diff_pay + night_diff_ot_pay + special_hol_pay + special_hol_ot_pay + legal_hol_pay + legal_hol_ot_pay + others + adjustment

        # tardiness and undertime charged at hourly_rate * hours
        tardiness_ded = hourly_rate * tardiness_hrs
        undertime_ded = hourly_rate * undertime_hrs
        lwop = absences * (daily_rate if daily_rate else (monthly_base/26.0))

        total_deductions = sss + sss_loan + philhealth + pagibig + pagibig_loan + income_tax + tardiness_ded + undertime_ded + lwop

        netpay = gross_earnings - total_deductions

        # insert payroll
        exec_db('''INSERT INTO payrolls (employee_id,pay_period,pay_out,payment_terms,monthly_base,daily_rate,hourly_rate,pay_rate_per_cutoff,incentives,regular_ot_hrs,night_diff_hrs,night_diff_ot_hrs,restday_f8,restday_e8,restday_nightdiff,restday_nd_ot,adjustment,special_hol_hrs,special_hol_ot,holiday_r_hrs,rd_sh_ot,special_hol_nd,special_hol_nd_ot,legal_hol_hrs,legal_hol_ot,rd_legal_hol_hrs,nd_on_lh,ndot_on_lh,others,tardiness_hrs,undertime_hrs,absences,sss,sss_loan,philhealth,pagibig,pagibig_loan,income_tax,total_earnings,total_deductions,netpay) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (employee_id, form.get('pay_period',''), form.get('pay_out',''), form.get('payment_terms',''), monthly_base, daily_rate, hourly_rate, f('pay_rate_per_cutoff'), incentives, regular_ot_hrs, night_diff_hrs, night_diff_ot_hrs, restday_f8, restday_e8, restday_nightdiff, restday_nd_ot, adjustment, special_hol_hrs, special_hol_ot, holiday_r_hrs, rd_sh_ot, special_hol_nd, special_hol_nd_ot, legal_hol_hrs, legal_hol_ot, rd_legal_hol_hrs, nd_on_lh, ndot_on_lh, others, tardiness_hrs, undertime_hrs, absences, sss, sss_loan, philhealth, pagibig, pagibig_loan, income_tax, gross_earnings, total_deductions, netpay))
        flash('Payroll added for '+emp['name'],'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('payroll_form.html', emp=emp, last=last)

@app.route('/admin/payrolls/<int:employee_id>')
@admin_required
def view_payrolls(employee_id):
    emp = query_db('SELECT * FROM employees WHERE id=?', (employee_id,), one=True)
    if not emp:
        flash('Employee not found','danger')
        return redirect(url_for('admin_dashboard'))
    payrolls = query_db('SELECT * FROM payrolls WHERE employee_id=? ORDER BY created_at DESC', (employee_id,))
    return render_template('payrolls_list.html', emp=emp, payrolls=payrolls)

# --- Employee dashboard ---
def employee_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*a, **k):
        if session.get('role')!='employee':
            flash('Employee access required','danger')
            return redirect(url_for('login'))
        return fn(*a, **k)
    return wrapper

@app.route('/employee')
@employee_required
def employee_dashboard():
    user = query_db('SELECT * FROM users WHERE id=?', (session['user_id'],), one=True)
    emp = query_db('SELECT * FROM employees WHERE username=?', (user['username'],), one=True)
    if not emp:
        flash('Employee record not found','danger')
        return redirect(url_for('login'))
    payrolls = query_db('SELECT * FROM payrolls WHERE employee_id=? ORDER BY created_at DESC', (emp['id'],))
    return render_template('employee_dashboard.html', emp=emp, payrolls=payrolls)

@app.route('/employee/payslip/<int:pid>')
@employee_required
def employee_payslip(pid):
    user = query_db('SELECT * FROM users WHERE id=?', (session['user_id'],), one=True)
    emp = query_db('SELECT * FROM employees WHERE username=?', (user['username'],), one=True)
    payroll = query_db('SELECT * FROM payrolls WHERE id=? AND employee_id=?', (pid, emp['id']), one=True)
    if not payroll:
        flash('Payslip not found or access denied','danger')
        return redirect(url_for('employee_dashboard'))
    return render_template('payslip.html', emp=emp, p=payroll)

# Static files route for simple deployments
@app.route('/static/<path:p>')
def static_file(p):
    return send_from_directory(os.path.join(BASE_DIR,'static'), p)

if __name__=='__main__':
    # ensure DB exists / initialized
    if not os.path.exists(DB_PATH):
        with app.app_context():
            init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
