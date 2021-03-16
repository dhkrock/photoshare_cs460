######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for, flash
from flaskext.mysql import MySQL
import flask_login

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '1210'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''
@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		first_name = request.form.get('first_name')
		last_name = request.form.get('last_name')
		email=request.form.get('email')
		birth_date=request.form.get('birth_date')
		hometown=request.form.get('hometown')
		gender=request.form.get('gender')
		password=request.form.get('password')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (first_name, last_name, email, birth_date, hometown, gender, password) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(first_name, last_name, email, birth_date, hometown, gender, password)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("registered already")
		flash('A user is already registered with that email')
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, photo_id, caption FROM Photos WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True

def albumExists(album, uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT album_name, user_id FROM Albums WHERE album_name = '{0}' AND user_id = '{1}'".format(album, uid)):
		return True
	else:
		return False

def findAlbumID(album, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id FROM Albums WHERE album_name = '{0}' AND user_id = '{1}'".format(album, uid))
	return cursor.fetchone()[0]

def friendExists(friend_email):
	cursor = conn.cursor()
	if cursor.execute("SELECT email FROM Users WHERE email = '{0}'".format(friend_email)):
		return True
	else:
		False
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/friends', methods = ['GET','POST'])
def friends():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	friend_email = request.form.get('friend_email')
	cursor = conn.cursor()
	if friendExists(friend_email):
		print(cursor.execute("INSERT INTO Friends(user_id1, user_id2) VALUES ('{0}', '{1}')".format(uid, getUserIdFromEmail(friend_email))))
		conn.commit()
	#query to find user's friends
	friends = cursor.execute("SELECT first_name, last_name, email FROM Users u INNER JOIN Friends f On user_id2 = user_id WHERE user_id1 ='{0}'".format(uid))
	friends = cursor.fetchall()
	friend_recs = cursor.execute("SELECT first_name, last_name, email, COUNT(*) FROM Friends f1 INNER JOIN Users u ON f1.user_id2 = user_id WHERE f1.user_id1 IN (SELECT user_id2 FROM Friends f WHERE f.user_id1='{0}') AND f1.user_id2 NOT IN (SELECT user_id2 FROM Friends f WHERE f.user_id1 = '{0}') AND f1.user_id2 <> '{0}' GROUP BY email ORDER BY COUNT(*) DESC".format(uid))
	friend_recs = cursor.fetchall()
	print(friend_recs)
	return render_template('friends.html', friends=friends, friend_recs = friend_recs)

@app.route('/top_users', methods = ['GET', 'POST'])
def top_users():
	cursor = conn.cursor()
	users = cursor.execute("SELECT first_name, last_name, email, score FROM users ORDER BY score DESC LIMIT 10")
	users = cursor.fetchall()
	return render_template('top_users.html', users = users)

@app.route('/create_album', methods = ['GET'])
def create():
	return render_template('create_album.html')

@app.route('/create_album', methods = ['POST'])
def create_album():
	try:
		album_name = request.form.get('album_name')
		doc = request.form.get('doc')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('create_album'))
	cursor = conn.cursor()
	uid = getUserIdFromEmail(flask_login.current_user.id)
	test = albumExists(album_name, uid)
	if test:
		flash("This album already exists!")
		return flask.redirect(flask.url_for('create_album'))
	else:
		print(cursor.execute("INSERT INTO Albums(album_name, album_date, user_id) VALUES ('{0}', '{1}', '{2}')".format(album_name, doc, uid)))
		conn.commit()
	return render_template('hello.html', name=flask_login.current_user.id, message="Album created")

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		album = request.form.get('album')
		photo_data =imgfile.read()
		cursor = conn.cursor()
		test = albumExists(album,uid)
		if test:
			aid = findAlbumID(album, uid)
			cursor.execute('''INSERT INTO Photos(imgdata, user_id, caption, albums_id) VALUES (%s, %s, %s, %s)''', (photo_data, uid, caption, aid))
			cursor.execute("UPDATE Users SET score = score + 1 WHERE user_id = '{0}'".format(uid))
			conn.commit()
		else:
			flash("That album does not exist! Try again with another album.")
			return flask.redirect(flask.url_for('upload_file'))
		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid),base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code

@app.route('/view_photos', methods = ['GET', 'POST'])
def view_photos():
	cursor = conn.cursor()
	photos_v = 	cursor.execute("SELECT imgdata, photo_id, caption FROM Photos")
	photos_v = cursor.fetchall()
	return render_template('view_photos.html', photos=photos_v, base64=base64)

