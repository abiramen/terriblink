import os
from sys import exit
from hashlib import pbkdf2_hmac
from base64 import b64encode
from app import app
import hmac
from urllib.parse import urlparse, ParseResult
import string
import re
import validators
from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////var/www/terriblink.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SECRET_KEY = os.getenv('SECRET_KEY') 
ADMIN_PASSWD = os.getenv('ADMIN_PASSWD') 

if SECRET_KEY is None or ADMIN_PASSWD is None:
    print('WARNING: NO SECRET KEY AND/OR HASHED PASSWORD IS SET')
    exit()

app.config['SECRET_KEY'] = SECRET_KEY
db = SQLAlchemy(app)

RESERVED = ['admin', 'add', 'delete']

def hash(passwd):
    return b64encode(pbkdf2_hmac('sha256', passwd.encode(), b'', 32768)).decode()

def check_passwd(passwd):
    return hmac.compare_digest(ADMIN_PASSWD, hash(passwd))

class Shortlink(db.Model):
    link = db.Column(db.String(30), primary_key=True)
    dest = db.Column(db.String(1000))

@app.route('/')
def index():
    return 'Nothing to see here!'

def render_admin(message=''):
    shortlinks = Shortlink.query.all()
    return render_template('admin.html', message=message, shortlinks=shortlinks)

@app.route('/admin', methods=['POST', 'GET'])
def admin():
    if 'logged_in' not in session:
        session['logged_in'] = False
    if 'message' not in session:
        session['message'] = ''

    if request.method == 'GET':
        if session['logged_in']:
            message = session['message']
            session.pop('message') 
            return render_admin(message=message)
        else:
            return render_template('login.html', message='')
    else:
        if session['logged_in']:
            session['logged_in'] = False
            return render_template('login.html', message='You have been logged out.')
        else:
            if check_passwd(request.form['password']):
                session['logged_in'] = True
                return render_admin(message="Logged in!")
            else:
                return render_template('login.html', message='Incorrect password.')

@app.route('/add', methods=['POST'])
def add():
    if 'logged_in' in session and session['logged_in']:
        link = request.form['link'].lower()
        dest = request.form['dest']
        p = urlparse(dest, 'https')
        netloc = p.netloc or p.path
        path = p.path if p.netloc else ''
        p = ParseResult('https', netloc, path, *p[3:])
        dest = p.geturl()


        if re.match(r'[a-z0-9-]{1,30}', link) is not None and \
           Shortlink.query.get(link) is None and \
           validators.url(dest):
            shortlink = Shortlink(link=link, dest=dest)
            db.session.add(shortlink)
            db.session.commit()
            session['message'] = 'Added!'
            return redirect(url_for('admin'))
        else:
            session['message'] = 'There was an issue. Please check your input.'
            return redirect(url_for('admin'))
    
    else:
        return '403 Forbidden', 403

@app.route('/delete/<shortlink>', methods=['GET'])
def delete(shortlink):
    if 'logged_in' in session and session['logged_in']:
        result = Shortlink.query.filter_by(link=shortlink)
        if result is not None:
            result.delete()
            db.session.commit()
            session['message'] = f'Deleted {shortlink}.'
            return redirect(url_for('admin'))
        else:
            session['message'] = 'Error: already removed.'
            return redirect(url_for('admin'))
    else:
        return '403 Forbidden', 403



@app.route('/favicon.ico')
def favicon():
    return ''

@app.route('/<path>', methods=['GET'])
def catch_all(path):
    result = Shortlink.query.get(path)
    if result is not None:
        return redirect(result.dest)
    else:
        return "Invalid link", 404
