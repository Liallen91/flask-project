from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, current_user, logout_user
import hashlib

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
app.config['SECRET_KEY'] = "aforum"

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

salt="HasAASdwsg"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    discussions = db.relationship('Discussion', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy='dynamic')
    comments_upvoted = db.relationship('Comment',
                secondary='user_comment_upvotes',
                backref='users_upvoted')
    comments_downvoted = db.relationship('Comment',
                secondary='user_comment_downvotes',
                backref='users_downvoted')

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discussion_topic = db.Column(db.String(20), nullable=False)
    discussion_text = db.Column(db.String(100), nullable=False)
    discussion_category = db.Column(db.String(20), nullable=False)
    discussion_replies = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='discussion', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(100), nullable=False)
    votes = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    db.UniqueConstraint('user_id', 'comment_id', name='user_comment_unique')

class UserCommentUpvote(db.Model):
    __tablename__ = 'user_comment_upvotes'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), primary_key=True)

class UserCommentDownvote(db.Model):
    __tablename__ = 'user_comment_downvotes'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), primary_key=True)

with app.app_context():
    db.create_all() 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def main():
    all_discussions = Discussion.query.all()
    return render_template('main.html', all_discussions=all_discussions)

@app.route('/filter')
def filter():
    cat = request.args.get('cat')
    print(cat)
    if (cat == "All"):
        filter_discussions = Discussion.query.all()
        return render_template('filtered.html', filter_discussions=filter_discussions)
    else:   
        filter_discussions = Discussion.query.filter_by(discussion_category=cat).all()
        return render_template('filtered.html', filter_discussions=filter_discussions)

@app.route('/new_discussion', methods=['GET', 'POST'])
def new_discussion():
    if current_user.is_authenticated:
        render_template('new_discussion.html')
        if request.method == 'POST':
            discussion_topic = request.form['discussion_topic']
            discussion_text = request.form['discussion_text']
            discussion_category = request.form['discussion_category']
            if discussion_topic=='' or  discussion_text=='' or discussion_category=='':
                None
            else:
                discussion = Discussion(discussion_topic=discussion_topic, discussion_text=discussion_text, 
                    discussion_category=discussion_category, discussion_replies=0, user_id=current_user.id)
                db.session.add(discussion)
                db.session.commit()
                return redirect(url_for('main'))
    else:
        return render_template('login.html')
    return render_template('new_discussion.html')

@app.route('/discussion_link/<disc_name>', methods=['GET', 'POST'])
def discussion_link(disc_name):
    disc_id = Discussion.query.filter_by(discussion_topic=disc_name).first()
    disc = Discussion.query.filter_by(discussion_topic=disc_name)
    user = User.query.filter_by(id=disc_id.user_id).first()
    comments = Comment.query.filter_by(discussion_id=disc_id.id).all()
    return render_template('discussion_link.html', disc=disc, comments=comments, user=user)

@app.route('/discussions/<disc_name>/submit_comment', methods=['POST'])
def submit_comment(disc_name):
    comment = request.form.get('comment')
    disc_id = Discussion.query.filter_by(discussion_topic=disc_name).first()
    com = Comment(comment=comment, votes=0, discussion_id=disc_id.id, user_id=current_user.id)
    disc_id.discussion_replies += 1
    db.session.add(com)
    db.session.commit()
    return redirect(url_for('discussion_link', disc_name=disc_name))

@app.route('/upvote/<disc_name>/<int:comment_id>', methods=['POST'])
def upvote(disc_name, comment_id):
    if current_user.is_authenticated:
        comment = Comment.query.filter_by(id=comment_id).first()
        user = User.query.filter_by(id=current_user.id).first()
        if comment in user.comments_upvoted:
            comment.votes -= 1
            user.comments_upvoted.remove(comment)
        else:
            comment.votes += 1
            user.comments_upvoted.append(comment)
            if comment in user.comments_downvoted:
                comment.votes += 1
                user.comments_downvoted.remove(comment)
        db.session.commit()
    else:
        return render_template('login.html')
    return redirect(url_for('discussion_link', disc_name=disc_name))

@app.route('/downvote/<disc_name>/<int:comment_id>', methods=['POST'])
def downvote(disc_name, comment_id):
    if current_user.is_authenticated:
        comment = Comment.query.filter_by(id=comment_id).first()
        user = User.query.filter_by(id=current_user.id).first()
        if comment in user.comments_downvoted:
            comment.votes += 1
            user.comments_downvoted.remove(comment)
        else:
            comment.votes -= 1
            user.comments_downvoted.append(comment)
            if comment in user.comments_upvoted:
                comment.votes -= 1
                user.comments_upvoted.remove(comment)
        db.session.commit()
    else:
        return render_template('login.html')
    return redirect(url_for('discussion_link', disc_name=disc_name))


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        logout_user()
        return redirect(url_for('main'))
    else:
        return render_template('logout.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db_password = password + salt
        h = hashlib.md5(db_password.encode())

        user = User.query.filter_by(username=username).first()
        if user is not None and user.password == h.hexdigest():
            login_user(user)
            return redirect(url_for('main'))
        else:
            flash('Wrong username or password')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db_password = password + salt
        h = hashlib.md5(db_password.encode())
        if User.query.filter_by(username=username).first() is not None:
            flash('Username already exists')
        else:
            user = User(username=username, password=h.hexdigest())
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('main'))
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)