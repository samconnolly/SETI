"""
seti.py

Created on Mon Jul 28 08:48:59 2014

Author: Sam Connolly

Website application for the Southampton Physics & Astronomy SETI Cipher Challenge.
Can be generally used for any forum-based online competition.

To create database with admin account manually:

> from seti import init_db,add_account_manual,config_init_db
> init_db()
> config_init_db()
> add_account_manual('Username','password','true','Institute',['Joe Bloggs'],[25]) 

"""

# import modules
import os
import sqlite3
import time
import datetime
import json
import geocoder
import numpy as np

# logging
import logging      
from logging import FileHandler

# flask
from flask import Flask, request, session, g, redirect, url_for, abort, \
                    render_template, flash, jsonify
# mobile version
from flask.ext.mobility import Mobility
from flask.ext.mobility.decorators import mobile_template

# emailing - only works with python2.7 (many LAMP servers use 2.6, so unused)
#from flask.ext.mail import Mail, Message

# uploads
from werkzeug import secure_filename

# create application
app = Flask(__name__)  # name given in brackets, but providing __name__
                       # is good for single apps, as the name will change
Mobility(app)          # Create mobile version


app.config.from_object(__name__)
# Load default config:
#  set username, password, database, key etc
# MAKE SURE DEBUG IS OFF WHEN LIVE OR USERS CAN EXECUTE CODE ON THE SERVER!
# 'blarg.db' is the name of the SQL database - archived versions (e.g. previous
# years) should have the generic name given in ARCHIVE_DATABASE (also 'blarg.db'
# here).
# Keep your secret key secret. To generate a new one (which you MUST DO) use:
# > import os
# > os.urandom(24)
app.config.update(dict(
    DATABASE=os.path.join(app.root_path,'blarg.db'), 
    ARCHIVE_DATABASE=os.path.join(app.root_path,'{0}/blarg.db'),
    DEBUG=False,    # !!! change this to false before release! !!!
    ACTIVE_DAY=0,
    REGISTRATION_OPEN=True,
    MAIL_SERVER = 'smtp.soton.ac.uk',           # only needed if using emailing
    MAIL_PORT = 25,                             #  |
    MAIL_USE_TLS = True,                        #  |
    MAIL_USE_SSL = False,                       #  |
    MAIL_USERNAME = 'seti@soton.ac.uk',         #  |
    MAIL_PASSWORD = 'password',                 #  V
    MAIL_DEFAULT_SENDER = 'seti@soton.ac.uk',   # emails' sender appears as this
    UPLOAD_FOLDER = '/var/www/seti/htdocs/static/uploads/',# uploads stored here
    SESSION_COOKIE_SECURE = True,               # MUST be True for https
    SECRET_KEY = '\x1e\xf7\x8f~\x15-p\xddT\xb5\x00\x15\xd8w\xfb\x8c\xf7g9\xd3_\xbb\xcb\x99',
    SESSION_TYPE = 'filesystem',
    CIPHERS = ['cipher1.txt',\  # These are the file names of the 10 ciphers.
                'cipher2.txt',\ # ciphers 1-5 are the science forum ciphers
                'cipher3.txt',\ # for days 1-5, ciphers 6-10 are the media
                'cipher4.txt',\ # forum ciphers for days 1-5 respectively
                'cipher5.txt',\
                'cipher6.txt',\
                'cipher7.txt',\
                'cipher8.txt',\
                'cipher9.txt',\
                'cipher10.txt'],
    RELEASED = 0,
    START_DATE = '2016-06-06',  # Start date and time of the competition (allows
    START_TIME = '09:00:00',    # auto opening of the forums)
    END_TIME = '11:46:00'       # end time
    )) 

# uncomment for emailing
#mail = Mail(app)
#sess = Session(app)

# file upload types allowed
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'JPG', 'jpeg','JPEG', 'gif','mp4','ogg','mp3','wav'])

# override config from an environment variable,
#    to give var pointing to config file
app.config.from_envvar('BLARG_SETTINGS', silent=True)

# logging - python/flask errors are stored here
file_handler = FileHandler("debug.log","a")                                                                                             
file_handler.setLevel(logging.WARNING)
app.logger.addHandler(file_handler)

#======== Database functions ===================================================

# database reading function
def connect_db():
    '''Connects to the specified database.'''
    
    rv = sqlite3.connect(app.config['DATABASE']) # connect to config database
    rv.row_factory = sqlite3.Row                  # get rows object
    
    return rv

