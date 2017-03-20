# -*-encoding=utf-8-*-

from Photo_Share import db, login_manager
import random
from datetime import datetime


# ORM
# 用户类
class User(db.Model):  # db.Model表示该类与数据库表相关联
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True)  # username就是一列，与数据库相关联
    password = db.Column(db.String(32))
    salt = db.Column(db.String(32))  # 盐加密
    head_url = db.Column(db.String(256))
    images = db.relationship('Image', backref='user', lazy='dynamic')

    # 构造函数
    def __init__(self, username, password, salt=''):
        self.username = username
        self.password = password
        self.salt = salt
        # 从网站头像库随机提取一张照片
        self.head_url = 'http://images.nowcoder.com/head/' + str(random.randint(0, 1000)) + 'm.png'

    # 打印
    def __repr__(self):
        return '<User %d %s>' % (self.id, self.username)
        # 用户登记

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


# 图片类
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url = db.Column(db.String(512))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 与user表相关联
    created_date = db.Column(db.DateTime)
    comments = db.relationship('Comment')

    def __init__(self, url, user_id):
        self.url = url
        self.user_id = user_id
        self.created_date = datetime.now()

    # 打印
    def __repr__(self):
        return '<Image %d %s>' % (self.id, self.url)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.String(1024))
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 与user表相关联
    status = db.Column(db.Integer, default=0)  # 0 正常 1 被删除
    user = db.relationship('User')

    def __init__(self, content, image_id, user_id):
        self.content = content
        self.image_id = image_id
        self.user_id = user_id

    # 打印
    def __repr__(self):
        return '<Comment %d %s>' % (self.id, self.content)




# 用户加载
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
