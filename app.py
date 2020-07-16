from flask import Flask, render_template, request, redirect, session, flash
from flask_mysqldb import MySQL
from sklearn.model_selection import train_test_split
from werkzeug.security import generate_password_hash, check_password_hash
import os
import yaml
app = Flask(__name__)
db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

app.config['SECRET_KEY'] = os.urandom(24)

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    resultValue = cur.execute("SELECT * FROM news")
    if resultValue > 0:
        news = cur.fetchall()
        cur.close()
        return render_template('index.html', news=news)
    cur.close()
    return render_template('index.html', news=None)

@app.route('/about/')
def about():
    return render_template('about.html')
@app.route('/news/<int:id>/')
def news(id):
    cur = mysql.connection.cursor()
    resultValue = cur.execute("SELECT * FROM news WHERE news_id = {}".format(id))
    if resultValue > 0:
        new = cur.fetchone()
        return render_template('news.html', new=new)
    return 'Blog not found'

@app.route('/my_news/')
def my_news():
    author = session['firstname'] + ' ' + session['lastname']
    cur = mysql.connection.cursor()
    result_value = cur.execute("SELECT * FROM news WHERE author = %s",[author])
    if result_value > 0:
        my_news = cur.fetchall()
        return render_template('my_news.html',my_news=my_news)
    else:
        return render_template('my_news.html',my_news=None)
@app.route('/write_news/',methods=['GET', 'POST'])
def write_news():
    if request.method == 'POST':
        newspost = request.form
        title = newspost['title']
        body = newspost['body']
        import numpy as np
        import pandas as pd
        df = pd.read_csv('textfiles/d1.csv', sep='\t')
        from sklearn.model_selection import train_test_split
        X = df['Title']
        y = df['label']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        from sklearn.pipeline import Pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import LinearSVC
        # Linear SVC:
        text_clf_lsvc = Pipeline([('tfidf', TfidfVectorizer()),
                     ('clf', LinearSVC()),])
        
        text_clf_lsvc.fit(X_train, y_train)
        predictions = text_clf_lsvc.predict(X_test)
        from sklearn import metrics
        print(metrics.accuracy_score(y_test,predictions))
        l=text_clf_lsvc.predict([title])
        if(l[0]==1):
            author = session['firstname'] + ' ' + session['lastname']
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO news(title, body, author) VALUES(%s, %s, %s)", (title, body, author))
            mysql.connection.commit()
            cur.close()
            flash("Successfully posted new blog", 'success')
            return redirect('/my_news')
        else:
            flash("Not successfully posted please post related to covid",'danger')
            return render_template('write_news.html')
    return render_template('write_news.html')
@app.route('/my_news/<int:id>/')
def delete_blog(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM news WHERE news_id = {}".format(id))
    mysql.connection.commit()
    flash("Your news has been deleted", 'success')
    return redirect('/my_news')

@app.route('/login/',methods=['GET','POST'])
def login():
    if request.method =='POST':
        userDetails=request.form
        username=userDetails['username']
        cur=mysql.connection.cursor()
        resultValue=cur.execute("select * from user where username=%s",([username]))
        if resultValue>0:
            user=cur.fetchone()
            if check_password_hash(user['password'], userDetails['password']):
                session['login']=True
                session['firstname']=user['first_name']
                session['lastname']=user['last_name']
                flash('Welcome '+ session['firstname']+'! You are logged in','success')
            else:
                cur.close()
                flash('Password does not match','danger')
                return render_template('login.html')
        else:
            cur.close()
            flash('User not found','danger')
            return render_template('login.html')
        cur.close()
        return redirect('/my_news')
    return render_template('login.html')
@app.route('/register/',methods=['GET','POST'])
def register():
    if request.method =='POST':
        userDetails=request.form
        if userDetails['password']!=userDetails['confirm_password']:
            flash("Passwords do not match! Try Again.","danger")
            return render_template("register.html")
        cur=mysql.connection.cursor()
        cur.execute("insert into user(first_name, last_name, username, email, password)"\
        "values(%s,%s,%s,%s,%s)",(userDetails['first_name'],userDetails['last_name'],\
        userDetails['username'],userDetails['email'],generate_password_hash(userDetails['password'])))
        mysql.connection.commit()
        cur.close()
        flash('Registration successful! Please login.','success')
        return redirect('/login')
    return render_template('register.html')
@app.route('/edit-news/<int:id>/', methods=['GET', 'POST'])
def edit_news(id):
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        title = request.form['title']
        body = request.form['body']
        cur.execute("UPDATE news SET title = %s, body = %s where news_id = %s",(title, body, id))
        mysql.connection.commit()
        cur.close()
        flash('News updated successfully', 'success')
        return redirect('/my_news')
    return render_template('edit-news.html')
@app.route('/logout/')
def logout():
    session.clear()
    flash("You have been logged out", 'info')
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True, port=5001)
