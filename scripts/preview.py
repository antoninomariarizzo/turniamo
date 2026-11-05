"""Render the local HTML UI with fictitious data, without touching the live DB."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu')
from datetime import date,timedelta
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QEventLoop,QTimer,QSize
from PySide6.QtGui import QImage,QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from turniamo.domain import Activity as A,Assignment
from turniamo.storage import Store
from turniamo.web_ui import MainWindow
from turniamo.exports import document_html,export_pdf,export_excel

output=Path(__file__).resolve().parents[1]/'test-output'/'preview'
output.mkdir(parents=True,exist_ok=True)
app=QApplication([])
store=Store(':memory:')
start=date(2026,12,7)
names=[f'Medico demo {index:02d}' for index in range(1,13)]
doctors=[store.save_doctor(n) for n in names]
store.create_week(start);store.set_setting('last_week',start.isoformat())
counter=0
def add(day,activity,index,paid=False,role='',name=''):
    global counter
    counter+=1
    store.save_assignment(Assignment(str(counter),day,activity,doctors[index],paid,role,name))
for n in range(7):
    day=start+timedelta(days=n)
    if n<5:
        add(day,A.SURGERY_URGENT,n,role='training' if n==0 else '',name='Persona demo' if n==0 else '')
        add(day,A.SURGERY_URGENT,(n+1)%5)
        add(day,A.SURGERY_2,(n+2)%5)
        add(day,A.WARD,5)
        if n%2==0:add(day,A.WARD_HELP,6)
        add(day,A.WEEK_SERVICE,7)
        add(day,A.CLINIC_PM,n,paid=n==2)
        add(day,A.CLINIC_AM,8)
    add(day,A.DAY_DUTY,9 if n%2==0 else 10)
    add(day,A.NIGHT_DUTY,10 if n%2==0 else 9,paid=n==6)
    add(day,A.ON_CALL_PM,(n+1)%5,role='reference',name='Referente demo')
add(start+timedelta(days=5),A.ON_CALL_AM,11)
add(start,A.HOLIDAY,11);add(start+timedelta(days=1),A.RECOVERY,11)
window=MainWindow(store);window.show()
def js(expression):
    result=[];loop=QEventLoop()
    window.view.page().runJavaScript(expression,lambda value:(result.append(value),loop.quit()))
    QTimer.singleShot(3000,loop.quit);loop.exec()
    return result[0] if result else None
for attempt in range(150):
    if js('window.turniamoReady === true'):break
    QTest.qWait(50)
else:raise RuntimeError('HTML UI failed to load')
QTest.qWait(250)
window.grab().save(str(output/'schedule-it.png'))
js("document.querySelector('[data-activity=surgery_urgent]').click()")
QTest.qWait(200)
window.grab().save(str(output/'dropdown-it.png'))
js("document.querySelector('[data-tab=doctors]').click()")
QTest.qWait(100);window.grab().save(str(output/'doctors-it.png'))
js("document.querySelector('[data-tab=summary]').click()")
QTest.qWait(100);window.grab().save(str(output/'summary-it.png'))
for language in ('it','en'):
    context=store.week_context(start);roster=store.week_doctors(start)
    path=output/f'schedule-{language}.pdf'
    export_pdf(path,document_html(start,context,roster,language))
    export_excel(output/f'schedule-{language}.xlsx',start,context,roster,language)
    pdf=QPdfDocument();pdf.load(str(path));print(language,'PDF pages:',pdf.pageCount())
    for page in range(pdf.pageCount()):
        rendered=pdf.render(page,QSize(1980,1400))
        canvas=QImage(rendered.size(),QImage.Format.Format_RGB32);canvas.fill(0xFFFFFF)
        painter=QPainter(canvas);painter.drawImage(0,0,rendered);painter.end()
        canvas.save(str(output/f'pdf-{language}-{page+1}.png'))
window.bridge.dispatch('language',{'language':'en'});window.bridge.publish()
QTest.qWait(100);js("document.querySelector('[data-tab=schedule]').click()")
QTest.qWait(100);window.grab().save(str(output/'schedule-en.png'))
window.close();store.close();print(output)
