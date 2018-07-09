from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, make_response, abort
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, scoped_session
from model import Base, User, Spending
from flask import session as login_session
import random
import string

# Neccessary imports for oauth for Google and Facebook
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2

import json
import requests




app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "User Expense Tracking Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///userSpending.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = scoped_session(DBSession)




##########################################################
# Create anti-forgery state token
@app.route('/login')
def showLogin():
    if 'username' in login_session:
        return redirect('/spending')
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response



@app.route('/spending/JSON')
def spendingJSON():
    if 'username' not in login_session:
        return abort(403)
        
    spendings = session.query(Spending).filter_by(user_id=login_session['user_id'])
    return jsonify(spendings=[s.serialize for s in spendings])

# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        return redirect(url_for('showSpendings'))
    else:
        return redirect(url_for('showSpendings'))




#########################################################


# Front page to enter the page. 
# If user is logged in, it will lead to users spending, or provide a logout link
# If user is not logged in, it will lead user to login.
@app.route('/')
def frontPage():
    return render_template('frontPage.html')

# Show all spending accounts by the current user
@app.route('/spending/')
def showSpendings():
    if 'username' not in login_session:
        return redirect('/')
    spendings = session.query(Spending).filter_by(user_id=login_session['user_id']).order_by(asc(Spending.name))
    return render_template('spending.html', spendings=spendings)

# Add new spending
@app.route('/spending/new/', methods=['GET', 'POST'])
def newSpending():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newSpending = Spending(name=request.form['name'], 
                                merchant=request.form['merchant'], 
                                price=request.form['price'],
                                user_id=login_session['user_id'])
        session.add(newSpending)
        flash('New Spending %s Successfully Created' % newSpending.name)
        session.commit()
        return redirect(url_for('showSpendings'))
    else:
        return render_template('newSpending.html')


# Edit a spending
@app.route('/spending/<int:spending_id>/edit/', methods=['GET', 'POST'])
def editSpending(spending_id):
    editedSpending = session.query(Spending).filter_by(id=spending_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        ## TO-DO
        if request.form['name']:
            editedSpending.name = request.form['name']
        if request.form['merchant']:
            editedSpending.merchant = request.form['merchant']
        if request.form['price']:
            editedSpending.price = request.form['price']
        session.add(editedSpending)   
        session.commit() 
        flash('Spending Successfully Edited %s' % editedSpending.name)
        return redirect(url_for('showSpendings'))
    else:
        return render_template('editSpending.html', spending=editedSpending)





# Show a specific expense
@app.route('/spending/<int:spending_id>/')
def readSpending(spending_id):
    if 'username' not in login_session:
        return redirect('/login')
    spending = session.query(Spending).filter_by(id=spending_id).one()
    return render_template('readSpending.html', spending=spending)

# Delete a expense
@app.route('/spending/<int:spending_id>/delete/', methods=['GET', 'POST'])
def deleteSpending(spending_id):
    if 'username' not in login_session:
        return redirect('/login')
    spending = session.query(
        Spending).filter_by(id=spending_id).one()
    if request.method == 'POST':
        session.delete(spending)
        flash('%s Successfully Deleted' % spending.name)
        session.commit()
        spendings = session.query(Spending).order_by(asc(Spending.name))
        return redirect(url_for('showSpendings', spendings=spendings))
    else:
        return render_template('deleteSpending.html', spending=spending)



if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)