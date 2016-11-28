"""
dbEdit.py

Created July 2015

Author: Sam Connolly

Used to edit the SETI cipher challenge database if necessary...

To create an admin account manually:
    

os.chdir('/location/of/this/file/')
from dbEdit import init_db,add_account_manual
add_account_manual('sam','dog','true','Southampton Uni',['Sam Connolly'],[25])
"""

import os
import sqlite3
import time
import datetime

from flask import Flask, request, session, g, redirect, url_for, abort, \
                    render_template, flash

# create application
app = Flask(__name__)  # name given in brackets, but providing __name__
                            # is good for single apps, as the name will change

app.config.from_object(__name__)

#======== Database functions ===================================================

# database reading function
def connect_db(database):
    '''Connects to the specified database.'''
    
    rv = sqlite3.connect(database) # connect to config database
    rv.row_factory = sqlite3.Row                  # get rows object
    
    return rv

# database connection creation function
def get_db(database):
    '''Opens a new database connection if there is none yet for the current 
        application context.'''
    if not hasattr(g,'sqlite_db'):
        g.sqlite_db = connect_db(database)
    return g.sqlite_db

# close database connection function
@app.teardown_appcontext
def close_db(error):
    '''Closes the database again at the end of the request.'''
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def get_data(database,field,team=None):
    with app.app_context():
        db = get_db(database)
        cur = db.execute('select * from accounts order by id desc')
        accounts = cur.fetchall()
        for account in accounts:
        	if team == None or team == account['username']:
	            print account[field]

def get_req_data(database,field,team=None):
    with app.app_context():
        db = get_db(database)
        cur = db.execute('select id,username,password,teamemail, school,postcode,teachername,teacheremail,name1,age1,name2,age2,name3,age3,name4,age4,name5,age5 from req_accounts order by id desc')
        accounts = cur.fetchall()
        for account in accounts:
        	if team == None or team == account['username']:
	            print account[field]

def get_config(database):
    with app.app_context():
        db = get_db(database)
        cur = db.execute('select id,active,released,reg from config order by id desc')
        setup = cur.fetchall()[0]
        print setup['active']
        print setup['released']
        print setup['reg']

def get_keys(database):
    with app.app_context():
        db = get_db(database)
        cur = db.execute('select * from accounts')
        setup = cur.fetchall()[0]
        print setup.keys()

def change_data(database,team,field,new_data):
    with app.app_context():
        db = get_db(database)
        cur = db.execute('select id,username,password,teamemail,admin, score,school,postcode,teachername,teacheremail,name1,age1,name2,age2,name3,age3,name4,age4,name5,age5 from accounts order by id desc')
        accounts = cur.fetchall()
        for account in accounts:
            if team == account['username']:
                print "old value:", account[field]
                cur = db.execute('update accounts set {0}=(?) where username=(?)'.format(field),[new_data,account['username']])
                db.commit()
                print "new value:", new_data

def add_data(database,team,field,new_data):
    with app.app_context():
        db = get_db(database)
        cur = db.execute('select id,username,password,teamemail,admin, score,school,postcode,teachername,teacheremail,name1,age1,name2,age2,name3,age3,name4,age4,name5,age5 from accounts order by id desc')
        accounts = cur.fetchall()
        for account in accounts:
            if team == account['username']:
                cur = db.execute('update accounts set {0}=(?) where username=(?)'.format(field),[new_data,account['username']])
                db.commit()
                print "new value:", new_data

# add account manually
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