@app.route('/view_albums', methods = ['GET','POST'])
def view_albums():
	cursor = conn.cursor()
	albums_v = cursor.execute("SELECT albums_id, album_name FROM Albums")
	albums_v = cursor.fetchall()
	return render_template('view_albums.html', albums=albums_v)

@app.route('/view_albums_photos', methods = ['GET','POST'])
def view_albums_photos():
	aid = request.args.get('id')
	cursor = conn.cursor()
	albums_photos_v = cursor.execute("SELECT imgdata, photo_id, caption FROM Photos WHERE albums_id = '{0}'".format(aid))
	albums_photos_v = cursor.fetchall()
	return render_template('view_albums_photos.html', photos=albums_photos_v, base64=base64)

@app.route('/delete_photo', methods = ['GET', 'POST'])
def delete_photos():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	pid = request.values.get("id")
	cursor = conn.cursor()
	if pid:
		cursor.execute("DELETE FROM Photos WHERE photo_id = '{0}'".format(pid))
		flash("Photo deleted successfully!")
		conn.commit()
	photos = cursor.execute("SELECT imgdata, photo_id, caption FROM Photos WHERE user_id = '{0}'".format(uid))
	photos = cursor.fetchall()
	return render_template('delete_photo.html', message="Photo deleted!", photos=photos, base64=base64)

@app.route('/delete_album', methods = ['GET', 'POST'])
def delete_album():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	aid = request.args.get('id')
	cursor = conn.cursor()
	if aid:
		cursor.execute("DELETE FROM Albums WHERE albums_id = '{0}'".format(aid))
		flash("Album deleted successfully!")
		conn.commit()
	albums_v = cursor.execute("SELECT albums_id, album_name FROM Albums WHERE user_id = '{0}'".format(uid))
	albums_v = cursor.fetchall()
	return render_template('delete_album.html', albums=albums_v)

@app.route('/comments/addComment/<photoID>', methods=['GET'])
def comments(photoID):
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('comments.html', message="Leave a comment!", addComment="True", name=flask_login.current_user.id, photoID=photoID)
	except:
		return render_template('comments.html', message="Leave a comment!", addComment="True", photoID=photoID)

@app.route('/comments/<commentPhotoId>', methods=['GET'])
def viewComments(commentPhotoId):
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		cursor = conn.cursor()
		cursor.execute("SELECT comments_text, comments_owner_name, date_of_comments FROM Comments WHERE Photos_photos_id = '{0}'".format(commentPhotoId))
		comments_list=cursor.fetchall()
		return render_template('comments.html', name=flask_login.current_user.id, message="Here are the comments of this photo", comments= comments_list, photoID=commentPhotoId)
	except:
		cursor = conn.cursor()
		cursor.execute("SELECT comments_text, comments_owner_name, date_of_comments FROM Comments WHERE Photos_photos_id = '{0}'".format(commentPhotoId))
		comments_list=cursor.fetchall()
		return render_template('comments.html', message="Here are the comments of this photo", comments= comments_list, photoID=commentPhotoId)



@app.route('/leaveComments/<photoID>', methods=['POST'])
def leaveComments(photoID):
	comments_text=request.form.get('comment')
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		comments_owner_name = findUserNameFromId(uid)
	except:
		uid = None
		comments_owner_name = 'Other User'
	date_of_comments= time.strftime("%Y-%m-%d")
	photos_owner_id=findPhotoOwnerId(photoID)
	if photos_owner_id==uid:
		comments_list=search_comments(photoID)
		return render_template ('comments.html', message='You can\'t leave a comment in your own photo', comments=comments_list, name=flask_login.current_user.id)
	if uid == None:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Comments(comments_text, comments_owner_name, date_of_comments, Photos_photos_id) VALUES ('{0}', '{1}', '{2}', '{3}')".format(comments_text, comments_owner_name, date_of_comments, photoID))
		conn.commit()
	else:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Comments(comments_text, comments_owner_name, date_of_comments, Photos_photos_id, comment_owner_id) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}')".format(comments_text, comments_owner_name, date_of_comments, photoID, uid))
		conn.commit()
	comments_list=search_comments(photoID)
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('comments.html', message="Comment created!", name=flask_login.current_user.id, comments=comments_list)
	except:
		return render_template('comments.html', message="Comment created!", comments=comments_list)

def search_comments(photos_id):
	cursor = conn.cursor()
	cursor.execute("SELECT comments_text, comments_owner_name, date_of_comments, comments_id FROM Comments WHERE Photos_photos_id = '{0}'".format(photos_id))
	return cursor.fetchall()

#default page
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welecome to Photoshare')

if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)