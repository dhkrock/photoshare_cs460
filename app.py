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

# for image uploading
import os, base64
from datetime import date
import re

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

# These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '1210'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# begin code used for login
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
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
    data = cursor.fetchall()
    pwd = str(data[0][0])
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
    # The request method is POST (page is recieving data)
    email = flask.request.form['email']
    cursor = conn.cursor()
    # check if email is registered
    if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
        data = cursor.fetchall()
        pwd = str(data[0][0])
        if flask.request.form['password'] == pwd:
            user = User()
            user.id = email
            flask_login.login_user(user)  # okay login in user
            return flask.redirect(flask.url_for('protected'))  # protected is a function defined in this file

    # information did not match
    return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('hello.html', message='Logged out')


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')


# you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')


@app.route("/register", methods=['POST'])
def register_user():
    try:
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        birth_date = request.form.get('birth_date')
        hometown = request.form.get('hometown')
        gender = request.form.get('gender')
        password = request.form.get('password')
    except:
        print(
            "couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test = isEmailUnique(email)
    if test:
        print(cursor.execute(
            "INSERT INTO Users (first_name, last_name, email, birth_date, hometown, gender, password) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(
                first_name, last_name, email, birth_date, hometown, gender, password)))
        conn.commit()
        # log user in
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
    return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]


def getUserIdFromEmail(email):
    cursor = conn.cursor()
    print(cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email)))
    return cursor.fetchone()[0]


