import streamlit as st
import sqlite3, os, io, csv
from datetime import date, datetime
import pandas as pd

st.set_page_config(page_title='TF Matematika', page_icon='🎓', layout='wide')
DB=os.environ.get('TF_DB_PATH','tf_matematika.db')

def db():
    c=sqlite3.connect(DB,timeout=15)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY, name TEXT NOT NULL, year TEXT NOT NULL, UNIQUE(name,year));
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, index_no TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL, email TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS enrollments(course_id INTEGER NOT NULL, student_id INTEGER NOT NULL, activity REAL DEFAULT 0 CHECK(activity BETWEEN 0 AND 10), PRIMARY KEY(course_id,student_id), FOREIGN KEY(course_id) REFERENCES courses(id), FOREIGN KEY(student_id) REFERENCES students(id));
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('K1','K2','ZI')), is_repeat INTEGER NOT NULL DEFAULT 0, session TEXT NOT NULL, held_on TEXT NOT NULL, FOREIGN KEY(course_id) REFERENCES courses(id));
        CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL, student_id INTEGER NOT NULL, points REAL NOT NULL, created_at TEXT NOT NULL, UNIQUE(event_id,student_id), FOREIGN KEY(event_id) REFERENCES events(id), FOREIGN KEY(student_id) REFERENCES students(id));
        CREATE TABLE IF NOT EXISTS exceptions(id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL, student_id INTEGER NOT NULL, event_id INTEGER NOT NULL, granted_at TEXT NOT NULL, reason TEXT NOT NULL, revoked_at TEXT, UNIQUE(student_id,event_id), FOREIGN KEY(event_id) REFERENCES events(id));
        CREATE TABLE IF NOT EXISTS passed(id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL, student_id INTEGER NOT NULL, points REAL NOT NULL, grade INTEGER NOT NULL CHECK(grade BETWEEN 6 AND 10), passed_on TEXT NOT NULL, session TEXT NOT NULL, confirmed_at TEXT NOT NULL, UNIQUE(course_id,student_id));
        ''')
        c.execute("INSERT OR IGNORE INTO courses(name,year) VALUES ('Matematika 1','2025/26')")

def rows(sql,args=()):
    with db() as c:return [dict(r) for r in c.execute(sql,args).fetchall()]

def execute(sql,args=()):
    with db() as c:c.execute(sql,args)

def grade(total):
    for p,g in [(91,10),(81,9),(71,8),(61,7),(51,6)]:
        if total>=p:return g
    return 5

def status(cid,sid):
    rr=rows('''SELECT e.kind,e.is_repeat,a.points,e.id AS event_id FROM attempts a JOIN events e ON e.id=a.event_id WHERE e.course_id=? AND a.student_id=? ORDER BY e.held_on,e.id''',(cid,sid))
    best={k:max([r['points'] for r in rr if r['kind']==k],default=None) for k in ['K1','K2','ZI']}
    activity=rows('SELECT activity FROM enrollments WHERE course_id=? AND student_id=?',(cid,sid))
    act=float(activity[0]['activity']) if activity else 0
    total=round(sum(x or 0 for x in best.values())+act,2)
    ready=all(best[k] is not None for k in best)
    eligible=ready and best['K1']+best['K2']>=30 and best['ZI']>=16 and total>=51
    count=sum(1 for r in rr if r['is_repeat'] and r['kind'] in ('K1','K2'))
    return best,act,total,(grade(total) if eligible else 5),count

init()
st.title('🎓 TF Matematika')
st.caption('Nezavisna aplikacija za predmete, kolokvijume, ispitne rokove i položenе ispite · probna verzija')
st.warning('Probna verzija: koristite samo izmišljene podatke. Lokalna SQLite baza nije trajno skladište na Streamlit Community Cloud-u. Za stvarne studentske podatke potrebni su autentifikacija, ovlašćenja i zaštićena cloud baza.')

with st.sidebar:
    cs=rows('SELECT * FROM courses ORDER BY year DESC,name')
    chosen=st.selectbox('Predmet i školska godina',[c['id'] for c in cs],format_func=lambda x:next(f"{c['name']} — {c['year']}" for c in cs if c['id']==x))
    course=next(c for c in cs if c['id']==chosen)
    st.caption('K1: 30 · K2: 30 · ZI: 30 · aktivnost: 10')
    st.caption('Uslovi: K1+K2 ≥ 30; ZI ≥ 16; ukupno ≥ 51')

tabs=st.tabs(['Pregled','Studenti','Događaji i rokovi','Unos rezultata','Izuzeci','Položeni ispiti','Izvoz'])

with tabs[0]:
    st.subheader('Aktivni studenti')
    enrolled=rows('''SELECT s.id,s.index_no,s.full_name FROM enrollments en JOIN students s ON s.id=en.student_id WHERE en.course_id=? AND NOT EXISTS(SELECT 1 FROM passed p WHERE p.course_id=en.course_id AND p.student_id=s.id) ORDER BY s.full_name''',(chosen,))
    view=[]
    for s in enrolled:
        b,a,t,g,n=status(chosen,s['id'])
        view.append({'Indeks':s['index_no'],'Student':s['full_name'],'K1':b['K1'],'K2':b['K2'],'ZI':b['ZI'],'Aktivnost':a,'Ukupno':t,'Predlog ocene':g,'Ponovljeni izlasci':f'{n}/3','Preostalo':max(0,3-n)})
    st.dataframe(pd.DataFrame(view),hide_index=True,use_container_width=True)
    st.caption('Najbolji ostvareni rezultat za svaki tip provere ulazi u zbir. Ponovljeni izlasci broje se zajednički za K1 i K2; redovni ne troše limit.')

with tabs[1]:
    st.subheader('Predmeti i studenti')
    with st.form('new_course'):
        a,b=st.columns(2); name=a.text_input('Naziv predmeta',value='Matematika 1');year=b.text_input('Školska godina',value='2025/26')
        if st.form_submit_button('Dodaj predmet'):
            try:execute('INSERT INTO courses(name,year) VALUES (?,?)',(name.strip(),year.strip()));st.success('Predmet dodat. Osvežite stranicu za izbor.')
            except sqlite3.IntegrityError:st.error('Predmet i godina već postoje.')
    with st.form('student'):
        a,b,c=st.columns(3);idx=a.text_input('Broj indeksa');nm=b.text_input('Ime i prezime');email=c.text_input('Email (opciono)')
        if st.form_submit_button('Dodaj / upiši na predmet'):
            if not idx.strip() or not nm.strip():st.error('Indeks i ime su obavezni.')
            else:
                with db() as con:
                    con.execute('INSERT OR IGNORE INTO students(index_no,full_name,email) VALUES (?,?,?)',(idx.strip(),nm.strip(),email.strip()))
                    sid=con.execute('SELECT id FROM students WHERE index_no=?',(idx.strip(),)).fetchone()['id']
                    con.execute('INSERT OR IGNORE INTO enrollments(course_id,student_id) VALUES (?,?)',(chosen,sid))
                st.success('Student upisan.')
    people=rows('SELECT s.id,s.index_no,s.full_name,en.activity FROM enrollments en JOIN students s ON s.id=en.student_id WHERE en.course_id=? ORDER BY s.full_name',(chosen,))
    if people:
        with st.form('activity'):
            sid=st.selectbox('Student za aktivnost',[s['id'] for s in people],format_func=lambda x:next(f"{s['index_no']} — {s['full_name']}" for s in people if s['id']==x))
            current=next(s['activity'] for s in people if s['id']==sid)
            act=st.number_input('Aktivnost (0–10)',0.0,10.0,float(current),0.5)
            if st.form_submit_button('Sačuvaj aktivnost'):
                execute('UPDATE enrollments SET activity=? WHERE course_id=? AND student_id=?',(act,chosen,sid));st.success('Sačuvano.')

with tabs[2]:
    st.subheader('Kreiraj događaj')
    st.info('Redovni K1 i K2 imaju zasebne događaje. Ponovljeni kolokvijum nosi naziv predmeta, godinu, rok i oznaku K1 ili K2.')
    with st.form('event'):
        typ=st.selectbox('Provera',['K1','K2','ZI']);rep=st.checkbox('Ponovljeni kolokvijum',disabled=False)
        session=st.text_input('Ispitni rok / događaj',value='Aprilski rok');dt=st.date_input('Datum održavanja',value=date.today())
        if st.form_submit_button('Kreiraj događaj'):
            if rep and typ=='ZI':st.error('Ograničenje ponavljanja važi samo za K1 i K2.')
            elif rep and not all(rows('SELECT id FROM events WHERE course_id=? AND kind=? AND is_repeat=0',(chosen,k)) for k in ['K1','K2']):st.error('Prvo kreirajte oba redovna kolokvijuma.')
            else:
                execute('INSERT INTO events(course_id,kind,is_repeat,session,held_on) VALUES (?,?,?,?,?)',(chosen,typ,int(rep),session.strip(),dt.isoformat()));st.success('Događaj kreiran.')
    ev=rows('SELECT * FROM events WHERE course_id=? ORDER BY held_on,id',(chosen,))
    for e in ev:
        label=('Ponovljeni kolokvijum' if e['is_repeat'] else e['kind'])+f" — {course['name']} — {course['year']} — {e['session']} — {e['kind']} — {e['held_on']}"
        st.write(label)

with tabs[3]:
    st.subheader('Unos bodova')
    ev=rows('SELECT * FROM events WHERE course_id=? ORDER BY held_on DESC,id DESC',(chosen,))
    people=rows('SELECT s.id,s.index_no,s.full_name FROM enrollments en JOIN students s ON s.id=en.student_id WHERE en.course_id=?',(chosen,))
    if not ev or not people:st.info('Najpre unesite studente i kreirajte događaj.')
    else:
        eid=st.selectbox('Događaj',[e['id'] for e in ev],format_func=lambda x:next(f"{'Ponovljeni ' if e['is_repeat'] else ''}{e['kind']} · {e['session']} · {e['held_on']}" for e in ev if e['id']==x))
        e=next(e for e in ev if e['id']==eid)
        sid=st.selectbox('Student',[s['id'] for s in people],format_func=lambda x:next(f"{s['index_no']} — {s['full_name']}" for s in people if s['id']==x),key='attempt_sid')
        old=rows('SELECT * FROM attempts WHERE event_id=? AND student_id=?',(eid,sid))
        b,a,t,g,n=status(chosen,sid)
        st.write(f'Iskorišćeno ponovljenih izlazaka: **{n}/3**')
        if old:st.info(f"Postojeći rezultat: {old[0]['points']} poena. Ispravka istog događaja ne troši novi izlazak.")
        limit=30.0
        points=st.number_input('Bodovi',0.0,limit,float(old[0]['points']) if old else 0.0,0.5)
        exception=rows('SELECT * FROM exceptions WHERE course_id=? AND student_id=? AND event_id=? AND revoked_at IS NULL',(chosen,sid,eid))
        blocked=bool(e['is_repeat'] and e['kind'] in ('K1','K2') and n>=3 and not old and not exception)
        passed=bool(rows('SELECT id FROM passed WHERE course_id=? AND student_id=?',(chosen,sid)))
        if blocked:st.error('Blokirano: tri ponovljena izlaska su iskorišćena. Odobrite izuzetak u kartici Izuzeci za ovaj događaj.')
        if passed:st.error('Student je već evidentiran kao položio ispit.')
        if st.button('Sačuvaj rezultat',disabled=blocked or passed):
            try:
                execute('INSERT INTO attempts(event_id,student_id,points,created_at) VALUES (?,?,?,?) ON CONFLICT(event_id,student_id) DO UPDATE SET points=excluded.points',(eid,sid,points,datetime.now().isoformat(timespec='seconds')))
                st.success('Rezultat sačuvan.')
            except sqlite3.IntegrityError as ex:st.error(str(ex))

with tabs[4]:
    st.subheader('Jednokratno skidanje blokade')
    st.caption('Izuzetak važi samo za izabranog studenta i događaj. Ne briše istoriju prethodnih izlazaka.')
    people=rows('SELECT s.id,s.index_no,s.full_name FROM enrollments en JOIN students s ON s.id=en.student_id WHERE en.course_id=?',(chosen,))
    repeats=rows("SELECT * FROM events WHERE course_id=? AND is_repeat=1 AND kind IN ('K1','K2') ORDER BY held_on DESC",(chosen,))
    if people and repeats:
        with st.form('exception'):
            sid=st.selectbox('Student',[s['id'] for s in people],format_func=lambda x:next(f"{s['index_no']} — {s['full_name']}" for s in people if s['id']==x),key='exc_sid')
            eid=st.selectbox('Događaj',[e['id'] for e in repeats],format_func=lambda x:next(f"{e['kind']} · {e['session']} · {e['held_on']}" for e in repeats if e['id']==x))
            reason=st.text_input('Obrazloženje odobrenja')
            if st.form_submit_button('Odobri dodatni izlazak'):
                if not reason.strip():st.error('Unesite obrazloženje.')
                elif rows('SELECT id FROM passed WHERE course_id=? AND student_id=?',(chosen,sid)):st.error('Student je već položio.')
                else:
                    execute('INSERT INTO exceptions(course_id,student_id,event_id,granted_at,reason,revoked_at) VALUES (?,?,?,?,?,NULL) ON CONFLICT(student_id,event_id) DO UPDATE SET granted_at=excluded.granted_at,reason=excluded.reason,revoked_at=NULL',(chosen,sid,eid,datetime.now().isoformat(timespec='seconds'),reason.strip()))
                    st.success('Izuzetak odobren.')
    exceptions=rows('''SELECT x.*,s.index_no,e.kind,e.session,e.held_on FROM exceptions x JOIN students s ON s.id=x.student_id JOIN events e ON e.id=x.event_id WHERE x.course_id=? ORDER BY x.id DESC''',(chosen,))
    for x in exceptions:
        st.write(f"{x['index_no']} · {x['kind']} · {x['session']} · {x['held_on']} · {'Opozvano' if x['revoked_at'] else 'Aktivno'} · {x['reason']}")
        if not x['revoked_at'] and not rows('SELECT id FROM attempts WHERE student_id=? AND event_id=?',(x['student_id'],x['event_id'])):
            if st.button('Opozovi izuzetak',key=f"revoke_{x['id']}"):
                execute('UPDATE exceptions SET revoked_at=? WHERE id=?',(datetime.now().isoformat(timespec='seconds'),x['id']));st.rerun()

with tabs[5]:
    st.subheader('Potvrda položenog ispita')
    people=rows('''SELECT s.id,s.index_no,s.full_name FROM enrollments en JOIN students s ON s.id=en.student_id WHERE en.course_id=? AND NOT EXISTS(SELECT 1 FROM passed p WHERE p.course_id=en.course_id AND p.student_id=s.id)''',(chosen,))
    if people:
        sid=st.selectbox('Student',[s['id'] for s in people],format_func=lambda x:next(f"{s['index_no']} — {s['full_name']}" for s in people if s['id']==x),key='pass_sid')
        b,a,total,g,n=status(chosen,sid)
        st.write(f'K1: {b["K1"]} · K2: {b["K2"]} · ZI: {b["ZI"]} · Aktivnost: {a} · Ukupno: **{total}** · Predlog ocene: **{g}**')
        with st.form('pass'):
            dt=st.date_input('Datum polaganja',date.today(),key='pass_date')
            session=st.text_input('Ispitni rok',value='Aprilski rok',key='pass_session')
            confirmed=st.checkbox('Potvrđujem konačnu ocenu')
            if st.form_submit_button('Potvrdi položen ispit'):
                if g==5:st.error('Student trenutno ne ispunjava uslove za prolaz.')
                elif not confirmed or not session.strip():st.error('Potvrdite ocenu i navedite rok.')
                else:
                    execute('INSERT INTO passed(course_id,student_id,points,grade,passed_on,session,confirmed_at) VALUES (?,?,?,?,?,?,?)',(chosen,sid,total,g,dt.isoformat(),session.strip(),datetime.now().isoformat(timespec='seconds')))
                    st.success('Ispit potvrđen i premešten u arhivu položenih.')
    passed=rows('''SELECT p.*,s.index_no,s.full_name FROM passed p JOIN students s ON s.id=p.student_id WHERE p.course_id=? ORDER BY p.passed_on DESC''',(chosen,))
    if passed:
        sessions=sorted({p['session'] for p in passed});filter_session=st.selectbox('Filtriraj po roku',['Svi rokovi']+sessions)
        filtered=[p for p in passed if filter_session=='Svi rokovi' or p['session']==filter_session]
        st.dataframe(pd.DataFrame([{'Indeks':p['index_no'],'Student':p['full_name'],'Bodovi':p['points'],'Ocena':p['grade'],'Datum':p['passed_on'],'Rok':p['session']} for p in filtered]),hide_index=True,use_container_width=True)
        with st.expander('Ispravka pogrešne potvrde'):
            pid=st.selectbox('Vrati u aktivne',[p['id'] for p in passed],format_func=lambda x:next(f"{p['index_no']} — {p['full_name']}" for p in passed if p['id']==x))
            confirm=st.checkbox('Potvrđujem vraćanje u aktivne')
            if st.button('Vrati u aktivne',disabled=not confirm):
                execute('DELETE FROM passed WHERE id=?',(pid,));st.success('Student vraćen u aktivnu evidenciju.');st.rerun()

with tabs[6]:
    st.subheader('Izvoz i rezervna kopija')
    tables={'Studenti':rows('SELECT * FROM students'),'Predmeti':rows('SELECT * FROM courses'),'Upisi':rows('SELECT * FROM enrollments'),'Dogadjaji':rows('SELECT * FROM events'),'Rezultati':rows('SELECT * FROM attempts'),'Izuzeci':rows('SELECT * FROM exceptions'),'Polozeni':rows('SELECT * FROM passed')}
    output=io.BytesIO()
    with pd.ExcelWriter(output,engine='xlsxwriter') as writer:
        for name,data in tables.items():pd.DataFrame(data if data else [{'Nema podataka':''}]).to_excel(writer,index=False,sheet_name=name)
    st.download_button('Preuzmi Excel evidenciju',output.getvalue(),file_name='tf_matematika_evidencija.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    if os.path.isfile(DB):
        with open(DB,'rb') as f:st.download_button('Preuzmi kompletnu SQLite bazu',f.read(),file_name='tf_matematika_backup.db',mime='application/octet-stream')
    st.caption('Izvozite redovno. Na besplatnom Streamlit hostingu lokalni fajl baze može nestati pri ponovnom pokretanju.')