# database connection creation function
def get_db():
    '''Opens a new database connection if there is none yet for the current 
        application context.'''
    if not hasattr(g,'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

# close database connection function
@app.teardown_appcontext
def close_db(error):
    '''Closes the database again at the end of the request.'''
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql',mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

#====== App config DB ================
# database reading function
def config_connect_db():
    '''Connects to the specified database.'''
    
    rv = sqlite3.connect(os.path.join(app.root_path,'config.db')) # connect to config database
    rv.row_factory = sqlite3.Row                  # get rows object
    
    return rv

# database connection creation function
def config_get_db():
    '''Opens a new database connection if there is none yet for the current 
        application context.'''
    if not hasattr(g,'sqlite_db'):
        g.sqlite_db = config_connect_db()
    return g.sqlite_db

# close database connection function
@app.teardown_appcontext
def config_close_db(error):
    '''Closes the database again at the end of the request.'''
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def config_init_db():
    with app.app_context():
        db = config_get_db()
        with app.open_resource('config_schema.sql',mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

#=================================================================================
#--------------- General User Commands -------------------------------------------
#=================================================================================

#============ Home/ index page ===================================================
@app.route('/')
@mobile_template('{mobile/}home.html')     
def home(template):
    read_config()

    if 'username' in session:
        return render_template(template, active=app.config['ACTIVE_DAY'])
    else:
        session['logged_in'] = False
    return render_template(template, active=app.config['ACTIVE_DAY'])
 
#============ Info pages =========================================================
@app.route('/webcast')
@mobile_template('{mobile/}webcast.html') 
def webcast(template):
    read_config()
    return render_template(template, active=app.config['ACTIVE_DAY'])

# @app.route('/prizes')
# def prizes():
#     read_config()
#     return render_template('prizes.html', active=app.config['ACTIVE_DAY'])

@app.route('/intro')
@mobile_template('{mobile/}intro.html') 
def intro(template):
    read_config()
    return render_template(template, active=app.config['ACTIVE_DAY'])

@app.route('/rules')
@mobile_template('{mobile/}Rules.html') 
def rules(template):
    read_config()
    return render_template(template, active=app.config['ACTIVE_DAY'])

@app.route('/prizes')
@mobile_template('{mobile/}Prizes.html') 
def prizes(template):
    read_config()
    return render_template(template, active=app.config['ACTIVE_DAY'])

@app.route('/links')
@mobile_template('{mobile/}Links.html') 
def links(template):
    read_config()
    return render_template(template, active=app.config['ACTIVE_DAY'])

@app.route('/answer')
@mobile_template('{mobile/}answer.html') 
def answer(template):
    read_config()
    return render_template(template, active=app.config['ACTIVE_DAY'])



#============ Forum Entry Commands ================================================


# show entries - list newest first (highest id first)
@app.route('/post/<int:n>')
@mobile_template('{mobile/}show_entries.html')
def show_entries(n,template,methods=['POST','GET']):
    read_config()
    if n >= 1 and n <= 10:

        db = get_db()
        cur = db.execute('select title, time, text, etime, score, username, forum from entries order by id desc')
        entries = cur.fetchall()

        rcur = db.execute('select title, time, text, etime, score, username, forum from staged order by id desc')
        staged = rcur.fetchall()

        dcur = db.execute('select title, time, text, etime, score, username, forum from deleted order by id desc')
        deleted = dcur.fetchall()

        cur2 = db.execute('select username, id, logo, admin from accounts order by id desc')
        acc = cur2.fetchall()

        counts = 0

        if 'username' in session:
            for entry in entries:
                if entry['username'] == session['username'] and entry['forum'] == n:
                    counts += 1
            for entry in staged:
                if entry['username'] == session['username'] and entry['forum'] == n:
                    counts += 1
            for entry in deleted:
                if entry['username'] == session['username'] and entry['forum'] == n and entry['score'] == -1:
                    counts += 1


        #entries = [entries[1],entries[1]]

        cipher = np.genfromtxt(app.root_path+'/static/{0}'.format(app.config['CIPHERS'][n-1]),dtype=str,delimiter='frog whale donkey')
        cipher = '<br>'.join(cipher)

        etime = time.time()
        dt = datetime.datetime.fromtimestamp(etime).strftime('%Y-%m-%d %H:%M:%S')

        #app.config['CIPHERS'][n-1]
        # show the post with the given id, the id is an integer
        return render_template(template,n=n, entries=entries, active=app.config['ACTIVE_DAY'],
                cipher=cipher,released=app.config['RELEASED'], accounts=acc,counts=counts, 
                    date=dt.split(' ')[0],time=dt.split(' ')[1], startDate=app.config['START_DATE'],
                        startTime=app.config['START_TIME'], endTime=app.config['END_TIME'],)

    elif n == 0 or n == 11:
        return render_template('closed.html', active=app.config['ACTIVE_DAY'],n=n)
    else:
        abort(401)

# show SINGLE entry
@app.route('/entry/<int:n>')
@mobile_template('{mobile/}entry.html')
def show_entry(template,n):
    read_config()

    db = get_db()
    cur = db.execute('select title, time, text, etime, score, username, forum, id from entries order by id desc')
    entries = cur.fetchall()

    cur2 = db.execute('select username, id, logo from accounts order by id desc')
    acc = cur2.fetchall()

    return render_template(template, n=n, entries=entries, active=app.config['ACTIVE_DAY'], accounts=acc)

# edit entry
@app.route('/edit/<int:n>')
def edit_entry(n):
    read_config()

    db = get_db()
    cur = db.execute('select title, time, text, etime, score, username, forum, id from entries order by id desc')
    entries = cur.fetchall()

    cur2 = db.execute('select username, id, logo from accounts order by id desc')
    acc = cur2.fetchall()

    return render_template("edit_entry.html", n=n, entries=entries, active=app.config['ACTIVE_DAY'], accounts=acc)

@app.route('/edit_staged/<int:n>')
def edit_stage_entry(n):
    read_config()

    db = get_db()
    cur = db.execute('select title, time, text, etime, score, username, forum, id from staged order by id desc')
    entries = cur.fetchall()

    cur2 = db.execute('select username, id, logo from accounts order by id desc')
    acc = cur2.fetchall()

    return render_template("edit_staged_entry.html", n=n, entries=entries, active=app.config['ACTIVE_DAY'], accounts=acc)

# add new entry
@app.route('/add/<int:n>',methods=['POST'])
def add_entry(n):
    if not session.get('logged_in'):    # check if user is logged on
        abort(401)

    # set timestamp, get database
    etime = time.time()
    timestamp = datetime.datetime.fromtimestamp(etime)\
                .strftime('%Y-%m-%d %H:%M:%S') # timestamp in good format
    
    # file uploads....
    if request.form['submit'] == 'Upload' and request.form['title'] != '':
        file = request.files['file']
        if file: 
            if allowed_file(file.filename):
                filename = session['username'] + str(np.random.randint(99999)) + secure_filename( file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                allowed = False

                # get file extension to set html dependent on file type (image,video,pdf,audio)
                if filename.rsplit('.', 1)[1] in ['png', 'jpg', 'jpeg', 'gif']:
                    fileText = '<img src="/static/uploads/{0}" alt="Team logo" width="900px" title="logo" border="0" class="logo" target="_blank" />"'\
                    .format(filename)
                    allowed = True
                elif filename.rsplit('.', 1)[1] in ['mp4']:
                    fileText = '<video width="600" controls>\
                                <source src="/static/uploads/{0}" type="video/mp4">\
                                Your browser does not support the video tag.\
                                </video>'\
                                .format(filename)
                    allowed = True
                elif filename.rsplit('.', 1)[1] in ['ogg']:
                    fileText = '<video width="600" controls>\
                                <source src="/static/uploads/{0}" type="video/ogg">\
                                Your browser does not support the video tag.\
                                </video>'\
                                .format(filename)
                    allowed = True
                elif filename.rsplit('.', 1)[1] in ['pdf']:
                    fileText = '<iframe src="/static/uploads/{0}" style="width:718px; height:700px;" frameborder="0"></iframe>'\
                                .format(filename)
                    allowed = True
                elif filename.rsplit('.', 1)[1] in ['mp3']:
                    fileText = '<audio controls>\
                                <source src="/static/uploads/{0}" type="audio/wav">\
                                Your browser does not support the audio element.\
                                </audio>'\
                                .format(filename)
                    allowed = True
                elif filename.rsplit('.', 1)[1] in ['wav']:
                    fileText = '<audio controls>\
                                <source src="/static/uploads/{0}" type="audio/ogg">\
                                Your browser does not support the audio element.\
                                </audio>'\
                                .format(filename)
                    allowed = True

                if allowed:
                    # add to database
                    db = get_db()
                    db.execute('insert into staged (title,text,etime,time,score,username,forum) values (?,?,?,?,?,?,?)',
                            [request.form['title'],fileText,etime,timestamp,0,session['username'],n])
                    db.commit()
                    flash("File successfully uploaded and posted.")
                    return redirect(url_for('show_entries',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page
                else:
                    # handle disallowed file types
                    flash("File type not allowed.")
                    return redirect(url_for('show_entries',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page
            else:
                # handle disallowed file types
                flash("File type not allowed.")
                return redirect(url_for('show_entries',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page
        else:
            # handle not choosing anything
            flash("File and/or title not chosen.")
            return redirect(url_for('show_entries',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page

    # text entries
    else:
        if request.form['title'] != '' and request.form['text'] != '':

            db = get_db()
            db.execute('insert into staged (title,text,etime,time,score,username,forum) values (?,?,?,?,?,?,?)',
                        [request.form['title'],request.form['text'],etime,timestamp,0,session['username'],n])
            db.commit()

            flash('New entry was successfully posted')
            return redirect(url_for('show_entries',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page
        else:
            # handle not choosing anything
            flash("Title and/or text not filled in.")
            return redirect(url_for('show_entries',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page#======= score board =============================================================

# add new entry
@app.route('/mod/<int:n>',methods=['POST'])
def mod_entry(n):
    if not session.get('logged_in'):    # check if user is logged on
        abort(401)
   

    if request.form['title'] != '' and request.form['text'] != '':

        db = get_db()
        cur = db.execute('select title, time, text, etime, score, username, forum, id from entries order by id desc')
        entries = cur.fetchall()
        #n = len(entries) - n
        cur = db.execute('update entries set text=(?) where etime=(?)',
                [request.form['text']+";;"+request.form['comments']+";;"+session['username'],request.form['submit']])

        this = db.execute('select forum from entries where etime=(?)',[request.form['submit']])
        this = cur.fetchall()
        db.commit()

        flash('Entry was successfully edited')
        return redirect(url_for('edit_entry',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page
    else:
        # handle not choosing anything
        flash("Title and/or text not filled in.")
        return redirect(url_for('edit_entry',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page

# add new entry
@app.route('/mod_stage/<int:n>',methods=['POST'])
def mod_stage_entry(n):
    if not session.get('logged_in'):    # check if user is logged on
        abort(401)   

    if request.form['title'] != '' and request.form['text'] != '':

        db = get_db()
        cur = db.execute('select title, time, text, etime, score, username, forum, id from staged order by id desc')
        entries = cur.fetchall()
        #n = len(entries) - n
        cur = db.execute('update staged set text=(?) where etime=(?)',[request.form['text'],request.form['submit']])
        db.commit()

        flash('Entry was successfully edited')
        return redirect(url_for('edit_stage_entry',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page
    else:
        # handle not choosing anything
        flash("Title and/or text not filled in.")
        return redirect(url_for('edit_stage_entry',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page

@app.route('/scoreboard')
@mobile_template('{mobile/}scoreboard.html')
def scoreboard(template):
    read_config()
    db = get_db()
    cur = db.execute('select username,score,admin,year1,year2,year3,year4,year5 from accounts order by id desc')
    accs = cur.fetchall()
    cur = db.execute('select username, score,forum from entries order by id desc')
    posts = cur.fetchall()
    
    scores = []  # GCSE
    sscores = []
    mscores = []
    scoresA = []  # A-level
    sscoresA = []
    mscoresA = []
    
    for acc in accs:
        if acc['admin'] != 'true' and acc['username'] != 'Team Mitchell':
            if (acc['year1'] != 'ALevel' and acc['year2'] != 'ALevel' and acc['year3'] != 'ALevel' and \
                acc['year4'] != 'ALevel' and acc['year5'] != 'ALevel' and acc['username'] != 'Internet Explorer') or acc['username'] == 'Braniancs':
                username = acc['username']
                score = 0
                sscore = 0
                mscore = 0
                
                # add up scores for this account
                for post in posts:                  
                    if post['username'] == username:
                        score += int(post['score'])
                        
                        if int(post['forum']) < 6:
                            sscore += int(post['score'])
                        else:
                            mscore += int(post['score'])
                
                # make sure scores are in order
                if len(scores) > 0:
                    # overall
                    done = False
                    
                    for i in range(len(scores)):
                        if score < int(scores[i][1]) and done == False:
                            scores.insert(i,[username,str(score)])
                            done = True
                            
                    if done == False:
                        scores.append([username,str(score)])
                       
                    # science
                    done = False
                    
                    for i in range(len(sscores)):
                        if sscore < int(sscores[i][1]) and done == False:
                            sscores.insert(i,[username,str(sscore)])
                            done = True
                            
                    if done == False:
                        sscores.append([username,str(sscore)])
                      
                    # media
                    done = False
                    
                    for i in range(len(mscores)):
                        if mscore < int(mscores[i][1]) and done == False:
                            mscores.insert(i,[username,str(mscore)])
                            done = True
                            
                    if done == False:
                        mscores.append([username,str(mscore)])
                else:
                    scores.append([username,str(score)]) 
                    sscores.append([username,str(sscore)]) 
                    mscores.append([username,str(mscore)]) 
            else:
                username = acc['username']
                score = 0
                sscore = 0
                mscore = 0
                
                # add up scores for this account
                for post in posts:                  
                    if post['username'] == username:
                        score += int(post['score'])
                        
                        if int(post['forum']) < 6:
                            sscore += int(post['score'])
                        else:
                            mscore += int(post['score'])
                
                # make sure scores are in order
                if len(scoresA) > 0:
                    # overall
                    done = False
                    
                    for i in range(len(scoresA)):
                        if score < int(scoresA[i][1]) and done == False:
                            scoresA.insert(i,[username,str(score)])
                            done = True
                            
                    if done == False:
                        scoresA.append([username,str(score)])
                       
                    # science
                    done = False
                    
                    for i in range(len(sscoresA)):
                        if sscore < int(sscoresA[i][1]) and done == False:
                            sscoresA.insert(i,[username,str(sscore)])
                            done = True
                            
                    if done == False:
                        sscoresA.append([username,str(sscore)])
                      
                    # media
                    done = False
                    
                    for i in range(len(mscoresA)):
                        if mscore < int(mscoresA[i][1]) and done == False:
                            mscoresA.insert(i,[username,str(mscore)])
                            done = True
                            
                    if done == False:
                        mscoresA.append([username,str(mscore)])
                else:
                    scoresA.append([username,str(score)]) 
                    sscoresA.append([username,str(sscore)]) 
                    mscoresA.append([username,str(mscore)])   
    return render_template(template,scores=scores[::-1],sscores=sscores[::-1],mscores=mscores[::-1], 
                scoresA=scoresA[::-1],sscoresA=sscoresA[::-1],mscoresA=mscoresA[::-1],active=app.config['ACTIVE_DAY'])    
    
#========== login/out commands ===================================================

@app.route('/login', methods=['GET','POST'])
@mobile_template('{mobile/}login.html')
def login(template):  
    read_config() 
    error = None
    if request.method == 'POST':
        db = get_db()
        acc = db.execute('select username,password,admin,teamemail from accounts order by id desc')
        accounts = acc.fetchall()

        for a in accounts:
            if (request.form['username'].lower() == a['username'].lower().rstrip() or request.form['username'].lower() == a['teamemail'].lower())\
                and request.form['password'] == a['password']:
                    if a['admin'] == 'true':
                        session['admin'] = True
                        flash('You were logged in as admin')
                    else:
                        session['admin'] = False
                        flash('You were logged in')
                    session['logged_in'] = True
                    session['username'] = a['username']#request.form['username']
                    
                    return redirect(url_for('intro'))# return to entries if success
        else:
            error = 'Invalid username and password combination'
    return render_template(template,error=error, active=app.config['ACTIVE_DAY'])  # else return error
        
    
@app.route('/logout')
def logout():
    session.pop('logged_in',None)
    session['admin'] = False
    flash('You were logged out')
    return redirect(url_for('home', active=app.config['ACTIVE_DAY']))

#---------------------------------------------------------------------------------
#=============== Admin user commands =============================================
#---------------------------------------------------------------------------------


#=================== accounts ====================================================

#==== Signing up, confirming new accounts ========================================
# sign-up (request new account)
@app.route('/sign_up')
@mobile_template('{mobile/}sign_up.html') 
def sign_up(template): 
    read_config()
    read_config()
    saved = ["","","","","", "",
                "","","Choose","Choose","Choose","Choose","Choose","",
                "","","Choose","Choose","Choose","Choose","Choose","",
                "","","Choose","Choose","Choose","Choose","Choose","",
                "","","Choose","Choose","Choose","Choose","Choose","",
                "","","Choose","Choose","Choose","Choose","Choose",""]
    return render_template(template, active=app.config['ACTIVE_DAY'],open=app.config['REGISTRATION_OPEN'],saved=saved)

@app.route('/sign_up_admin')
def sign_up_admin(): 
    read_config()
    read_config()
    saved = ["","","","","", "",
                "","","Choose","Choose","Choose","Choose","Choose","",
                "","","Choose","Choose","Choose","Choose","Choose","",
                "","","Choose","Choose","Choose","Choose","Choose","",
                "","","Choose","Choose","Choose","Choose","Choose","",
                "","","Choose","Choose","Choose","Choose","Choose",""]
    return render_template('sign_up_admin.html', active=app.config['ACTIVE_DAY'],open=app.config['REGISTRATION_OPEN'],saved=saved)

@app.route('/close_reg',methods=['POST'])
def close_registration(): 
    app.config['REGISTRATION_OPEN'] = False
    change_reg(False)
    return redirect(url_for('sign_up', active=app.config['ACTIVE_DAY'],open=app.config['REGISTRATION_OPEN']))

@app.route('/open_reg',methods=['POST'])
def open_registration(): 
    app.config['REGISTRATION_OPEN'] = True
    change_reg(True)
    return redirect(url_for('sign_up', active=app.config['ACTIVE_DAY'],open=app.config['REGISTRATION_OPEN']))

# request new account
@app.route('/request_account',methods=['POST'])
def request_account():
    username = request.form['username'] 
    password = request.form['password'] 
    passwordConfirm = request.form['passwordConfirm'] 
    teamemail = request.form['teamemail'] 
    school = request.form['school'] 
    postcode = request.form['postcode'] 
    teachername = request.form['teachername'] 
    teacheremail = request.form['teacheremail'] 


    names = []
    ages = []
    genders = []
    years = []
    phys = []
    physRate = []
    sciRate = []
    sciWords = []
    for i in range(1,6):
        names.append(request.form['name{0}'.format(i)])
        ages.append(request.form['age{0}'.format(i)])
        genders.append(request.form['gender{0}'.format(i)])
        years.append(request.form['year{0}'.format(i)])
        phys.append(request.form['phys{0}'.format(i)])
        physRate.append(request.form['physRate{0}'.format(i)])
        sciRate.append(request.form['sciRate{0}'.format(i)])
        sciWords.append(request.form['sciWords{0}'.format(i)])



    if username != '' and password != '' and \
        school != '' and postcode != '' and \
        teachername != '' and teacheremail != '' and \
        names[0] != '' and ages[0] != '' and \
        genders[0] != 'Choose' and years[0] != 'Choose' and \
        phys[0] != 'Choose' and physRate[0] != 'Choose'  and \
        sciRate[0] != 'Choose' and sciWords[0] != '' and \
        names[1] != '' and ages[1] != '' and \
        genders[1] != 'Choose' and years[1] != 'Choose' and \
        phys[1] != 'Choose' and physRate[1] != 'Choose' and  \
        sciRate[1] != 'Choose' and sciWords[1] != '' and \
        password == passwordConfirm:
        
        db = get_db()

        teamN = 0
        if names[2] == '' or ages[2] == '':
            teamN = 2
        elif names[3] == '' or names[3] == '':
               teamN = 3
        elif names[4] == '' or names[4] == '':
               teamN = 4
        else:
            teamN = 5

        sqlComm = 'insert into req_accounts (username,password,teamemail,school,postcode,teachername,teacheremail'
        sqlCommEnd = ') values (?,?,?,?,?,?,?'
        sqlData = [username,password,teamemail,school,postcode,teachername,teacheremail]

        for i in range(teamN):
            sqlComm = sqlComm + ',name{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(names[i])
            sqlComm = sqlComm + ',age{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(ages[i])
            sqlComm = sqlComm + ',gender{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(genders[i])
            sqlComm = sqlComm + ',year{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(years[i])
            sqlComm = sqlComm + ',phys{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(phys[i])
            sqlComm = sqlComm + ',physRate{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(physRate[i])
            sqlComm = sqlComm + ',sciRate{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(sciRate[i])
            sqlComm = sqlComm + ',sciWords{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(sciWords[i])        

        sqlCommEnd = sqlCommEnd + ')'


                
        db.execute(sqlComm+sqlCommEnd,sqlData)
        db.commit()


#         # email
# #         email = \
# # 'Hi SETI admin,\n\n \
# # A new account request has been made for the SETI cipher challenge.\n \
# # A team by the name of {0} has asked to join.\n \
# # The team is from {1} ({2})\n\n \
# # The team consists of these members:\n \
# # {3} (age {4}), {5} (age {6})'.format(
# #         username,school,postcode,
# #         name1,age1,name2,age2)

# #         if name3 != "":
# #                 email = email + ', {0} (age {1})'.format(name3,age3)
# #         if name4!= "":
# #                 email = email + ', {0} (age {1})'.format(name4,age4)
# #         if name5 != "":
# #                 email = email + ', {0} (age {1})'.format(name5,age5)


# #         email = email + \
# # '\n\nTheir supporting teacher is {0}, contact email {1}\n\n\
# # Cheers,\n\
# # your friendly automated SETI Cipher Challenge website'.format(teachername,teacheremail)

#         # notify!
#         #send_mail('New SETI cipher challenge team request: {0}'.format(username),email,['samdconnolly@gmail.com'])

        flash('New account was successfully requested')
        return redirect(url_for('home', active=app.config['ACTIVE_DAY']))
        
    else:
        saved = [username,teamemail,school,postcode,teachername, teacheremail,
        names[0],ages[0],genders[0],years[0],phys[0],physRate[0],sciRate[0],sciWords[0],
        names[1],ages[1],genders[1],years[1],phys[1],physRate[1],sciRate[1],sciWords[1],
        names[2],ages[2],genders[2],years[2],phys[2],physRate[2],sciRate[2],sciWords[2],
        names[3],ages[3],genders[3],years[3],phys[3],physRate[3],sciRate[3],sciWords[3],
        names[4],ages[4],genders[4],years[4],phys[4],physRate[4],sciRate[4],sciWords[4]]

        if password != passwordConfirm:
            flash('Password and confirmation did not match')
        else:
            flash('All fields must be filled up to a minimum of two members')

        return render_template('sign_up.html', active=app.config['ACTIVE_DAY'],open=app.config['REGISTRATION_OPEN'],saved=saved)
        #redirect(url_for('sign_up', active=app.config['ACTIVE_DAY'],saved=saved))


# display requested accounts
@app.route('/req_accounts')
def show_req_accounts(): 
    read_config()
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select id,username,password,teamemail,school,postcode,teachername,teacheremail,\
        name1,name2,name3,name4,name5,age1,age2,age3,age4,age5, \
        gender1,gender2,gender3,gender4,gender5,\
        year1,year2,year3,year4,year5, \
        phys1,phys2,phys3,phys4,phys5,  \
        physRate1,physRate2,physRate3,physRate4,physRate5, \
        sciRate1,sciRate2,sciRate3,sciRate4,sciRate5, \
        sciWords1, sciWords2, sciWords3,sciWords4,sciWords5 \
        from req_accounts order by id desc')
    accounts = cur.fetchall()
    return render_template('show_req_accounts.html', entries=accounts, active=app.config['ACTIVE_DAY'])

# delete requested account
@app.route('/delete_req_account',methods=['POST'])
def delete_req_account():
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    if 'confirm' in request.form.keys():
    
        db = get_db()
        cur = db.execute('select username,id from req_accounts order by id desc')
        accounts = cur.fetchall()

        for account in accounts:
            if int(request.form['delete']) == int(account['id']):
                    selected = account
                    break
            
        db.execute('delete from req_accounts where id == (?)',[selected['id']])
        db.commit()
        flash('Requested account was successfully deleted')
        return redirect(url_for('show_req_accounts', active=app.config['ACTIVE_DAY']))    # return to entries page


    else:
        flash('Confirm deletion before clicking to delete.')
        return redirect(url_for('show_req_accounts', active=app.config['ACTIVE_DAY']))
    
# add requested account
@app.route('/convert_req_account',methods=['POST'])
def convert_req_account():
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)

    db = get_db()
    cur = db.execute('select id,username,password,teamemail,school,postcode,teachername,teacheremail,\
        name1,name2,name3,name4,name5,age1,age2,age3,age4,age5, \
        gender1,gender2,gender3,gender4,gender5,\
        year1,year2,year3,year4,year5, \
        phys1,phys2,phys3,phys4,phys5,  \
        physRate1,physRate2,physRate3,physRate4,physRate5, \
        sciRate1,sciRate2,sciRate3,sciRate4,sciRate5, \
        sciWords1, sciWords2, sciWords3,sciWords4,sciWords5 \
        from req_accounts order by id desc')
    accounts = cur.fetchall()

    for account in accounts:
        if int(request.form['accept']) == int(account['id']):
                selected = account

    # geocode!
    postcode = selected['postcode']
    g = geocoder.google(postcode)
    if len(g.latlng) > 1:
        latitude = g.latlng[0]
        longitude = g.latlng[1]
    else:
        latitude, longitude = 50.934189,-1.395685

    if 'admin' in request.form.keys():
        admin = 'true'
    else:
        admin = 'false'

    db.execute('insert into accounts (username,password,teamemail,admin,score,school,postcode,lat,lng,teachername,teacheremail,\
        name1,name2,name3,name4,name5,age1,age2,age3,age4,age5, \
        gender1,gender2,gender3,gender4,gender5,\
        year1,year2,year3,year4,year5, \
        phys1,phys2,phys3,phys4,phys5,  \
        physRate1,physRate2,physRate3,physRate4,physRate5, \
        sciRate1,sciRate2,sciRate3,sciRate4,sciRate5, \
        sciWords1, sciWords2, sciWords3,sciWords4,sciWords5) values \
        (?,?,?,?,?,?,?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [selected['username'],selected['password'],selected['teamemail'],admin,0,
                selected['school'],postcode,latitude, longitude,selected['teachername'],selected['teacheremail'],
                selected['name1'],selected['name2'],selected['name3'],selected['name4'],selected['name5'],
                selected['age1'],selected['age2'],selected['age3'],selected['age4'],selected['age5'],
                selected['gender1'],selected['gender2'],selected['gender3'],selected['gender4'],selected['gender5'],
                selected['year1'],selected['year2'],selected['year3'],selected['year4'],selected['year5'],
                selected['phys1'],selected['phys2'],selected['phys3'],selected['phys4'],selected['phys5'],
                selected['physRate1'],selected['physRate2'],selected['physRate3'],selected['physRate4'],selected['physRate5'],
                selected['sciRate1'],selected['sciRate2'],selected['sciRate3'],selected['sciRate4'],selected['sciRate5'],
                selected['sciWords1'],selected['sciWords2'],selected['sciWords3'],selected['sciWords4'],selected['sciWords5']])
    db.commit() 
    db.execute('delete from req_accounts where username == (?)',[selected['username']])
    db.commit()
    flash('Requested account was successfully added to accounts')
    return redirect(url_for('show_req_accounts', active=app.config['ACTIVE_DAY']))    # return to entries page

#==== existing account management 

# display existing accounts
@app.route('/accounts')
def show_accounts(): 
    read_config()
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select id,username,password,admin,teamemail,school,postcode,lat,lng,teachername,teacheremail,\
        name1,name2,name3,name4,name5,age1,age2,age3,age4,age5, \
        gender1,gender2,gender3,gender4,gender5,\
        year1,year2,year3,year4,year5, \
        phys1,phys2,phys3,phys4,phys5,  \
        physRate1,physRate2,physRate3,physRate4,physRate5, \
        sciRate1,sciRate2,sciRate3,sciRate4,sciRate5, \
        sciWords1, sciWords2, sciWords3,sciWords4,sciWords5 \
        from accounts order by id desc')
    accounts = cur.fetchall()

    # stats
    ages = [0,0,0,0,0] # <15, 15, 16, 17, 18
    genders = [0,0,0,0] # male,female,other, prefer not to say
    emails = []
    teamEmails = []
    for account in accounts:

        if account['teacheremail'] not in emails:
            emails.append(account['teacheremail'])
        if account['teamemail'] not in teamEmails:
            teamEmails.append(account['teamemail'])

        if account['admin'] == 'false':
            thisAges = [account['age1'],account['age2'],account['age3'],account['age4'],account['age5']]
            for age in thisAges:
                if age != None:
                    try:
                        b = int(age)-14
                        if b < 0:
                            b = 0
                        if b <  5:
                            ages[b] += 1
                    except ValueError:
                        continue
            thisGenders = [account['gender1'],account['gender2'],account['gender3'],account['gender4'],account['gender5']]
            for gender in thisGenders:
                if gender == 'Male':
                    genders[0] += 1
                elif gender == 'Female':
                    genders[1] += 1
                elif gender == 'Female':
                    genders[1] += 1
                elif gender == 'Other':
                    genders[2] += 1
                elif gender == 'Prefer':
                    genders[3] += 1

    return render_template('show_accounts.html', entries=accounts, active=app.config['ACTIVE_DAY'],ages=ages,genders=genders, emails=emails, teamEmails=teamEmails)

# add new account
@app.route('/add_account',methods=['POST'])
def add_account():
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)

    if request.form['username'] != '' and request.form['password'] != '':
        db = get_db()
        if 'admin' in request.form.keys():
            admin = 'true'
        else:
            admin = 'false'
        db.execute('insert into accounts (username,password,teamemail,admin,score,school,postcode,teachername,teacheremail,name1,name2,name3,name4,name5,age1,age2,age3,age4,age5) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [request.form['username'],request.form['password'],'none',admin,0,
                request.form['school'],'none','none','none',
                request.form['name1'],request.form['name2'],request.form['name3'],request.form['name4'],request.form['name5'],
                request.form['age1'],request.form['age2'],request.form['age3'],request.form['age4'],request.form['age5']])
        db.commit()
        flash('New account was successfully added')
        return redirect(url_for('show_accounts'))    # return to entries page
        
    else:
        flash('Non-blank username and password required')
        return redirect(url_for('show_accounts', active=app.config['ACTIVE_DAY']))

# add new admin account
@app.route('/request_account_admin',methods=['POST'])
def request_account_admin():
    username = request.form['username'] 
    password = request.form['password'] 
    passwordConfirm = request.form['passwordConfirm'] 
    teamemail = request.form['teamemail'] 
    school = request.form['school'] 
    postcode = request.form['postcode'] 
    teachername = request.form['teachername'] 
    teacheremail = request.form['teacheremail'] 


    names = []
    ages = []
    genders = []
    years = []
    phys = []
    physRate = []
    sciRate = []
    sciWords = []
    for i in range(1,6):
        names.append(request.form['name{0}'.format(i)])
        ages.append(request.form['age{0}'.format(i)])
        genders.append(request.form['gender{0}'.format(i)])
        years.append(request.form['year{0}'.format(i)])
        phys.append(request.form['phys{0}'.format(i)])
        physRate.append(request.form['physRate{0}'.format(i)])
        sciRate.append(request.form['sciRate{0}'.format(i)])
        sciWords.append(request.form['sciWords{0}'.format(i)])



    if username != '' and password != '' and \
        school != '' and \
        names[0] != '' and ages[0] != '' and \
        password == passwordConfirm:
        
        db = get_db()

        teamN = 0
        if names[1] == '' or ages[1] == '':
            teamN = 1
        elif names[2] == '' or ages[2] == '':
            teamN = 2
        elif names[3] == '' or names[3] == '':
               teamN = 3
        elif names[4] == '' or names[4] == '':
               teamN = 4
        else:
            teamN = 5

        sqlComm = 'insert into req_accounts (username,password,teamemail,school,postcode,teachername,teacheremail'
        sqlCommEnd = ') values (?,?,?,?,?,?,?'
        sqlData = [username,password,teamemail,school,postcode,teachername,teacheremail]

        for i in range(teamN):
            sqlComm = sqlComm + ',name{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(names[i])
            sqlComm = sqlComm + ',age{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(ages[i])
            sqlComm = sqlComm + ',gender{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(genders[i])
            sqlComm = sqlComm + ',year{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(years[i])
            sqlComm = sqlComm + ',phys{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(phys[i])
            sqlComm = sqlComm + ',physRate{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(physRate[i])
            sqlComm = sqlComm + ',sciRate{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(sciRate[i])
            sqlComm = sqlComm + ',sciWords{0}'.format(i+1)
            sqlCommEnd = sqlCommEnd + ',?'
            sqlData.append(sciWords[i])        

        sqlCommEnd = sqlCommEnd + ')'


                
        db.execute(sqlComm+sqlCommEnd,sqlData)
        db.commit()

        flash('New account was successfully requested')
        return redirect(url_for('home', active=app.config['ACTIVE_DAY']))
        
    else:
        saved = [username,teamemail,school,postcode,teachername, teacheremail,
        names[0],ages[0],genders[0],years[0],phys[0],physRate[0],sciRate[0],sciWords[0],
        names[1],ages[1],genders[1],years[1],phys[1],physRate[1],sciRate[1],sciWords[1],
        names[2],ages[2],genders[2],years[2],phys[2],physRate[2],sciRate[2],sciWords[2],
        names[3],ages[3],genders[3],years[3],phys[3],physRate[3],sciRate[3],sciWords[3],
        names[4],ages[4],genders[4],years[4],phys[4],physRate[4],sciRate[4],sciWords[4]]

        if password != passwordConfirm:
            flash('Password and confirmation did not match')
        else:
            flash('Essential fields not filled (see below)')

        return render_template('sign_up_admin.html', active=app.config['ACTIVE_DAY'],open=app.config['REGISTRATION_OPEN'],saved=saved)


# delete account
@app.route('/delete_account',methods=['POST'])
def delete_account():
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    if 'confirm' in request.form.keys():
    
        db = get_db()
        cur = db.execute('select id,username from accounts order by id desc')
        accounts = cur.fetchall()

        for account in accounts:
            if int(request.form['delete']) == int(account['id']):
                    selected = account
            
        db.execute('delete from accounts where id == (?)',[selected['id']])
        db.commit()
        flash('Account was successfully deleted')
        return redirect(url_for('show_accounts', active=app.config['ACTIVE_DAY']))    # return to entries page


    else:
        flash('Confirm deletion before clicking to delete.')
        return redirect(url_for('show_accounts', active=app.config['ACTIVE_DAY']))
      
# manually add account        
def add_account_manual(username,password,admin,school,names,ages,teamemail='none',postcode='none',teachername='none',teacheremail='none'):
    with app.app_context():
        db = get_db()
        if len(names) == 1:
            db.execute('insert into accounts (username,password,teamemail,admin, score,school,postcode,teachername,teacheremail,name1,age1) values (?,?,?,?,?,?,?,?,?,?,?)',
                    [username,password,teamemail,admin,0,school,postcode,teachername,teacheremail,names[0],ages[0]])
        elif len(names) == 2:
            db.execute('insert into accounts (username,password,teamemail,admin, score,school,postcode,teachername,teacheremail,name1,age1,name2,age2) values (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    [username,password,teamemail,admin,0,school,postcode,teachername,teacheremail,names[0],ages[0],names[1],ages[1]])
        elif len(names) == 3:
            db.execute('insert into accounts (username,password,teamemail,admin, score,school,postcode,teachername,teacheremail,name1,age1,name2,age2,name3,age3) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    [username,password,teamemail,admin,0,school,postcode,teachername,teacheremail,names[0],ages[0],names[1],ages[1],names[2],ages[2]])
        elif len(names) == 4:
            db.execute('insert into accounts (username,password,teamemail,admin, score,school,postcode,teachername,teacheremail,name1,age1,name2,age2,name3,age3,name4,age4) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    [username,password,teamemail,admin,0,school,postcode,teachername,teacheremail,names[0],ages[0],names[1],ages[1],names[2],ages[2],names[3],ages[3]])
        elif len(names) == 5:
            db.execute('insert into accounts (username,password,teamemail,admin, score,school,postcode,teachername,teacheremail,name1,age1,name2,age2,name3,age3,name4,age4,name5,age5) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    [username,password,teamemail,admin,0,school,postcode,teachername,teacheremail,names[0],ages[0],names[1],ages[1],names[2],ages[2],names[3],ages[3],names[4],ages[4]])
        db.commit() 

#=== profile stuff

# show profiles - list newest first (highest id first)
@app.route('/profile/<int:n>/<int:edit>',methods=['POST','GET'])
@mobile_template('{mobile/}profile.html') 
def account_profile(template,n,edit):
    read_config()
    db = get_db()
    cur = db.execute("select username,bio,logo,id,school,name1,name2,name3,name4,name5, lat, lng from accounts order by id desc")
    accounts = cur.fetchall()

    for account in accounts:
        if int(account['id']) == n:
            entry = account

    # check if relevant user is logged on if editing
    if edit == 1 and ((session.get('logged_in') == False or session['username'] != entry['username'])):
        return redirect(url_for('account_profile',n=n,edit=0))

    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = session['username'] + secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename.lower()))

            db = get_db()
            cur = db.execute('update accounts set logo=(?) where username=(?)',[filename,entry['username']])
            db.commit() 

            flash("File successfully uploaded.")
            return redirect(url_for('account_profile',n=n,edit=1, active=app.config['ACTIVE_DAY']))

        else:
            flash("No file chosen.")

    # show the post with the given id, the id is an integer
    return render_template(template, account=entry,edit=edit, active=app.config['ACTIVE_DAY'])

@app.route('/profile/<int:n>/edit_profile',methods=['POST'])
def edit_profile(n):
    db = get_db()
    cur = db.execute('select username,bio,id from accounts order by id desc')
    accounts = cur.fetchall()


    for account in accounts:
        if int(account['id']) == n:
            entry = account

    if (session.get('logged_in') == False or session['username'] != entry['username']):    # check if user is logged on
        abort(401)

    cur = db.execute('update accounts set bio=(?) where username=(?)',[request.form['bio'],entry['username']])
    db.commit() 

    return redirect(url_for('account_profile',n=n,edit=0, active=app.config['ACTIVE_DAY']))

def change_bio(n,text):
    with app.app_context():
        db = get_db()
        cur = db.execute('select username,bio from accounts order by id desc')
        entries = cur.fetchall()
        cur = db.execute('update accounts set bio=(?) where username=(?)',[text,entries[n]['username']])
        db.commit() 

def change_logo(n,filename):
    with app.app_context():
        db = get_db()
        cur = db.execute('select username,logo from accounts order by id desc')
        entries = cur.fetchall()
        cur = db.execute('update accounts set logo=(?) where username=(?)',[filename,entries[n]['username']])
        db.commit() 

@app.route('/profiles')
@mobile_template('{mobile/}profiles.html') 
def profiles(template):
    read_config()
    db = get_db()
    cur = db.execute('select username,logo,id,admin,postcode, lat,lng from accounts order by id desc')
    accs = cur.fetchall()   
    return render_template(template,accounts=accs, active=app.config['ACTIVE_DAY'])    
    

#=================== post staging and deletion ===================================

# display staged posts        
@app.route('/stage_entries')
def stage_entries():
    read_config()
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select title, time, text, etime,score,username,forum from staged order by id desc')
    entries = cur.fetchall()
    entries = entries[::-1]
    return render_template('stage_entries.html', entries=entries, active=app.config['ACTIVE_DAY']) 

# display deleted posts        
@app.route('/deleted')
def deleted_entries():
    read_config()
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select title, time, text, etime,score,username, forum from deleted order by id desc')
    entries = cur.fetchall()
    return render_template('deleted_entries.html', entries=entries, active=app.config['ACTIVE_DAY']) 

# submit or delete staged posts
@app.route('/submit',methods=['POST'])
def submit_staged():
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select title,text,time,etime, score,username, forum from staged order by id desc')
    staged = cur.fetchall()
    
    for entry in staged:
        keys = request.form.keys()
        
        if 'submit' in keys:
            
            score = request.form['score']
            
            if score == '':
                score = 0
            
            if request.form['submit'] == entry['etime']:
                selected = entry
                text = selected['text']
                comments = request.form['comments']
                if comments != '':
                    text = text + ";;" + comments + ';;' + session['username']

                db.execute('insert into entries (title,text,time,etime,score,username,forum) values (?,?,?,?,?,?,?)',
                [selected['title'],text,selected['time'],selected['etime'],score,selected['username'],selected['forum']])
                flash('Staged entry was successfully posted')

        elif 'delete' in keys:                
            if request.form['delete'] == entry['etime']:
                selected = entry
                db.execute('insert into deleted (title,text,time,etime,score,username,forum) values (?,?,?,?,?,?,?)',
                [selected['title'],selected['text'],selected['time'],selected['etime'],selected['score'],selected['username'],selected['forum']])
                flash('Staged entry was successfully deleted') 

        elif 'punish' in keys:                
            if request.form['punish'] == entry['etime']:
                selected = entry
                db.execute('insert into deleted (title,text,time,etime,score,username,forum) values (?,?,?,?,?,?,?)',
                [selected['title'],selected['text'],selected['time'],selected['etime'],-1,selected['username'],selected['forum']])
                flash('Staged entry was successfully punished')     
  
    db.execute('delete from staged where etime == (?)',[selected['etime']])
    db.commit()
    return redirect(url_for('stage_entries', active=app.config['ACTIVE_DAY']))    # return to entries page

# delete submitted posts
@app.route('/delete/<int:n>',methods=['POST']) 
def delete_entry(n):
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select title,text,time,etime,score,username,forum from entries order by id desc')
    entries = cur.fetchall()
  
    for entry in entries:
        if request.form['delete'] == entry['etime']:
                selected = entry
        
    db.execute('insert into deleted (title,text,time,etime,score,username,forum) values (?,?,?,?,?,?,?)',
                [selected['title'],selected['text'],selected['time'],selected['etime'],selected['score'],selected['username'],selected['forum']])
    db.execute('delete from entries where etime == (?)',[selected['etime']])
    db.commit()
    flash('Entry was successfully deleted')      
    return redirect(url_for('show_entries',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page
 
# delete submitted posts
@app.route('/punish/<int:n>',methods=['POST']) 
def punish_entry(n):
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select title,text,time,etime,score,username,forum from entries order by id desc')
    entries = cur.fetchall()
  
    for entry in entries:
        if request.form['delete'] == entry['etime']:
                selected = entry
        
    db.execute('insert into deleted (title,text,time,etime,score,username,forum) values (?,?,?,?,?,?,?)',
                [selected['title'],selected['text'],selected['time'],selected['etime'],-1,selected['username'],selected['forum']])
    db.execute('delete from entries where etime == (?)',[selected['etime']])
    db.commit()
    flash('Entry was successfully punished')      
    return redirect(url_for('show_entries',n=n, active=app.config['ACTIVE_DAY']))    # return to entries page

# restore deleted posts
@app.route('/forum_restore',methods=['POST']) 
def restore_post():
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select title,text,time,etime,score,username,forum from deleted order by id desc')
    entries = cur.fetchall()
  
    for entry in entries:
        if request.form['post'] == entry['etime']:
                selected = entry
        
    db.execute('insert into entries (title,text,time,etime,score,username,forum) values (?,?,?,?,?,?,?)',
                [selected['title'],selected['text'],selected['time'],selected['etime'],selected['score'],selected['username'],selected['forum']])
    db.execute('delete from deleted where etime == (?)',[selected['etime']])
    db.commit()
    flash('Entry was successfully restored to forum')      
    return redirect(url_for('deleted_entries', active=app.config['ACTIVE_DAY']))    # return to entries page
       
@app.route('/staged_restore',methods=['POST'])   
def restore_staged(): 
    if not (session.get('logged_in') and session['admin'] == True):    # check if user is logged on
        abort(401)
    db = get_db()
    cur = db.execute('select title,text,time,etime,score,username,forum from deleted order by id desc')
    entries = cur.fetchall()
  
    for entry in entries:
        if request.form['stage'] == entry['etime']:
                selected = entry
        
    db.execute('insert into staged (title,text,time,etime,score,username,forum) values (?,?,?,?,?,?,?)',
                [selected['title'],selected['text'],selected['time'],selected['etime'],selected['score'],selected['username'],selected['forum']])
    db.execute('delete from deleted where etime == (?)',[selected['etime']])
    db.commit()
    flash('Entry was successfully restored to staging')      
    return redirect(url_for('deleted_entries', active=app.config['ACTIVE_DAY']))    # return to entries page
    
#========== Dev/testing ==========================================================
@app.route('/active_forum')
@mobile_template('{mobile/}active_forum.html')  
def active_forum(template):
    #read_config()
    return render_template(template, active=app.config['ACTIVE_DAY'], released=app.config['RELEASED']) 

@app.route('/activate_forum',methods=['POST'])
def activate_forum():
    active = int(request.form['activate'])
    app.config['ACTIVE_DAY'] = active
    change_active(active) 
    return redirect(url_for('active_forum', active=app.config['ACTIVE_DAY'])) 
   
@app.route('/release_cipher',methods=['POST'])
def release_cipher():
    released = int(request.form['release'])
    app.config['RELEASED'] = released
    change_released(released) 
    return redirect(url_for('active_forum', active=app.config['ACTIVE_DAY'])) 

# config setup
def setup_config(active=0,released=0,reg=0):
    with app.app_context():
        db = config_get_db()
        db.execute('insert into config (active,released,reg) values (?,?,?)',
                    [active,released,reg])
        db.commit() 

def read_config():
    with app.app_context():
        db = config_get_db()
        cur = db.execute('select active,released,reg from config order by id desc')
        config = cur.fetchall()
        active = config[0]['active'] 
        released = config[0]['released']
        reg = config[0]['reg'] 

    app.config['ACTIVE_DAY'] = active 
    app.config['RELEASED'] = released
    if reg == 0:
        app.config['REGISTRATION_OPEN'] = False
    else:
        app.config['REGISTRATION_OPEN'] = True

def change_reg(open):
    with app.app_context():
        db = config_get_db()

        if open == True:
            cur = db.execute('update config set reg=1')
        else:
            cur = db.execute('update config set reg=0')
        db.commit() 

def change_active(active):
    with app.app_context():
        db = config_get_db()
        cur = db.execute('update config set active=(?)',[active])
        db.commit() 

def change_released(released):
    with app.app_context():
        db = config_get_db()
        cur = db.execute('update config set released=(?)',[released])
        db.commit() 

# geocoding test

@app.route('/geo')
def geo():
    g = geocoder.google('SO17 1BJ')
    return str(g.latlng)


#========== Mailing ==============================================================

# doesn't work with python 2.6
# def send_mail(subject, body, recipients):

#     with app.app_context():

#         msg = Message(subject,recipients=recipients)
#         msg.body = body

#         mail.send(msg)

# @app.route('/mail')
# def send_mail():

#     msg = Message('test',recipients=["samdconnolly@gmail.com"])
#     msg.body = 'test'
#     mail.send(msg)

#     return redirect(url_for('home', active=app.config['ACTIVE_DAY'])) 

#====== Uploading ==============================================================
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# @app.route('/upload', methods=['GET', 'POST'])
# def upload_file():
#     if request.method == 'POST':
#         file = request.files['file']
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             return redirect(url_for('upload_file',
#                                     filename=filename, active=app.config['ACTIVE_DAY']))
#     return render_template('upload.html') 

#============ 2014 site =========================================================
#@app.route('/2014/index')
#def 2014index():
#    return render_template('test.html')

@app.route('/2014/index')
def index_old():
    return render_template('2014/index.html') 

@app.route('/2014/intro')
def intro_old():
    return render_template('2014/intro.html') 

@app.route('/2014/rules')
def rules_old():
    return render_template('2014/rules.html') 

@app.route('/2014/register')
def register_old():
    return render_template('2014/register.html') 

@app.route('/2014/forum')
def forum_old():
    return render_template('2014/forum.html') 

@app.route('/2014/scoreboard')
def scoreboard_old():
    return render_template('2014/scoreboard.html') 


@app.route('/2014/prizes')
def prizes_old():
    return render_template('2014/prizes.html') 

@app.route('/2014/links')
def links_old():
    return render_template('2014/links.html')
 
@app.route('/2014/answer')
def answer_old():
    return render_template('2014/answer.html')

@app.route('/2014/science/<int:n>')
def science_old(n):
    return render_template('2014/ScienceDay{0}.html'.format(n))

@app.route('/2014/media/<int:n>')
def media_old(n):
    return render_template('2014/MediaDay{0}.html'.format(n))

#============ archived sites (2015 onwards) ======================================


# database reading function
def connect_db_archive(year):
    '''Connects to the specified database.'''
    
    rv = sqlite3.connect(app.config['ARCHIVE_DATABASE'].format(year)) # connect to config database
    rv.row_factory = sqlite3.Row                  # get rows object
    
    return rv

# database connection creation function
def get_db_archive(year):
    '''Opens a new database connection if there is none yet for the current 
        application context.'''
    if not hasattr(g,'sqlite_db'):
        g.sqlite_db = connect_db_archive(year)
    return g.sqlite_db

# close database connection function
@app.teardown_appcontext
def close_db_archive(error):
    '''Closes the database again at the end of the request.'''
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/<int:year>/home')
def index_archive(year):
    return render_template('{0}/home.html'.format(year),year=year) 

@app.route('/<int:year>/active_forum')
def active_forum_archive(year):
    return render_template('{0}/active_forum.html'.format(year),year=year)




# show entries - list newest first (highest id first)
@app.route('/<int:year>/post/<int:n>')
def show_entries_archive(n,year,methods=['GET']):
    if n >= 1 and n <= 10:

        db = get_db_archive(year)
        cur = db.execute('select title, time, text, etime, score, username, forum from entries order by id desc')
        entries = cur.fetchall()

        rcur = db.execute('select title, time, text, etime, score, username, forum from staged order by id desc')
        staged = rcur.fetchall()

        dcur = db.execute('select title, time, text, etime, score, username, forum from deleted order by id desc')
        deleted = dcur.fetchall()

        cur2 = db.execute('select username, id, logo from accounts order by id desc')
        acc = cur2.fetchall()

        counts = 0

        if 'username' in session:
            for entry in entries:
                if entry['username'] == session['username'] and entry['forum'] == n:
                    counts += 1
            for entry in staged:
                if entry['username'] == session['username'] and entry['forum'] == n:
                    counts += 1
            for entry in deleted:
                if entry['username'] == session['username'] and entry['forum'] == n and entry['score'] == -1:
                    counts += 1


        #entries = [entries[1],entries[1]]

        cipher = np.genfromtxt(app.root_path+'/static/{0}/{1}'.format(year,app.config['CIPHERS'][n-1]),dtype=str,delimiter='frog whale donkey')
        cipher = '<br>'.join(cipher)

        # show the post with the given id, the id is an integer
        return render_template('{0}/show_entries.html'.format(year),n=n, entries=entries, cipher=cipher,year=year)

    else:
        abort(401)


@app.route('/<int:year>/profiles')
def profiles_archive(year):
    db = get_db_archive(year)
    cur = db.execute('select username,logo,id,admin,postcode from accounts order by id desc')
    accs = cur.fetchall()   
    return render_template('{0}/profiles.html'.format(year),year=year,accounts=accs) 


@app.route('/<int:year>/links')
def links_archive(year):
    return render_template('{0}/Links.html'.format(year),year=year) 

@app.route('/<int:year>/prizes')
def prizes_archive(year):
    return render_template('{0}/Prizes.html'.format(year),year=year) 

@app.route('/<int:year>/scoreboard')
def scoreboard_archive(year):
    db = get_db_archive(year)
    cur = db.execute('select username,score,admin from accounts order by id desc')
    accs = cur.fetchall()
    cur = db.execute('select username, score,forum from entries order by id desc')
    posts = cur.fetchall()
    
    scores = []  
    sscores = []
    mscores = []
    
    for acc in accs:
        if acc['admin'] != 'true' and acc['username'] != 'Team Mitchell':
            username = acc['username']
            score = 0
            sscore = 0
            mscore = 0
            
            # add up scores for this account
            for post in posts:                  
                if post['username'] == username:
                    score += int(post['score'])
                    
                    if int(post['forum']) < 6:
                        sscore += int(post['score'])
                    else:
                        mscore += int(post['score'])
            
            # make sure scores are in order
            if len(scores) > 0:
                # overall
                done = False
                
                for i in range(len(scores)):
                    if score < int(scores[i][1]) and done == False:
                        scores.insert(i,[username,str(score)])
                        done = True
                        
                if done == False:
                    scores.append([username,str(score)])
                   
                # science
                done = False
                
                for i in range(len(sscores)):
                    if sscore < int(sscores[i][1]) and done == False:
                        sscores.insert(i,[username,str(sscore)])
                        done = True
                        
                if done == False:
                    sscores.append([username,str(sscore)])
                  
                # media
                done = False
                
                for i in range(len(mscores)):
                    if mscore < int(mscores[i][1]) and done == False:
                        mscores.insert(i,[username,str(mscore)])
                        done = True
                        
                if done == False:
                    mscores.append([username,str(mscore)])
            else:
                scores.append([username,str(score)]) 
                sscores.append([username,str(sscore)]) 
                mscores.append([username,str(mscore)]) 
   
    return render_template('/{0}/scoreboard.html'.format(year),scores=scores[::-1],sscores=sscores[::-1],mscores=mscores[::-1],year=year)    
    


@app.route('/<int:year>/profile/<int:n>')
def account_profile_archive(year,n):
    db = get_db_archive(year)
    cur = db.execute("select username,bio,logo,id,school,name1,name2,name3,name4,name5 from accounts order by id desc")
    accounts = cur.fetchall()

    for account in accounts:
        if int(account['id']) == n:
            entry = account

    # show the post with the given id, the id is an integer
    return render_template('{0}/profile.html'.format(year), account=entry, year=year)

#=================================================================================
#            Run app
#=================================================================================
# set the secret key. Keep it safe. Keep it secret.
# app.secret_key = '_~q\xf4c\x88\x1b\x0fPi\x88\x9dj?Ofj\x8f\xee\xa4\xcb\x9a\xe9U'


# run the application if run as standalone app
if __name__ == '__main__':

    sess.init_app(app)

    app.run() #host='0.0.0.0'

    