def isEmailUnique(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True


def albumExists(album, uid):
    cursor = conn.cursor()
    if cursor.execute(
            "SELECT album_name, user_id FROM Albums WHERE album_name = '{0}' AND user_id = '{1}'".format(album, uid)):
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


def commenterCheck(uid, pid):
    cursor = conn.cursor()
    if cursor.execute("SELECT user_id FROM Photos WHERE user_id = '{0}' AND photo_id = '{1}'".format(uid, pid)):
        return True
    else:
        return False


def likesCheck(uid, pid):
    cursor = conn.cursor()
    if cursor.execute(
            "SELECT user_id, photo_id FROM LIKES WHERE user_id = '{0}' AND photo_id = '{1}'".format(uid, pid)):
        return True
    else:
        return False


def tagDoesNotExist(tag):
    cursor = conn.cursor()
    if cursor.execute("SELECT name FROM Tags WHERE name = '{0}'".format(tag)):
        return False
    else:
        return True

def countX(tup, y):
    count = 0
    for x in range(len(tup)):
        if (tup[x][0] == y):
            count = count + 1
    return count

def tagCount(pid):
    cursor = conn.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM Tagged WHERE Tagged.photo_id = '{0}'".format(pid))
    return cursor.fetchone()[0]

# end login code

@app.route('/profile')
@flask_login.login_required
def protected():
    return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")


# begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/friends', methods=['GET', 'POST'])
def friends():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    friend_email = request.form.get('friend_email')
    cursor = conn.cursor()
    if friendExists(friend_email):
        print(cursor.execute("INSERT INTO Friends(user_id1, user_id2) VALUES ('{0}', '{1}')".format(uid,
                                                                                                    getUserIdFromEmail(
                                                                                                        friend_email))))
        conn.commit()
    # query to find user's friends
    friends = cursor.execute(
        "SELECT first_name, last_name, email FROM Users u INNER JOIN Friends f On user_id2 = user_id WHERE user_id1 ='{0}'".format(
            uid))
    friends = cursor.fetchall()
    friend_recs = cursor.execute(
        "SELECT first_name, last_name, email, COUNT(*) FROM Friends f1 INNER JOIN Users u ON f1.user_id2 = user_id WHERE f1.user_id1 IN (SELECT user_id2 FROM Friends f WHERE f.user_id1='{0}') AND f1.user_id2 NOT IN (SELECT user_id2 FROM Friends f WHERE f.user_id1 = '{0}') AND f1.user_id2 <> '{0}' GROUP BY email ORDER BY COUNT(*) DESC".format(
            uid))
    friend_recs = cursor.fetchall()
    print(friend_recs)
    return render_template('friends.html', friends=friends, friend_recs=friend_recs)


@app.route('/top_users', methods=['GET', 'POST'])
def top_users():
    cursor = conn.cursor()
    users = cursor.execute("SELECT first_name, last_name, email, score FROM users ORDER BY score DESC LIMIT 10")
    users = cursor.fetchall()
    return render_template('top_users.html', users=users)


@app.route('/create_album', methods=['GET'])
def create():
    return render_template('create_album.html')


@app.route('/create_album', methods=['POST'])
def create_album():
    try:
        album_name = request.form.get('album_name')
        doc = request.form.get('doc')
    except:
        print(
            "couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('create_album'))
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    test = albumExists(album_name, uid)
    if test:
        flash("This album already exists!")
        return flask.redirect(flask.url_for('create_album'))
    else:
        print(cursor.execute(
            "INSERT INTO Albums(album_name, album_date, user_id) VALUES ('{0}', '{1}', '{2}')".format(album_name, doc,
                                                                                                      uid)))
        conn.commit()
    return render_template('hello.html', name=flask_login.current_user.id, message="Album created")


@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
    if request.method == 'POST':
        cursor = conn.cursor()
        uid = getUserIdFromEmail(flask_login.current_user.id)
        imgfile = request.files['photo']
        caption = request.form.get('caption')
        album = request.form.get('album')
        photo_data = imgfile.read()
        test = albumExists(album, uid)
        if test:
            aid = findAlbumID(album, uid)
            cursor.execute('''INSERT INTO Photos(imgdata, user_id, caption, albums_id) VALUES (%s, %s, %s, %s)''',
                           (photo_data, uid, caption, aid))
            cursor.execute("UPDATE Users SET score = score + 1 WHERE user_id = '{0}'".format(uid))
            conn.commit()
        else:
            flash("That album does not exist! Try again with another album.")
            return flask.redirect(flask.url_for('upload_file'))
        return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!',
                               photos=getUsersPhotos(uid), base64=base64)
    # The method is GET so we return a  HTML form to upload the a photo.
    else:
        return render_template('upload.html')


# end photo uploading code

@app.route('/tags', methods=['GET'])
def tags_g():
    pid = request.args.get("id")
    flask.session['pidtags'] = pid
    return render_template('tags.html')


@app.route('/tags', methods=['POST'])
def tags():
    cursor = conn.cursor()
    pid = flask.session['pidtags']
    tags = request.form.get("tags")
    if tagDoesNotExist(tags) == True:
        cursor.execute('''INSERT INTO Tags(name) VALUES (%s)''', (tags))
        conn.commit()
        cursor.execute('''INSERT INTO Tagged(photo_id, tag_id) VALUES(%s,%s)''', (pid, cursor.lastrowid))
        conn.commit()
    else:
        cursor = conn.cursor()
        tid = cursor.execute("SELECT tag_id FROM Tags WHERE name = '{0}'".format(tags))
        tid = cursor.fetchall()
        cursor.execute('''INSERT INTO Tagged(photo_id, tag_id) VALUES(%s,%s)''', (pid, tid))
        conn.commit()
    return render_template('tags.html')


@app.route('/your_tags_hyperlink', methods=['GET', 'POST'])
def your_tags_hyperlink():
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    tags = cursor.execute(
        "SELECT DISTINCT Tags.tag_id, name FROM ((Tags INNER JOIN Tagged on Tags.tag_id = Tagged.tag_id) INNER JOIN Photos ON Photos.user_id = '{0}' AND Tagged.photo_id = Photos.photo_id)".format(
            uid))
    tags = cursor.fetchall()
    print(tags)
    return render_template('your_tags_hyperlink.html', tags=tags)


@app.route('/view_tags_personal', methods=['GET', 'POST'])
def view_tags_personal():
    tid = request.args.get('id')
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    tags_photos_v = cursor.execute(
        "SELECT DISTINCT imgdata, caption FROM ((Tags INNER JOIN Tagged on Tags.tag_id = Tagged.tag_id AND Tags.tag_id = '{0}') INNER JOIN Photos ON Photos.user_id = '{1}' AND Tagged.photo_id = Photos.photo_id)".format(
            tid, uid))
    tags_photos_v = cursor.fetchall()
    return render_template('view_tags_personal.html', photos=tags_photos_v, base64=base64)


@app.route('/all_tags_hyperlink', methods=['GET', 'POST'])
def all_tags_hyperlink():
    cursor = conn.cursor()
    uid = getUserIdFromEmail(flask_login.current_user.id)
    tags = cursor.execute("SELECT DISTINCT Tags.tag_id, name FROM Tags")
    tags = cursor.fetchall()
    print(tags)
    return render_template('all_tags_hyperlink.html', tags=tags)


@app.route('/view_tags_all', methods=['GET', 'POST'])
def view_tags_all():
    tid = request.args.get('id')
    cursor = conn.cursor()
    tags_photos_v = cursor.execute(
        "SELECT DISTINCT imgdata, caption FROM Tagged INNER JOIN Photos ON tag_id = '{0}' AND Tagged.photo_id = Photos.photo_id".format(
            tid))
    tags_photos_v = cursor.fetchall()
    return render_template('view_tags_all.html', photos=tags_photos_v, base64=base64)

@app.route('/most_popular', methods=['GET', 'POST'])
def most_popular():
    cursor = conn.cursor()
    tags = cursor.execute("SELECT name, Tags.tag_id FROM Tags INNER JOIN (SELECT DISTINCT tag_id, photo_id FROM Tagged) AS T ON Tags.tag_id = T.tag_id GROUP BY name ORDER BY COUNT(*) DESC")
    tags = cursor.fetchall()
    return render_template('most_popular.html', tags=tags)

@app.route('/popular_tagview', methods=['GET', 'POST'])
def popular_tagview():
    tid = request.args.get('id')
    cursor = conn.cursor()
    tags_photos_v = cursor.execute(
        "SELECT DISTINCT imgdata, caption FROM Tagged INNER JOIN Photos ON tag_id = '{0}' AND Tagged.photo_id = Photos.photo_id".format(
            tid))
    tags_photos_v = cursor.fetchall()
    return render_template('popular_tagview.html', photos=tags_photos_v, base64=base64)

@app.route('/search_tags', methods=['GET'])
def search_t():
    return render_template('search_tags.html')

@app.route('/search_tags', methods=['POST'])
def search_tags():
    cursor = conn.cursor()
    search = request.form.get("search")
    search = re.split("\s", search)
    l = tuple(search)
    params = {'l': l}
    if(len(l) > 1):
        photo_ids = cursor.execute("SELECT Photos.photo_id FROM ((Tags INNER JOIN Tagged on Tags.tag_id = Tagged.tag_id AND Tags.name IN %(l)s) INNER JOIN PHOTOS ON Tagged.photo_id = Photos.photo_id)", params)
        photo_ids = cursor.fetchall()
        distinct_photo_ids = cursor.execute("SELECT DISTINCT Photos.photo_id FROM ((Tags INNER JOIN Tagged on Tags.tag_id = Tagged.tag_id AND Tags.name IN %(l)s) INNER JOIN PHOTOS ON Tagged.photo_id = Photos.photo_id)", params)
        distinct_photo_ids = cursor.fetchall()
        results = ()
        for x in range(len(distinct_photo_ids)):
            if(countX(photo_ids,distinct_photo_ids[x][0]) == len(l)):
                results = results + (distinct_photo_ids[x][0],)
        l = results
        params = {'l': l}
        photos = cursor.execute("SELECT imgdata, caption FROM Photos WHERE photo_id IN %(l)s", params)
        photos = cursor.fetchall()
        return render_template('search_tags.html', photos=photos, base64=base64)
    else:
        search = request.form.get("search")
        photos = cursor.execute("SELECT DISTINCT imgdata, caption FROM ((Tags INNER JOIN Tagged on Tags.tag_id = Tagged.tag_id AND Tags.name = '{0}') INNER JOIN Photos ON Tagged.photo_id = Photos.photo_id)".format(search))
        photos = cursor.fetchall()
        return render_template('search_tags.html', photos=photos, base64=base64)

@app.route('/view_photos', methods=['GET', 'POST'])
def view_photos():
    cursor = conn.cursor()
    photos_v = cursor.execute("SELECT imgdata, photo_id, caption FROM Photos")
    photos_v = cursor.fetchall()
    return render_template('view_photos.html', photos=photos_v, base64=base64)

@app.route('/view_comments', methods=['GET', 'POST'])
def view_comments():
    cursor = conn.cursor()
    pid = request.args.get("id")
    like = request.form.get("like")
    if flask_login.current_user.is_anonymous == False:
        uid = getUserIdFromEmail(flask_login.current_user.id)
        if (like == "yes") and (likesCheck(uid, pid) == False):
            flash("Successfully liked!")
            cursor.execute('''INSERT INTO Likes(photo_id, user_id, email) VALUES (%s,%s,%s)''',
                   (pid, uid, flask_login.current_user.id))
            conn.commit()
        elif (like == "yes") and likesCheck(uid, pid):
            flash("Can't like again!")
    else:
        if(like == "yes"):
            flash("Anonymous users cannot like!")
    photos_v = cursor.execute("SELECT imgdata, photo_id, caption FROM Photos WHERE photo_id = '{0}'".format(pid))
    photos_v = cursor.fetchall()
    comments = cursor.execute("SELECT user_id, email, text, date FROM Comments WHERE photo_id = '{0}'".format(pid))
    comments = cursor.fetchall()
    likes_count = cursor.execute("SELECT COUNT(*) FROM Likes WHERE photo_id = '{0}'".format(pid))
    likes_count = cursor.fetchall()
    likes_email = cursor.execute("SELECT email FROM Likes WHERE photo_id = '{0}'".format(pid))
    likes_email = cursor.fetchall()
    return render_template('view_comments.html', photos=photos_v, comments=comments, likes_count=likes_count,
                           likes_email=likes_email, base64=base64)


@app.route('/add_comment', methods=['GET'])
def add_comment_g():
    pid = request.args.get("id")
    flask.session['pid'] = pid
    return render_template('add_comment.html')


@app.route('/add_comment', methods=['POST'])
def add_comment():
    cursor = conn.cursor()
    pid = flask.session['pid']
    today = date.today()
    current_date = today.strftime("%Y/%m/%d")
    comment = request.form.get('comment')
    if (flask_login.current_user.is_anonymous):
        cursor.execute('''INSERT INTO Comments(photo_id, text, date) VALUES (%s,%s,%s)''', (pid, comment, current_date))
        conn.commit()
        flash("Comment posted!")
        return render_template('add_comment.html')
    else:
        uid = getUserIdFromEmail(flask_login.current_user.id)
        if (commenterCheck(uid, pid)):
            flash("You can't comment on your own photo!")
            return render_template('add_comment.html')
        else:
            cursor.execute('''INSERT INTO Comments(user_id, email, photo_id, text, date) VALUES (%s,%s,%s,%s,%s)''',
                           (uid, flask_login.current_user.id, pid, comment, current_date))
            cursor.execute("UPDATE Users SET score = score + 1 WHERE user_id = '{0}'".format(uid))
            conn.commit()
            flash("Comment posted!")
            return render_template('add_comment.html')


@app.route('/search_comment', methods=['GET'])
def search_c():
    return render_template('search_comment.html')


@app.route('/search_comment', methods=['POST'])
def search_comment():
    cursor = conn.cursor()
    search = request.form.get("search")
    print(search)
    users = cursor.execute(
        "SELECT email FROM Comments WHERE text = '{0}' GROUP BY email ORDER BY COUNT(email) DESC".format(search))
    users = cursor.fetchall()
    print(users)
    return render_template('search_comment.html', users=users)


@app.route('/view_albums', methods=['GET', 'POST'])
def view_albums():
    cursor = conn.cursor()
    albums_v = cursor.execute("SELECT albums_id, album_name FROM Albums")
    albums_v = cursor.fetchall()
    return render_template('view_albums.html', albums=albums_v)


@app.route('/view_albums_photos', methods=['GET', 'POST'])
def view_albums_photos():
    aid = request.args.get('id')
    cursor = conn.cursor()
    albums_photos_v = cursor.execute(
        "SELECT imgdata, photo_id, caption FROM Photos WHERE albums_id = '{0}'".format(aid))
    albums_photos_v = cursor.fetchall()
    return render_template('view_albums_photos.html', photos=albums_photos_v, base64=base64)


@app.route('/your_photos', methods=['GET', 'POST'])
def your_photos():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    pid = request.values.get("id")
    cursor = conn.cursor()
    photos = cursor.execute("SELECT imgdata, photo_id, caption FROM Photos WHERE user_id = '{0}'".format(uid))
    photos = cursor.fetchall()
    return render_template('your_photos.html', photos=photos, base64=base64)


@app.route('/delete_photo', methods=['GET', 'POST'])
def delete_photos():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    pid = request.values.get("id")
    cursor = conn.cursor()
    if pid:
        cursor.execute("DELETE FROM Photos WHERE photo_id = '{0}'".format(pid))
        flash("Photo deleted successfully!")
        cursor.execute("UPDATE Users SET score = score - 1 WHERE user_id = '{0}'".format(uid))
        conn.commit()
    photos = cursor.execute("SELECT imgdata, photo_id, caption FROM Photos WHERE user_id = '{0}'".format(uid))
    photos = cursor.fetchall()
    return render_template('delete_photo.html', message="Photo deleted!", photos=photos, base64=base64)


@app.route('/delete_album', methods=['GET', 'POST'])
def delete_album():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    aid = request.args.get('id')
    cursor = conn.cursor()
    if aid:
        cursor.execute(
            "UPDATE Users SET score = score - (SELECT COUNT(*) FROM Photos WHERE albums_id = '{0}')  WHERE user_id = '{1}'".format(
                aid, uid))
        cursor.execute("DELETE FROM Albums WHERE albums_id = '{0}'".format(aid))
        flash("Album deleted successfully!")
        conn.commit()
    albums_v = cursor.execute("SELECT albums_id, album_name FROM Albums WHERE user_id = '{0}'".format(uid))
    albums_v = cursor.fetchall()
    return render_template('delete_album.html', albums=albums_v)

@app.route('/youmayalsolike', methods=['GET','POST'])
def youmayalsolike():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    five_tags = cursor.execute("SELECT Tags.tag_id FROM ((Tags INNER JOIN (SELECT DISTINCT tag_id, photo_id FROM Tagged) AS T ON Tags.tag_id = T.tag_id) INNER JOIN Photos ON Photos.user_id = '{0}' AND T.photo_id = Photos.photo_id) GROUP BY name ORDER BY COUNT(*) DESC".format(uid))
    five_tags = cursor.fetchall()
    conv = ()
    for x in range(len(five_tags)):
        conv = conv + (five_tags[x][0],)
    params = {'l': conv}
    other_tags = cursor.execute("SELECT Tagged.photo_id, COUNT(*) FROM ((Tags INNER JOIN Tagged ON Tags.tag_id = Tagged.tag_id AND Tagged.tag_id IN %(l)s) INNER JOIN Photos ON Photos.user_id != '{0}' AND Tagged.photo_id = Photos.photo_id) GROUP BY Tagged.photo_id ORDER BY COUNT(*) DESC".format(uid), params)
    other_tags = cursor.fetchall()
    tag_count = []
    for x in range(len(other_tags)):
       tag_count.append(tagCount(other_tags[x][0]))
    list_other_tags = list(other_tags)
    for x in range(len(other_tags)-1):
        if(other_tags[x][1] == other_tags[x+1][1]):
            if(tag_count[x] < tag_count[x+1]):
                prev = list_other_tags[x]
                list_other_tags[x] = list_other_tags[x+1]
                list_other_tags[x+1] = prev
    pids = []
    for x in range(len(list_other_tags)):
        pids.append(list_other_tags[x][0])
    l = tuple(pids)
    print(l)
    params = {'l': l}
    photos = cursor.execute("SELECT imgdata, photo_id FROM Photos WHERE photo_id IN %(l)s",params)
    photos = cursor.fetchall()
    return render_template('youmayalsolike.html', photos=photos, base64=base64)

# default page
@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html', message='Welecome to Photoshare')


if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)
