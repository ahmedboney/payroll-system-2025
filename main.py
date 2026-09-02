# -*- coding: utf-8 -*-
# نقطة دخول لإصدار الـ exe: تشغيل السيرفر بدون نافذة CMD وفتح المتصفح تلقائياً
import os, sys

if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

try:
    import app as _app
    _app.run_server()
except Exception:
    import traceback
    try:
        open(os.path.join(os.path.dirname(sys.executable), 'error_log.txt'), 'a', encoding='utf-8').write(traceback.format_exc())
    except Exception:
        pass
