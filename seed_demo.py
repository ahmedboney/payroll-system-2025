from database import Database
from datetime import datetime
db = Database()

deps = [('الإدارة المالية','محمد حسن','MC-01'),('الموارد البشرية','سارة خالد','HR-01'),
        ('المبيعات','عبد الله عمر','SL-01'),('تكنولوجيا المعلومات','أحمد علي','IT-01'),
        ('التسويق','نور محمود','MK-01'),('الإنتاج','خالد سمير','PR-01')]
dep_ids={}
for name,mgr,cc in deps:
    try: db.add_department(name,mgr,cc)
    except Exception: pass
for d in db.get_departments(True):
    dep_ids[d['name']]=d['id']

emps = [
 ('EMP001','محمد أحمد','الإدارة المالية','محاسب أول','monthly',12000,1500,1000,700,0),
 ('EMP002','سارة خالد','الموارد البشرية','مديرة موارد بشرية','monthly',15000,2000,1200,800,0),
 ('EMP003','عبد الله عمر','المبيعات','مدير مبيعات','monthly',10000,1200,900,600,2.5),
 ('EMP004','أحمد علي','تكنولوجيا المعلومات','مبرمج أول','monthly',18000,2500,1000,900,0),
 ('EMP005','نور محمود','التسويق','مسؤول تسويق','monthly',8500,900,700,500,0),
 ('EMP006','خالد سمير','الإنتاج','فني إنتاج','daily',0,0,0,0,0),
 ('EMP007','مصطفى فاروق','الإنتاج','عامل خط إنتاج','hourly',0,0,0,0,0),
 ('EMP008','يوسف عادل','المبيعات','مندوب مبيعات','commission',0,0,0,0,5.0),
 ('EMP009','حنان إبراهيم','الإدارة المالية','محاسب','monthly',9000,1000,800,600,0),
 ('EMP010','عمر مصطفى','تكنولوجيا المعلومات','محلل نظم','monthly',11000,1300,900,650,0),
]
for code,name,dept,pos,pt,b,h,t,f,c in emps:
    daily = round(b/26,2) if pt=='monthly' and b else (300 if pt=='daily' else 0)
    hourly = round(daily/8,2) if daily else (40 if pt=='hourly' else 0)
    data={'emp_code':code,'name':name,'department_id':dep_ids[dept],'position':pos,
      'national_id':'2'+code,'pay_type':pt,'base_salary':b,'daily_rate':daily,'hourly_rate':hourly,'commission_rate':c,
      'housing_allowance':h,'transport_allowance':t,'food_allowance':f,'other_allowances':0,
      'danger_allowance':300 if dept=='الإنتاج' else 0,'phone_allowance':200 if dept in ['المبيعات','التسويق'] else 0,
      'social_insurance_enabled':1,'income_tax_enabled':1,'social_insurance_employee_ratio':11,
      'social_insurance_employer_ratio':18.75,'tax_exempt_amount':0,'hire_date':'2021-03-15','status':'active'}
    db.add_employee(data)
print('Employees added')

today=datetime.now()
month=today.strftime('%Y-%m')
day=today.day
if day<2: day=15
for e in db.get_employees(status='active'):
    recs=[]
    for d in range(1, min(day,18)+1):
        status='present'
        if e['id']==4 and d in (5,6): status='absent'
        if e['id']==9 and d==10: status='late'
        if e['id']==7 and d in (12,13): status='absent'
        recs.append({'employee_id':e['id'],'date':f"{month}-{d:02d}",'check_in':'09:00','check_out':'17:00','status':status})
    db.bulk_save_attendance(month,recs)
print('Attendance added')

hr_overtime=[(1,8),(2,6),(4,10),(6,12),(8,15)]
for eid,h in hr_overtime:
    emp=db.get_employee(eid)
    daily=emp['base_salary']/26 if emp['pay_type']=='monthly' and emp['base_salary'] else emp['daily_rate']
    rate=round(daily/8*1.5,2)
    db.bulk_save_overtime(month,[{'employee_id':eid,'date':month+'-08','hours':h,'rate_type':'manual','hourly_rate':rate,'amount':round(h*rate,2)}])

for e in db.get_employees(status='active'):
    if e['pay_type']=='commission' or e['commission_rate']:
        rate=e['commission_rate'] or 2.5
        sales=80000
        db.bulk_save_commissions(month,[{'employee_id':e['id'],'date':month+'-15','sales_amount':sales,'rate':rate,'amount':round(sales*rate/100,2)}])

advances=[(2,5000,5),(4,10000,10),(8,3000,3)]
for eid,amt,inst in advances:
    db.add_advance({'employee_id':eid,'amount':amt,'installment_count':inst,'date':today.isoformat()})

db.bulk_save_deductions(month,[
    {'employee_id':5,'date':month+'-03','deduction_type':'جزاء إداري','amount':300,'note':'تأخير عن الدوام'},
    {'employee_id':9,'date':month+'-06','deduction_type':'قرض','amount':500,'note':'قرض شخصي'},
])

print('Sample data ready')
db.conn.close()
