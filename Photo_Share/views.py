# -*-encoding=utf-8-*-

from Photo_Share import app, db, login_manager
from Photo_Share.models import Image, User, Comment
from flask import render_template, redirect, request, flash, get_flashed_messages, send_from_directory
import random, hashlib, json
from flask_login import login_user, logout_user, current_user, login_required
import uuid, os
from Photo_Share.qiniusdk import qiniu_upload_file


@app.route('/')
def index():
    # images=Image.query.order_by('id desc').limit(10).all()
    images = Image.query.order_by(db.desc(Image.id)).limit(10).all()
    return render_template('index.html', images=images)


@app.route('/image/<int:image_id>/')
def image(image_id):
    image = Image.query.get(image_id)
    if image == None:
        return redirect('/')
    return render_template('pageDetail.html', image=image)


@app.route('/profile/<int:user_id>/')
@login_required  # 只有登陆才能访问
def proflie(user_id):
    user = User.query.get(user_id)
    if user == None:
        return redirect('/')
    paginate = Image.query.filter_by(user_id=user_id).paginate(page=1, per_page=3, error_out=False)
    return render_template('profile.html', user=user, images=paginate.items, has_next=paginate.has_next)


@app.route('/profile/images/<int:user_id>/<int:page>/<int:per_page>/')
def user_images(user_id, page, per_page):
    paginate = Image.query.filter_by(user_id=user_id).paginate(page=page, per_page=per_page, error_out=False)
    map = {'has_next': paginate.has_next}
    images = []
    for image in paginate.items:
        imgvo = {'id': image.id, 'url': image.url, 'comment_count': len(image.comments)}
        images.append(imgvo)
    map['images'] = images
    return json.dumps(map)


@app.route('/regloginpage/')
def regloginpage():
    msg = ''
    for m in get_flashed_messages(with_categories=False, category_filter=['reglogin']):
        msg = msg + m
    return render_template('login.html', msg=msg, next=request.values.get('next'))


def redirect_with_msg(target, msg, category):
    if msg != None:
        flash(msg, category=category)
    return redirect(target)


@app.route('/login/', methods={'get', 'post'})
def login():
    username = request.values.get('username').strip()
    password = request.values.get('password').strip()
    if username == '' or password == '':
        return redirect_with_msg('/regloginpage', u'用户名或密码不能为空！', 'reglogin')
    user = User.query.filter_by(username=username).first()
    if user == None:
        return redirect_with_msg('/regloginpage', u'用户名不存在！', 'reglogin')

    m = hashlib.md5()
    m.update(password + user.salt)
    if (m.hexdigest() != user.password):
        return redirect_with_msg('/regloginpage', u'密码错误！', 'reglogin')

    login_user(user)

    # next 登陆完了之后直接跳到next指定的页面（user100?为啥）
    next = request.values.get('next')
    if next != None and next.startswith('/'):
        return redirect(next)

    return redirect('/')


@app.route('/reg/', methods={'post', 'get'})
def reg():
    # request.args url中的参数
    # request.form 表单中的
    username = request.values.get('username').strip()
    password = request.values.get('password').strip()

    if username == '' or password == '':
        return redirect_with_msg('/regloginpage', u'用户名或密码不能为空！', 'reglogin')

    user = User.query.filter_by(username=username).first()
    if user != None:  # 用户名已存在
        return redirect_with_msg('/regloginpage', u'用户名已存在！', 'reglogin')

    # 更多判断...


    salt = '.'.join(random.sample('0123456789abcdefghiABCDEFGHI', 10))
    m = hashlib.md5()
    m.update(password + salt)
    password = m.hexdigest()

    user = User(username, password, salt)
    db.session.add(user)
    db.session.commit()

    # 注册后自动登陆
    login_user(user)
    # 注册完了之后直接跳到user100？还需要修改吧
    next = request.values.get('next')
    if next != None and next.startswith('/'):
        return redirect(next)

    return redirect('/')


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')


#
# def save_to_local(file, file_name):
#     save_dir = app.config['UPLOAD_DIR']
#     file.save(os.path.join(save_dir, file_name))
#     return '/image/' + file_name

def save_to_local(file, file_name):
    save_dir = app.config['UPLOAD_DIR']
    file.save(os.path.join(save_dir, file_name))
    return '/image/' + file_name


# @app.route('/upload/', methods={'post'})
# def upload():
#     # print type(request.files)
#     file = request.files['file']
#     # dir(file)
#     # return 'ok'
#     file_ext = ''
#     # 后缀名匹配
#     # file.filename
#     # asdf.jpg
#     if file.filename.find('.') > 0:
#         file_ext = file.filename.rsplit('.', 1)[1].sprip().lower()
#     if file_ext in app.config['ALLOWED_EXT']:  # 后缀名符合标准
#         file_name = str(uuid.uuid1()).replace('-', '') + '.' + file_ext
#         url = save_to_local(file, file_name)
#         if url != None:
#             db.session.add(Image(url, current_user.id))
#             db.session.commit()
#
#     return redirect('/proflie/%d' % current_user.id)

@app.route('/image/<image_name>')
def view_image(image_name):
    # 下载显示
    return send_from_directory(app.config['UPLOAD_DIR'], image_name)


@app.route('/upload/', methods={"post"})
# @login_required
def upload():
    file = request.files['file']
    # http://werkzeug.pocoo.org/docs/0.10/datastructures/
    # 需要对文件进行裁剪等操作
    file_ext = ''
    if file.filename.find('.') > 0:
        file_ext = file.filename.rsplit('.', 1)[1].strip().lower()
    if file_ext in app.config['ALLOWED_EXT']:
        file_name = str(uuid.uuid1()).replace('-', '') + '.' + file_ext
        url = qiniu_upload_file(file, file_name)
        # url = save_to_local(file, file_name)
        if url != None:
            db.session.add(Image(url, current_user.id))
            db.session.commit()

    return redirect('/profile/%d' % current_user.id)


@app.route('/addcomment/', methods={'post'})
@login_required
def add_comment():
    image_id = int(request.values['image_id'])
    content = request.values['content']
    comment = Comment(content, image_id, current_user.id)
    db.session.add(comment)
    db.session.commit()
    return json.dumps({"code": 0, "id": comment.id,
                       "content": comment.content,
                       "username": comment.user.username,
                       "user_id": comment.user_id})


@app.route('/index/images/<int:page>/<int:per_page>/')
def index_images(page, per_page):
    paginate = Image.query.order_by(db.desc(Image.id)).paginate(page=page, per_page=per_page, error_out=False)
    map = {'has_next': paginate.has_next}
    images = []
    for image in paginate.items:
        comments = []
        for i in range(0, min(2, len(image.comments))):
            comment = image.comments[i]
            comments.append({'username': comment.user.username,
                             'user_id': comment.user_id,
                             'content': comment.content})
        imgvo = {'id': image.id,
                 'url': image.url,
                 'comment_count': len(image.comments),
                 'user_id': image.user_id,
                 'head_url': image.user.head_url,
                 'created_date': str(image.created_date),
                 'comments': comments}
        images.append(imgvo)

    map['images'] = images
    return json.dumps(map)
