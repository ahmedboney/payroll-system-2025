import sqlite3
import os
import sys
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# في وضع PyInstaller: قاعدة البيانات تكون بجوار الـ exe (وليس في مجلد التحميل المؤقت)
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(_BASE_DIR, 'payroll.db')

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.create_tables()
        self._migrate()
        self.seed_defaults()

    def _cur(self):
        return self.conn.cursor()

    def create_tables(self):
        c = self._cur()
        c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                role TEXT DEFAULT 'user',
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                manager TEXT DEFAULT '',
                cost_center TEXT DEFAULT '',
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                national_id TEXT DEFAULT '',
                department_id INTEGER,
                position TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                address TEXT DEFAULT '',
                gender TEXT DEFAULT 'male',
                birth_date TEXT DEFAULT '',
                hire_date TEXT DEFAULT '',
                termination_date TEXT DEFAULT '',
                marital_status TEXT DEFAULT '',
                bank_name TEXT DEFAULT '',
                bank_account TEXT DEFAULT '',
                -- نوع الأجر: monthly / daily / hourly / commission
                pay_type TEXT DEFAULT 'monthly',
                base_salary REAL DEFAULT 0,
                daily_rate REAL DEFAULT 0,
                hourly_rate REAL DEFAULT 0,
                commission_rate REAL DEFAULT 0,
                -- البدلات
                housing_allowance REAL DEFAULT 0,
                transport_allowance REAL DEFAULT 0,
                food_allowance REAL DEFAULT 0,
                other_allowances REAL DEFAULT 0,
                danger_allowance REAL DEFAULT 0,
                phone_allowance REAL DEFAULT 0,
                -- التأمين والضرائب
                social_insurance_enabled INTEGER DEFAULT 1,
                social_insurance_employee_ratio REAL DEFAULT 11,
                social_insurance_employer_ratio REAL DEFAULT 18.75,
                income_tax_enabled INTEGER DEFAULT 1,
                tax_exempt_amount REAL DEFAULT 0,
                -- حالة
                status TEXT DEFAULT 'active',
                remarks TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                check_in TEXT DEFAULT '',
                check_out TEXT DEFAULT '',
                status TEXT DEFAULT 'present', -- present/absent/late/leave/sick
                note TEXT DEFAULT '',
                month TEXT DEFAULT '',
                UNIQUE(employee_id, date),
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS leave_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                leave_type TEXT NOT NULL, -- annual/sick/emergency/unpaid/maternity
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                days REAL DEFAULT 0,
                reason TEXT DEFAULT '',
                status TEXT DEFAULT 'pending', -- pending/approved/rejected
                approved_by TEXT DEFAULT '',
                approved_date TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS overtime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                hours REAL DEFAULT 0,
                rate_type TEXT DEFAULT 'auto', -- auto/manual
                multiplier REAL DEFAULT 1.5,
                hourly_rate REAL DEFAULT 0,
                amount REAL DEFAULT 0,
                confirmed INTEGER DEFAULT 0,
                note TEXT DEFAULT '',
                month TEXT DEFAULT '',
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                sales_amount REAL DEFAULT 0,
                rate REAL DEFAULT 0,
                amount REAL DEFAULT 0,
                note TEXT DEFAULT '',
                month TEXT DEFAULT '',
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS deduction_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT 'other', -- penalty/loan/damage/social/food/other
                description TEXT DEFAULT '',
                active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS deductions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                deduction_type TEXT DEFAULT '',
                amount REAL DEFAULT 0,
                note TEXT DEFAULT '',
                month TEXT DEFAULT '',
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS advances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL DEFAULT 0,
                installment_count INTEGER DEFAULT 1,
                installment_amount REAL DEFAULT 0,
                current_installment INTEGER DEFAULT 0,
                remaining REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS payroll_proof (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                gross_salary REAL DEFAULT 0,
                total_allowances REAL DEFAULT 0,
                overtime_amount REAL DEFAULT 0,
                commission_amount REAL DEFAULT 0,
                total_earnings REAL DEFAULT 0,
                social_insurance_employee REAL DEFAULT 0,
                social_insurance_employer REAL DEFAULT 0,
                income_tax REAL DEFAULT 0,
                advance_installments REAL DEFAULT 0,
                absence_deduction REAL DEFAULT 0,
                late_deduction REAL DEFAULT 0,
                other_deductions REAL DEFAULT 0,
                total_deductions REAL DEFAULT 0,
                net_salary REAL DEFAULT 0,
                days_worked REAL DEFAULT 0,
                status TEXT DEFAULT 'draft', -- draft/confirmed/paid
                paid_date TEXT DEFAULT '',
                note TEXT DEFAULT '',
                UNIQUE(employee_id, month),
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS salary_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                old_salary REAL DEFAULT 0,
                new_salary REAL DEFAULT 0,
                change_date TEXT DEFAULT '',
                reason TEXT DEFAULT '',
                created_by TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            -- التعاقدات
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                contract_type TEXT DEFAULT 'permanent', -- permanent/fixed/temporary/parttime
                contract_number TEXT DEFAULT '',
                start_date TEXT NOT NULL,
                end_date TEXT DEFAULT '',
                salary REAL DEFAULT 0,
                allowance_details TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                status TEXT DEFAULT 'active', -- active/expired/terminated
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            -- توقيع استلام الراتب (بصمة إلكترونية)
            CREATE TABLE IF NOT EXISTS payroll_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                slip_number TEXT DEFAULT '',
                gross_salary REAL DEFAULT 0,
                net_salary REAL DEFAULT 0,
                signature_data TEXT DEFAULT '',       -- قاعدة بيانات من الصورة أو نص التوقيع
                sign_date TEXT DEFAULT '',
                signed_by_ip TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                UNIQUE(employee_id, month),
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            -- سجل التدقيق (إجراءات حساسة)
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT DEFAULT '',
                action TEXT DEFAULT '',
                entity TEXT DEFAULT '',
                entity_id INTEGER,
                details TEXT DEFAULT '',
                ip_address TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- حوافز/خصومات جماعية
            CREATE TABLE IF NOT EXISTS bulk_incentives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                kind TEXT NOT NULL,        -- bonus / ded
                description TEXT DEFAULT '',
                per_employee_amount REAL DEFAULT 0,
                specific_employees TEXT DEFAULT '', -- JSON list or empty = all active
                applied INTEGER DEFAULT 0,
                created_by TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- ضريبة كسب العمل بالشرائح
            CREATE TABLE IF NOT EXISTS tax_brackets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_amount REAL NOT NULL,
                to_amount REAL,    -- NULL = infinity
                rate REAL NOT NULL,
                fixed_deduction REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT DEFAULT '',
                company_address TEXT DEFAULT '',
                company_phone TEXT DEFAULT '',
                company_tax_id TEXT DEFAULT '',
                company_insurance_no TEXT DEFAULT '',
                currency TEXT DEFAULT 'EGP',
                -- العمل
                weekly_holidays TEXT DEFAULT '6', -- يوم الجمعة (0=السبت .. 6=الجمعة)
                working_days_monthly REAL DEFAULT 26,
                working_hours_daily REAL DEFAULT 8,
                -- الإضافي
                overtime_weekday REAL DEFAULT 1.5,
                overtime_weekend REAL DEFAULT 2.0,
                overtime_holiday REAL DEFAULT 3.0,
                -- التأمينات
                insurance_floor REAL DEFAULT 2200,
                insurance_ceiling REAL DEFAULT 14700,
                insurance_employee_ratio REAL DEFAULT 11,
                insurance_employer_ratio REAL DEFAULT 18.75,
                -- ضرائب
                tax_exempt_default REAL DEFAULT 0,
                -- غياب/تأخير
                absence_deduction_percent REAL DEFAULT 100,
                late_minutes_tolerance INTEGER DEFAULT 15,
                late_deduction_per_hour REAL DEFAULT 0,
                -- أمان
                admin_password_changed INTEGER DEFAULT 0
            );
        ''')
        self.conn.commit()

    def _migrate(self):
        """ترحيل تدريجي للجداول الموجودة (إضافة أعمدة جديدة بدون فقدان بيانات)."""
        c = self._cur()
        # 1) عمود admin_password_changed في settings لإلزام تغيير كلمة مرور المدير أول مرة
        cols = [r[1] for r in c.execute("PRAGMA table_info(settings)").fetchall()]
        if 'admin_password_changed' not in cols:
            c.execute("ALTER TABLE settings ADD COLUMN admin_password_changed INTEGER DEFAULT 0")
        # 2) عمود last_backup في settings لتتبع النسخ الاحتياطي التلقائي الشهري
        if 'last_backup' not in cols:
            c.execute("ALTER TABLE settings ADD COLUMN last_backup TEXT DEFAULT ''")
        self.conn.commit()

    def seed_defaults(self):
        c = self._cur()
        # المستخدمون الافتراضيون (يُنبأون فقط عند قاعدة بيانات جديدة تماماً)
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            users = [
                ('admin', 'admin123', 'مدير النظام', 'admin'),
                ('supervisor', 'super123', 'محمد المشرف', 'supervisor'),
                ('user', 'user123', 'سارة المستخدمة', 'user'),
                ('viewer', 'viewer123', 'خالد المشاهد', 'viewer'),
            ]
            for uname, pwd, fname, role in users:
                c.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                    (uname, generate_password_hash(pwd), fname, role))
        # settings
        c.execute("SELECT COUNT(*) FROM settings")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO settings DEFAULT VALUES")
        # tax brackets - ضريبة كسب العمل في مصر
        c.execute("SELECT COUNT(*) FROM tax_brackets")
        if c.fetchone()[0] == 0:
            brackets = [
                (0, 15000, 0, 0),          # معفاة
                (15000, 30000, 2.5, 0),     # شريحة أولى
                (30000, 45000, 10, 375),    # شريحة ثانية
                (45000, 60000, 15, 2625),   # شريحة ثالثة
                (60000, 200000, 20, 5625),  # شريحة رابعة
                (200000, 400000, 22.5, 10625), # شريحة خامسة
                (400000, 500000, 25, 20625),   # شريحة سادسة
                (500000, 900000, 30, 45625),   # شريحة سابعة
                (900000, None, 32.5, 68125),   # أعلى
            ]
            c.executemany("INSERT INTO tax_brackets (from_amount,to_amount,rate,fixed_deduction) VALUES (?,?,?,?)", brackets)
        # deduction types
        c.execute("SELECT COUNT(*) FROM deduction_types")
        if c.fetchone()[0] == 0:
            types = [
                ('جزاء إداري', 'penalty', 'خصم بسبب مخالفة'),
                ('قرض', 'loan', 'أقساط قرض'),
                ('تلفيات', 'damage', 'خصم أضرار'),
                ('سلفة', 'advance', 'أقساط سلفة'),
                ('طعام', 'food', 'اشتراك وجبات'),
                ('موبايل', 'social', 'فاتورة موبايل'),
                ('خصم آخر', 'other', 'أي خصم آخر'),
            ]
            c.executemany("INSERT INTO deduction_types (name,category,description) VALUES (?,?,?)", types)
        self.conn.commit()

    # ==================== AUTH ====================
    def authenticate(self, username, password):
        c = self._cur()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if row and check_password_hash(row['password'], password):
            return dict(row)
        return None

    def verify_password(self, stored_hash, password):
        return check_password_hash(stored_hash, password)

    def change_password(self, uid, new_password):
        c = self._cur()
        c.execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(new_password), uid))
        self.conn.commit()

    def toggle_user(self, uid):
        c = self._cur()
        c.execute("SELECT active FROM users WHERE id=?", (uid,))
        r = c.fetchone()
        if r:
            c.execute("UPDATE users SET active=? WHERE id=?", (0 if r['active'] else 1, uid))
            self.conn.commit()

    def get_user_by_id(self, uid):
        c = self._cur()
        c.execute("SELECT * FROM users WHERE id=?", (uid,))
        r = c.fetchone()
        return dict(r) if r else None

    def get_all_users(self):
        c = self._cur()
        c.execute("SELECT id,username,full_name,role,active,created_at FROM users ORDER BY username")
        return [dict(r) for r in c.fetchall()]

    def add_user(self, data):
        c = self._cur()
        c.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
            (data['username'], generate_password_hash(data['password']), data.get('full_name',''), data.get('role','user')))
        self.conn.commit()

    def delete_user(self, uid):
        c = self._cur()
        c.execute("DELETE FROM users WHERE id=?", (uid,))
        self.conn.commit()

    # ==================== DEPARTMENTS ====================
    def get_departments(self, active_only=False):
        c = self._cur()
        q = """SELECT d.*, COUNT(e.id) as emp_count
               FROM departments d LEFT JOIN employees e ON d.id=e.department_id AND e.status='active'"""
        if active_only:
            q += " WHERE d.active=1"
        q += " GROUP BY d.id ORDER BY d.name"
        c.execute(q)
        return [dict(r) for r in c.fetchall()]

    def add_department(self, name, manager='', cost_center=''):
        c = self._cur()
        c.execute("INSERT INTO departments (name,manager,cost_center) VALUES (?,?,?)", (name,manager,cost_center))
        self.conn.commit()

    def delete_department(self, dep_id):
        c = self._cur()
        c.execute("SELECT COUNT(*) as cnt FROM employees WHERE department_id=?", (dep_id,))
        if c.fetchone()['cnt'] > 0:
            return False
        c.execute("DELETE FROM departments WHERE id=?", (dep_id,))
        self.conn.commit()
        return True

    # ==================== EMPLOYEES ====================
    def get_employees(self, department=None, status='active', search='', sort='name'):
        c = self._cur()
        q = """SELECT e.*, d.name as dept_name
               FROM employees e LEFT JOIN departments d ON e.department_id=d.id WHERE 1=1"""
        params = []
        if status and status != 'all':
            q += " AND e.status=?"
            params.append(status)
        if department:
            q += " AND e.department_id=?"
            params.append(department)
        if search:
            q += " AND (e.name LIKE ? OR e.emp_code LIKE ? OR e.national_id LIKE ? OR e.position LIKE ?)"
            params += [f"%{search}%"]*4
        allowed = {'name': 'e.name', 'emp_code': 'e.emp_code', 'base_salary': 'e.base_salary',
                   'department': 'd.name'}
        order = allowed.get(sort, 'e.name')
        q += f" ORDER BY {order}"
        c.execute(q, params)
        return [dict(r) for r in c.fetchall()]

    def get_employee(self, emp_id):
        c = self._cur()
        c.execute("""SELECT e.*, d.name as dept_name
                     FROM employees e LEFT JOIN departments d ON e.department_id=d.id WHERE e.id=?""", (emp_id,))
        r = c.fetchone()
        return dict(r) if r else None

    def next_emp_code(self):
        c = self._cur()
        c.execute("SELECT emp_code FROM employees ORDER BY id DESC LIMIT 1")
        r = c.fetchone()
        if not r:
            return "EMP001"
        try:
            n = int(r['emp_code'].replace('EMP','')) + 1
        except Exception:
            return "EMP001"
        return f"EMP{n:03d}"

    def add_employee(self, d):
        c = self._cur()
        dept_id = d.get('department_id') or None
        c.execute("""INSERT INTO employees (emp_code,name,national_id,department_id,position,phone,email,address,
            gender,birth_date,hire_date,marital_status,bank_name,bank_account,
            pay_type,base_salary,daily_rate,hourly_rate,commission_rate,
            housing_allowance,transport_allowance,food_allowance,other_allowances,danger_allowance,phone_allowance,
            social_insurance_enabled,social_insurance_employee_ratio,social_insurance_employer_ratio,
            income_tax_enabled,tax_exempt_amount,status,remarks)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d['emp_code'],d['name'],d.get('national_id',''),dept_id,d.get('position',''),
             d.get('phone',''),d.get('email',''),d.get('address',''),d.get('gender','male'),
             d.get('birth_date',''),d.get('hire_date',''),d.get('marital_status',''),
             d.get('bank_name',''),d.get('bank_account',''),
             d.get('pay_type','monthly'),d.get('base_salary',0),d.get('daily_rate',0),
             d.get('hourly_rate',0),d.get('commission_rate',0),
             d.get('housing_allowance',0),d.get('transport_allowance',0),d.get('food_allowance',0),
             d.get('other_allowances',0),d.get('danger_allowance',0),d.get('phone_allowance',0),
             d.get('social_insurance_enabled',1),d.get('social_insurance_employee_ratio',11),
             d.get('social_insurance_employer_ratio',18.75),d.get('income_tax_enabled',1),
             d.get('tax_exempt_amount',0),d.get('status','active'),d.get('remarks','')))
        self.conn.commit()
        return c.lastrowid

    def update_employee(self, emp_id, d):
        c = self._cur()
        dept_id = d.get('department_id') or None
        c.execute("""UPDATE employees SET emp_code=?,name=?,national_id=?,department_id=?,position=?,phone=?,email=?,
            address=?,gender=?,birth_date=?,hire_date=?,marital_status=?,bank_name=?,bank_account=?,
            pay_type=?,base_salary=?,daily_rate=?,hourly_rate=?,commission_rate=?,
            housing_allowance=?,transport_allowance=?,food_allowance=?,other_allowances=?,danger_allowance=?,phone_allowance=?,
            social_insurance_enabled=?,social_insurance_employee_ratio=?,social_insurance_employer_ratio=?,
            income_tax_enabled=?,tax_exempt_amount=?,status=?,remarks=? WHERE id=?""",
            (d['emp_code'],d['name'],d.get('national_id',''),dept_id,d.get('position',''),
             d.get('phone',''),d.get('email',''),d.get('address',''),d.get('gender','male'),
             d.get('birth_date',''),d.get('hire_date',''),d.get('marital_status',''),
             d.get('bank_name',''),d.get('bank_account',''),
             d.get('pay_type','monthly'),d.get('base_salary',0),d.get('daily_rate',0),
             d.get('hourly_rate',0),d.get('commission_rate',0),
             d.get('housing_allowance',0),d.get('transport_allowance',0),d.get('food_allowance',0),
             d.get('other_allowances',0),d.get('danger_allowance',0),d.get('phone_allowance',0),
             d.get('social_insurance_enabled',1),d.get('social_insurance_employee_ratio',11),
             d.get('social_insurance_employer_ratio',18.75),d.get('income_tax_enabled',1),
             d.get('tax_exempt_amount',0),d.get('status','active'),d.get('remarks',''), emp_id))
        self.conn.commit()

    def delete_employee(self, emp_id):
        c = self._cur()
        c.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        self.conn.commit()

    def record_salary_change(self, emp_id, old_salary, new_salary, reason, user):
        c = self._cur()
        c.execute("INSERT INTO salary_history (employee_id,old_salary,new_salary,reason,created_by) VALUES (?,?,?,?,?)",
            (emp_id, old_salary, new_salary, reason, user))
        self.conn.commit()

    def get_salary_history(self, emp_id):
        c = self._cur()
        c.execute("SELECT * FROM salary_history WHERE employee_id=? ORDER BY change_date DESC, id DESC", (emp_id,))
        return [dict(r) for r in c.fetchall()]

    # ==================== ATTENDANCE ====================
    def get_attendance(self, month):
        c = self._cur()
        c.execute("""SELECT a.*, e.name as emp_name, e.emp_code
            FROM attendance a JOIN employees e ON a.employee_id=e.id
            WHERE a.month=? ORDER BY e.name, a.date""", (month,))
        return [dict(r) for r in c.fetchall()]

    def bulk_save_attendance(self, month, records):
        c = self._cur()
        for r in records:
            c.execute("""INSERT OR REPLACE INTO attendance (employee_id,date,check_in,check_out,status,note,month)
                VALUES (?,?,?,?,?,?,?)""",
                (r['employee_id'], r['date'], r.get('check_in',''), r.get('check_out',''),
                 r.get('status','present'), r.get('note',''), month))
        self.conn.commit()

    # ==================== LEAVES ====================
    def get_leaves(self, **filters):
        c = self._cur()
        q = """SELECT l.*, e.name as emp_name, e.emp_code
               FROM leave_requests l JOIN employees e ON l.employee_id=e.id WHERE 1=1"""
        params = []
        if filters.get('status'):
            q += " AND l.status=?"
            params.append(filters['status'])
        q += " ORDER BY l.created_at DESC"
        c.execute(q, params)
        return [dict(r) for r in c.fetchall()]

    def add_leave(self, d):
        c = self._cur()
        c.execute("""INSERT INTO leave_requests (employee_id,leave_type,start_date,end_date,days,reason)
            VALUES (?,?,?,?,?,?)""",
            (d['employee_id'], d['leave_type'], d['start_date'], d['end_date'], d['days'], d.get('reason','')))
        self.conn.commit()

    def update_leave_status(self, leave_id, status, user):
        c = self._cur()
        c.execute("UPDATE leave_requests SET status=?,approved_by=?,approved_date=? WHERE id=?",
            (status, user, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), leave_id))
        self.conn.commit()

    # ==================== OVERTIME ====================
    def get_overtime(self, month):
        c = self._cur()
        c.execute("""SELECT o.*, e.name as emp_name, e.emp_code
            FROM overtime o JOIN employees e ON o.employee_id=e.id
            WHERE o.month=? ORDER BY e.name, o.date""", (month,))
        return [dict(r) for r in c.fetchall()]

    def bulk_save_overtime(self, month, records):
        c = self._cur()
        for r in records:
            c.execute("""INSERT INTO overtime (employee_id,date,hours,rate_type,multiplier,hourly_rate,amount,note,month)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (r['employee_id'], r['date'], r.get('hours',0), r.get('rate_type','auto'),
                 r.get('multiplier',1.5), r.get('hourly_rate',0), r.get('amount',0),
                 r.get('note',''), month))
        self.conn.commit()

    # ==================== COMMISSIONS ====================
    def get_commissions(self, month):
        c = self._cur()
        c.execute("""SELECT co.*, e.name as emp_name, e.emp_code
            FROM commissions co JOIN employees e ON co.employee_id=e.id
            WHERE co.month=? ORDER BY e.name, co.date""", (month,))
        return [dict(r) for r in c.fetchall()]

    def bulk_save_commissions(self, month, records):
        c = self._cur()
        for r in records:
            c.execute("""INSERT INTO commissions (employee_id,date,sales_amount,rate,amount,note,month)
                VALUES (?,?,?,?,?,?,?)""",
                (r['employee_id'], r.get('date', month+'-01'), r.get('sales_amount',0),
                 r.get('rate',0), r.get('amount',0), r.get('note',''), month))
        self.conn.commit()

    # ==================== DEDUCTIONS ====================
    def get_deduction_types(self):
        c = self._cur()
        c.execute("SELECT * FROM deduction_types WHERE active=1 ORDER BY name")
        return [dict(r) for r in c.fetchall()]

    def get_deductions(self, month):
        c = self._cur()
        c.execute("""SELECT dd.*, e.name as emp_name, e.emp_code
            FROM deductions dd JOIN employees e ON dd.employee_id=e.id
            WHERE dd.month=? ORDER BY e.name, dd.date""", (month,))
        return [dict(r) for r in c.fetchall()]

    def bulk_save_deductions(self, month, records):
        c = self._cur()
        for r in records:
            c.execute("""INSERT INTO deductions (employee_id,date,deduction_type,amount,note,month)
                VALUES (?,?,?,?,?,?)""",
                (r['employee_id'], r.get('date', month+'-01'), r.get('deduction_type','other'),
                 r.get('amount',0), r.get('note',''), month))
        self.conn.commit()

    # ==================== ADVANCES ====================
    def get_advances(self, month=None):
        c = self._cur()
        q = """SELECT a.*, e.name as emp_name, e.emp_code
               FROM advances a JOIN employees e ON a.employee_id=e.id WHERE 1=1"""
        params = []
        if month:
            q += " AND substr(a.date,1,7)=?"
            params.append(month)
        q += " ORDER BY a.created_at DESC"
        c.execute(q, params)
        return [dict(r) for r in c.fetchall()]

    def add_advance(self, d):
        c = self._cur()
        installment_amount = d['amount']/d['installment_count'] if d['installment_count'] > 0 else d['amount']
        c.execute("""INSERT INTO advances (employee_id,date,amount,installment_count,installment_amount,remaining,status,note)
            VALUES (?,?,?,?,?,?,?,?)""",
            (d['employee_id'], d.get('date', datetime.now().strftime('%Y-%m-%d')),
             d['amount'], d['installment_count'], installment_amount, d['amount'], 'active', d.get('note','')))
        self.conn.commit()
        return c.lastrowid

    def delete_advance(self, adv_id):
        c = self._cur()
        c.execute("DELETE FROM advances WHERE id=?", (adv_id,))
        self.conn.commit()

    # ==================== INCOME TAX ====================
    def calc_income_tax(self, annual_income, exempt=0):
        """حساب ضريبة كسب العمل حسب الشرائح على الدخل السنوي"""
        c = self._cur()
        c.execute("SELECT * FROM tax_brackets ORDER BY from_amount")
        brackets = [dict(r) for r in c.fetchall()]
        taxable = annual_income - exempt
        if taxable <= 0:
            return 0
        tax = 0
        # نستخدم طريقة الفرق - نحسب الضريبة مباشرة بناءً على الشريحة التي تقع فيها
        for i, b in enumerate(brackets):
            if taxable <= b['from_amount']:
                break
            upper = b['to_amount']
            if upper is None:
                upper = taxable
            if taxable <= (upper if upper else taxable):
                segment = taxable - b['from_amount'] if taxable > b['from_amount'] else 0
                # الضريبة للمبلغ في هذه الشريحة
                if b['fixed_deduction']:
                    tax = (taxable * b['rate']/100) - b['fixed_deduction']
                    break
                else:
                    tax = segment * b['rate']/100
                    break
        return max(0, round(tax, 2))

    # ==================== SETTINGS ====================
    def get_settings(self):
        c = self._cur()
        c.execute("SELECT * FROM settings LIMIT 1")
        r = c.fetchone()
        return dict(r) if r else {}

    def save_settings(self, d):
        c = self._cur()
        c.execute("""UPDATE settings SET company_name=?,company_address=?,company_phone=?,company_tax_id=?,
            company_insurance_no=?,currency=?,weekly_holidays=?,working_days_monthly=?,working_hours_daily=?,
            overtime_weekday=?,overtime_weekend=?,overtime_holiday=?,
            insurance_floor=?,insurance_ceiling=?,insurance_employee_ratio=?,insurance_employer_ratio=?,
            tax_exempt_default=?,absence_deduction_percent=?,late_minutes_tolerance=?,late_deduction_per_hour=? WHERE id=1""",
            (d.get('company_name',''),d.get('company_address',''),d.get('company_phone',''),d.get('company_tax_id',''),
             d.get('company_insurance_no',''),d.get('currency','EGP'),d.get('weekly_holidays','6'),
             d.get('working_days_monthly',26),d.get('working_hours_daily',8),
             d.get('overtime_weekday',1.5),d.get('overtime_weekend',2.0),d.get('overtime_holiday',3.0),
             d.get('insurance_floor',2200),d.get('insurance_ceiling',14700),
             d.get('insurance_employee_ratio',11),d.get('insurance_employer_ratio',18.75),
             d.get('tax_exempt_default',0),d.get('absence_deduction_percent',100),
             d.get('late_minutes_tolerance',15),d.get('late_deduction_per_hour',0)))
        self.conn.commit()

    # ==================== BACKUP / RESTORE ====================
    def create_backup(self):
        """إنشاء نسخة احتياطية من قاعدة البيانات عبر SQLite online-backup API."""
        import shutil
        try:
            self.conn.commit()
            self.conn.execute("PRAGMA wal_checkpoint(FULL)")
        except Exception:
            pass
        backups_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = os.path.join(backups_dir, f'backup_{stamp}.db')
        src = DB_PATH
        try:
            shutil.copy2(src, dest)
        except Exception:
            # بديل: نسخ عبر SQLite backup API
            bconn = sqlite3.connect(dest)
            self.conn.backup(bconn)
            bconn.close()
        # تسجيل آخر نسخة احتياطية في الإعدادات
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        c = self._cur()
        c.execute("UPDATE settings SET last_backup=? WHERE id=1", (now,))
        self.conn.commit()
        return dest, now

    def list_backups(self):
        backups_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
        if not os.path.isdir(backups_dir):
            return []
        out = []
        for f in sorted(os.listdir(backups_dir), reverse=True):
            if f.startswith('backup_') and f.endswith('.db'):
                p = os.path.join(backups_dir, f)
                out.append({'filename': f, 'path': p,
                            'size': os.path.getsize(p),
                            'created': datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')})
        return out

    def delete_backup(self, filename):
        backups_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
        p = os.path.join(backups_dir, filename)
        if os.path.isfile(p) and filename.startswith('backup_') and filename.endswith('.db'):
            os.remove(p)
            return True
        return False

    def restore_backup(self, filename):
        """استعادة نسخة احتياطية: تنسخ الملف فوق قاعدة البيانات الحالية."""
        backups_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
        p = os.path.join(backups_dir, filename)
        if not (os.path.isfile(p) and filename.startswith('backup_') and filename.endswith('.db')):
            raise ValueError('ملف نسخة احتياطية غير صالح')
        self.conn.commit()
        try:
            self.conn.close()
        except Exception:
            pass
        import shutil
        shutil.copy2(p, DB_PATH)
        # إعادة فتح الاتصال
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        return True

    def run_auto_backup_if_due(self):
        """نسخة احتياطية تلقائية شهرية (مقارنة بالشهر الحالي)."""
        sett = self.get_settings()
        last = (sett.get('last_backup') or '')
        if not last.startswith(datetime.now().strftime('%Y-%m')):
            try:
                self.create_backup()
                return True
            except Exception:
                return False
        return False

    # ==================== AUTH HELPERS ====================
    def mark_password_changed(self):
        c = self._cur()
        c.execute("UPDATE settings SET admin_password_changed=1 WHERE id=1")
        self.conn.commit()

    def admin_must_change_password(self, user):
        """إلزام مدير النظام الأولي بتغيير كلمة المرور الافتراضية."""
        if not user or user.get('role') != 'admin':
            return False
        sett = self.get_settings()
        return not bool(sett.get('admin_password_changed'))

    def get_tax_brackets(self):
        c = self._cur()
        c.execute("SELECT * FROM tax_brackets ORDER BY from_amount")
        return [dict(r) for r in c.fetchall()]

    # ==================== PAYROLL ====================
    def calculate_payroll(self, month):
        """حساب المرتبات الشامل لكافة الموظفين النشطين"""
        settings = self.get_settings()
        c = self._cur()
        employees = self.get_employees(status='active')

        # احصل على أيام عمل الشهر (عدا الإجازات الأسبوعية)
        monthly_days = settings['working_days_monthly']

        results = []
        for emp in employees:
            emp_id = emp['id']

            # 1) الأساسي حسب نوع الأجر
            if emp['pay_type'] == 'monthly':
                base = emp['base_salary']
                daily = base / monthly_days if monthly_days > 0 else 0
                hourly = daily / settings['working_hours_daily'] if settings['working_hours_daily'] > 0 else 0
            elif emp['pay_type'] == 'daily':
                daily = emp['daily_rate']
                base = daily * monthly_days
                hourly = daily / settings['working_hours_daily'] if settings['working_hours_daily'] > 0 else 0
            elif emp['pay_type'] == 'hourly':
                hourly = emp['hourly_rate']
                daily = hourly * settings['working_hours_daily']
                base = daily * monthly_days
            else:  # commission
                daily = 0
                hourly = 0
                base = 0

            # 2) البدلات
            allowances = (emp['housing_allowance'] + emp['transport_allowance'] + emp['food_allowance'] +
                          emp['other_allowances'] + emp['danger_allowance'] + emp['phone_allowance'])

            # 3) الحضور - أيام العمل والغياب والتأخير
            c.execute("SELECT * FROM attendance WHERE employee_id=? AND month=?", (emp_id, month))
            att_records = [dict(r) for r in c.fetchall()]
            present_days = sum(1 for a in att_records if a['status'] in ('present','late'))
            absent_days = sum(1 for a in att_records if a['status'] == 'absent')
            late_days = sum(1 for a in att_records if a['status'] == 'late')
            sick_days = sum(1 for a in att_records if a['status'] == 'sick')
            leave_days = sum(1 for a in att_records if a['status'] == 'leave')

            # 4) الإضافي
            c.execute("""SELECT COALESCE(SUM(hours),0) as hrs, COALESCE(SUM(amount),0) as amt
                         FROM overtime WHERE employee_id=? AND month=?""", (emp_id, month))
            ot = dict(c.fetchone())
            overtime_amt = ot['amt']

            # 5) العمولات
            c.execute("""SELECT COALESCE(SUM(amount),0) as amt FROM commissions WHERE employee_id=? AND month=?""", (emp_id, month))
            commissions = float(c.fetchone()['amt'])

            # 6) المستحقات
            base_allowances = base + allowances
            gross = base_allowances + overtime_amt + commissions

            # 7) التأمينات الاجتماعية
            si_employee = 0
            si_employer = 0
            if emp['social_insurance_enabled']:
                ins_floor = settings['insurance_floor']
                ins_ceiling = settings['insurance_ceiling']
                ins_base = min(max(base, ins_floor), ins_ceiling) if ins_ceiling else max(base, ins_floor)
                emp_ratio = emp['social_insurance_employee_ratio'] if emp['social_insurance_employee_ratio'] else settings['insurance_employee_ratio']
                empl_ratio = emp['social_insurance_employer_ratio'] if emp['social_insurance_employer_ratio'] else settings['insurance_employer_ratio']
                si_employee = ins_base * emp_ratio / 100
                si_employer = ins_base * empl_ratio / 100

            # 8) ضريبة كسب العمل (على الدخل السنوي)
            income_tax = 0
            if emp['income_tax_enabled']:
                annual = gross * 12
                exempt = emp['tax_exempt_amount'] if emp['tax_exempt_amount'] else settings['tax_exempt_default']
                income_tax = self.calc_income_tax(annual, exempt)

            # 9) سلف (أقساط الشهر)
            c.execute("""SELECT COALESCE(SUM(installment_amount),0) as amt FROM advances
                         WHERE employee_id=? AND status='active' AND date LIKE ?""", (emp_id, month+'%'))
            advance_installments = float(c.fetchone()['amt'])

            # 10) خصومات الغياب
            absence_deduction = absent_days * daily * (settings['absence_deduction_percent']/100)
            # خصم اليوم الكامل للإجازة بدون أجر
            c.execute("""SELECT COALESCE(SUM(days),0) as d FROM leave_requests
                         WHERE employee_id=? AND leave_type='unpaid' AND status='approved' AND substr(start_date,1,7)=?""", (emp_id, month))
            unpaid_days = float(c.fetchone()['d'])
            absence_deduction += unpaid_days * daily

            # خصم التأخير
            late_deduction = late_days * settings['late_deduction_per_hour'] * settings['working_hours_daily']

            # 11) خصومات يدوية (جزاءات، قروض...)
            c.execute("""SELECT COALESCE(SUM(amount),0) as amt FROM deductions WHERE employee_id=? AND month=?""", (emp_id, month))
            other_deductions = float(c.fetchone()['amt'])
            manual_earnings = 0

            # 12) حوافز/خصومات جماعية
            c.execute("SELECT * FROM bulk_incentives WHERE month=?", (month,))
            for bi in c.fetchall():
                spe = []
                if bi['specific_employees']:
                    try:
                        spe = json.loads(bi['specific_employees'])
                    except Exception:
                        spe = []
                if spe and str(emp_id) not in [str(s) for s in spe]:
                    continue
                amt = bi['per_employee_amount'] or 0
                if bi['kind'] == 'bonus':
                    manual_earnings += amt
                else:
                    other_deductions += amt

            gross = gross + manual_earnings

            total_deductions = (si_employee + income_tax/12 + advance_installments + absence_deduction +
                                late_deduction + other_deductions)
            net = gross - total_deductions

            results.append({
                'employee_id': emp_id,
                'emp_code': emp['emp_code'],
                'name': emp['name'],
                'dept_name': emp.get('dept_name',''),
                'position': emp['position'],
                'pay_type': emp['pay_type'],
                'base': round(base,2),
                'daily': round(daily,2),
                'hourly': round(hourly,2),
                'allowances': round(allowances,2),
                'overtime_amt': round(overtime_amt,2),
                'commissions': round(commissions,2),
                'bonus': round(manual_earnings,2),
                'gross': round(gross,2),
                'si_employee': round(si_employee,2),
                'si_employer': round(si_employer,2),
                'income_tax': round(income_tax/12,2),
                'advance_installments': round(advance_installments,2),
                'absence_deduction': round(absence_deduction,2),
                'late_deduction': round(late_deduction,2),
                'other_deductions': round(other_deductions,2),
                'total_deductions': round(total_deductions,2),
                'net': round(net,2),
                'present_days': present_days,
                'absent_days': absent_days,
                'late_days': late_days,
                'sick_days': sick_days,
                'leave_days': leave_days,
                'overtime_hours': ot['hrs']
            })
        return results

    def save_payroll(self, month, records):
        c = self._cur()
        for r in records:
            c.execute("""INSERT OR REPLACE INTO payroll_proof
                (employee_id,month,gross_salary,total_allowances,overtime_amount,commission_amount,
                 total_earnings,social_insurance_employee,social_insurance_employer,income_tax,
                 advance_installments,absence_deduction,late_deduction,other_deductions,total_deductions,
                 net_salary,days_worked,status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (r['employee_id'], month, r['base'], r['allowances'], r['overtime_amt'], r['commissions'],
                 r['gross'], r['si_employee'], r['si_employer'], r['income_tax']*12,
                 r['advance_installments'], r['absence_deduction'], r['late_deduction'],
                 r['other_deductions'], r['total_deductions'], r['net'],
                 r['present_days'], 'draft'))
        self.conn.commit()

    def confirm_payroll(self, month, user):
        c = self._cur()
        c.execute("UPDATE payroll_proof SET status='confirmed' WHERE month=?", (month,))
        # تقدم أقساط السلف: زيادة القسط الحالي وتحديث المتبقي لكل سلفة نشطة في هذا الشهر
        c.execute("""SELECT id, installment_amount FROM advances
                     WHERE status='active' AND date LIKE ?""", (month+'%',))
        for adv in c.fetchall():
            new_remaining = max(0, round(float(adv['installment_amount']), 2))
            c.execute("""UPDATE advances SET current_installment=current_installment+1,
                         remaining=remaining-?, status=CASE WHEN current_installment+1>=installment_count
                         THEN 'done' ELSE 'active' END WHERE id=?""", (new_remaining, adv['id']))
        self.conn.commit()

    def get_saved_payroll(self, month):
        c = self._cur()
        c.execute("""SELECT p.*, e.name, e.emp_code, e.pay_type, d.name as dept_name
            FROM payroll_proof p JOIN employees e ON p.employee_id=e.id
            LEFT JOIN departments d ON e.department_id=d.id
            WHERE p.month=? ORDER BY e.name""", (month,))
        return [dict(r) for r in c.fetchall()]

    # ==================== DASHBOARD ====================
    def get_dashboard_stats(self):
        c = self._cur()
        stats = {}
        c.execute("SELECT COUNT(*) cnt FROM employees WHERE status='active'")
        stats['employees'] = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) cnt FROM departments WHERE active=1")
        stats['departments'] = c.fetchone()['cnt']
        c.execute("SELECT COALESCE(SUM(base_salary),0) s FROM employees WHERE status='active'")
        stats['total_monthly_salary'] = c.fetchone()['s']
        c.execute("SELECT COUNT(*) cnt FROM leave_requests WHERE status='pending'")
        stats['pending_leaves'] = c.fetchone()['cnt']
        c.execute("SELECT COALESCE(SUM(remaining),0) s FROM advances WHERE status='active'")
        stats['active_advances'] = c.fetchone()['s']
        c.execute("SELECT COALESCE(SUM(amount),0) s FROM overtime WHERE month=?", (datetime.now().strftime('%Y-%m'),))
        stats['month_overtime'] = c.fetchone()['s']
        return stats

    # ==================== AUDIT LOG ====================
    def log_audit(self, action, entity='', entity_id=None, details=''):
        try:
            c = self._cur()
            c.execute("""INSERT INTO audit_log (user_id,username,action,entity,entity_id,details,ip_address)
                VALUES (?,?,?,?,?,?,?)""",
                (getattr(self, '_uid', None), getattr(self, '_uname', ''),
                 action, entity, entity_id, details[:2000], getattr(self, '_ip', '')))
            self.conn.commit()
        except Exception:
            pass

    def get_audit_log(self, limit=200, day=''):
        c = self._cur()
        if day:
            c.execute("SELECT * FROM audit_log WHERE substr(created_at,1,10)=? ORDER BY created_at DESC, id DESC LIMIT ?", (day, limit))
        else:
            c.execute("SELECT * FROM audit_log ORDER BY created_at DESC, id DESC LIMIT ?", (limit,))
        return [dict(r) for r in c.fetchall()]

    # ==================== CONTRACTS ====================
    def add_contract(self, d):
        c = self._cur()
        c.execute("""INSERT INTO contracts (employee_id,contract_type,contract_number,start_date,end_date,
            salary,allowance_details,notes,status) VALUES (?,?,?,?,?,?,?,?,?)""",
            (d['employee_id'], d.get('contract_type','permanent'), d.get('contract_number',''),
             d['start_date'], d.get('end_date',''), d.get('salary',0),
             d.get('allowance_details',''), d.get('notes',''), d.get('status','active')))
        self.conn.commit()
        return c.lastrowid

    def update_contract(self, cid, d):
        c = self._cur()
        c.execute("""UPDATE contracts SET contract_type=?,contract_number=?,start_date=?,end_date=?,
            salary=?,allowance_details=?,notes=?,status=? WHERE id=?""",
            (d.get('contract_type','permanent'), d.get('contract_number',''), d['start_date'],
             d.get('end_date',''), d.get('salary',0), d.get('allowance_details',''),
             d.get('notes',''), d.get('status','active'), cid))
        self.conn.commit()

    def get_contracts(self, emp_id=None):
        c = self._cur()
        q = """SELECT co.*, e.name as emp_name, e.emp_code
               FROM contracts co JOIN employees e ON co.employee_id=e.id WHERE 1=1"""
        params = []
        if emp_id:
            q += " AND co.employee_id=?"
            params.append(emp_id)
        q += " ORDER BY co.start_date DESC"
        c.execute(q, params)
        return [dict(r) for r in c.fetchall()]

    def get_expiring_contracts(self, days=30):
        c = self._cur()
        q = """SELECT co.*, e.name as emp_name, e.emp_code
               FROM contracts co JOIN employees e ON co.employee_id=e.id
               WHERE co.end_date IS NOT NULL AND co.end_date!='' AND co.status='active'
               AND date(co.end_date) BETWEEN date('now','localtime') AND date('now','localtime', ?)
               ORDER BY co.end_date"""
        c.execute(q, (f'+{days} days',))
        return [dict(r) for r in c.fetchall()]

    def delete_contract(self, cid):
        c = self._cur()
        c.execute("DELETE FROM contracts WHERE id=?", (cid,))
        self.conn.commit()

    # ==================== PAYROLL SIGNATURES ====================
    def sign_payroll(self, emp_id, month, slip_number, gross, net, signature_data, ip='', notes=''):
        c = self._cur()
        c.execute("""INSERT OR REPLACE INTO payroll_signatures
            (employee_id,month,slip_number,gross_salary,net_salary,signature_data,sign_date,signed_by_ip,notes)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (emp_id, month, slip_number, gross, net, signature_data,
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip, notes))
        self.conn.commit()

    def get_signatures(self, month=None, emp_id=None):
        c = self._cur()
        q = """SELECT s.*, e.name as emp_name, e.emp_code
               FROM payroll_signatures s JOIN employees e ON s.employee_id=e.id WHERE 1=1"""
        params = []
        if month:
            q += " AND s.month=?"
            params.append(month)
        if emp_id:
            q += " AND s.employee_id=?"
            params.append(emp_id)
        q += " ORDER BY s.sign_date DESC"
        c.execute(q, params)
        return [dict(r) for r in c.fetchall()]

    def has_signed(self, emp_id, month):
        c = self._cur()
        c.execute("SELECT COUNT(*) cnt FROM payroll_signatures WHERE employee_id=? AND month=?", (emp_id, month))
        return c.fetchone()['cnt'] > 0

    # ==================== BULK INCENTIVES ====================
    def add_bulk_incentive(self, d, by_user=''):
        c = self._cur()
        c.execute("""INSERT INTO bulk_incentives (month,kind,description,per_employee_amount,specific_employees,created_by)
            VALUES (?,?,?,?,?,?)""",
            (d['month'], d.get('kind','bonus'), d.get('description',''), d.get('per_employee_amount',0),
             d.get('specific_employees',''), by_user))
        self.conn.commit()
        return c.lastrowid

    def get_bulk_incentives(self, month=None):
        c = self._cur()
        q = "SELECT * FROM bulk_incentives WHERE 1=1"
        params = []
        if month:
            q += " AND month=?"
            params.append(month)
        q += " ORDER BY created_at DESC"
        c.execute(q, params)
        return [dict(r) for r in c.fetchall()]

    def delete_bulk_incentive(self, bid):
        c = self._cur()
        c.execute("DELETE FROM bulk_incentives WHERE id=?", (bid,))
        self.conn.commit()

    # ==================== DASHBOARD EXTRAS ====================
    def get_pay_type_distribution(self):
        c = self._cur()
        c.execute("""SELECT pay_type as type, COUNT(*) cnt, COALESCE(SUM(base_salary),0) base
                     FROM employees WHERE status='active' GROUP BY pay_type""")
        return [dict(r) for r in c.fetchall()]

    def get_monthly_budget(self, month):
        c = self._cur()
        data = self.calculate_payroll(month)
        return {
            'net': round(sum(r['net'] for r in data), 2),
            'gross': round(sum(r['gross'] for r in data), 2),
            'deductions': round(sum(r['total_deductions'] for r in data), 2),
            'count': len(data),
            'si_employer': round(sum(r['si_employer'] for r in data), 2),
        }

    # دالة مساعدة للتحقق من الحوافز الجماعية (تُستدعى بعد الحفظ)
    def apply_bulk_to_payroll(self, month):
        return True
