from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import timedelta, timezone, datetime
import os
import pyotp
import qrcode
import hashlib
import json
import random

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = basedir+'\public\image'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg'}

app = Flask(
    __name__,
    static_folder='public',
    static_url_path='/'
)  # 建立 application 物件


app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=60)
app.config['SECRET_KEY'] = os.urandom(24)







connection_string='mongodb+srv://samsonm825:g4zo1j6y94@cluster0.ow4o5g4.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(connection_string)
dbs = client.BT

key = 'iLufaMySuperSecretKey'
#将资料转换成json存入资料库
# jsonFile = open('example.json','r',encoding='UTF-8')
# jsonF = json.load(jsonFile)
# i = 1
# for doc in jsonF:
#     data = {
#         'name':doc['姓名'],
#         'phone':'0' + str(doc['电话']),
#         'address':doc['地址'].replace('\t', ''),
#         'number':i
#     }
#     i =  i + 1 
#     dbs.fake_data.insert_one(data)






def verify_potp(potp):
    totp = pyotp.TOTP(key)
    result = totp.verify(potp)
    return result

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def random_number(count):
    number_list = []
    for i in range(999):
        number_list.append(i)
    random.shuffle(number_list)
    return number_list[0:count]
    



@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        admin_data=[]
        account = request.form['account']
        password = request.form['password']
        potp = request.form['potp']

        pottp_resul = verify_potp(potp)

        admin_find = dbs.admin.find({
            'account': account
        })
        for doc in admin_find:
             admin_data.append(doc)
        if len(admin_data) <= 0:
            return redirect('index')
        password_str = password + admin_data[0]['salt']
        user_password = hashlib.sha1(password_str.encode('utf-8'))


        if admin_data[0]['password'] == user_password.hexdigest():
            session.permanent = True
            session['display_name'] = admin_data[0]['display_name']
            session['id'] = str(admin_data[0]['_id'])
            return redirect('admin_fakeData')
        else:
            return redirect('index')            
    else:
        if 'display_name' in session:
            return redirect ('admin_fakeData')
        return render_template('index.html')

@app.route('/admin_log',methods=['GET', 'POST'])
def admin_log():
    if 'display_name' in session and session['display_name'] == '最高管理者':
        record_data = []
        record_find = dbs.log_record.find({})
        for doc in record_find:
            record_data.append(doc)
        return render_template('admin_log.html', record_data=record_data)
    else:
        return redirect('admin_login')


@app.route('/resetPassword',methods=['GET','POST'])
def resetPassword():
    if 'id' in session:
        if request.method == 'POST':
            old_password = request.form['oldPassword']
            password = request.form['password']
            repeat_password = request.form['repeatPassword']
            member_data = dbs.member.find_one({'_id':ObjectId(session['id']) })
            old_password_str = old_password + member_data['salt']
            old_password = hashlib.sha1(old_password_str.encode('utf-8'))

            if member_data['password'] == old_password.hexdigest() and password ==repeat_password:
                password_str = password + member_data['salt']
                user_password = hashlib.sha1(password_str.encode('utf-8'))
                dbs.member.update_one(
                    {
                     '_id':ObjectId(session['id'])
                    },
                    {
                     '$set':{
                        'password': user_password.hexdigest()
                     }
                    }
                )
                session.clear()
                return redirect('login')
            
            else:
                return redirect('resetPassword')
        else:
            
            return render_template('resetPassword.html')
    else:
        return redirect('login')

@app.route('/cart/<product>')
def cart(product):
    if 'id' in session:
        member_data = dbs.member.find_one({'_id':ObjectId(session['id'])})

        if product == 'all':
            product_data = []
            product_find = dbs.product.find(
                {
                    'is_buy':False,
                    'price':{
                        '$lte':member_data['coin']
                    }
                }
            )
            for doc in product_find:
                product_data.append(doc)

            return render_template('cart.html',product_data = product_data)
        else:
            product_data = dbs.product.find_one({'_id':ObjectId(product)})
            if request.args.get('methods') == 'buy':
                if request.args.get('mid')!= session['id']:
                    session.clear()
                    return redirect(url_for('login'))
                dbs.member.update_one(
                {
                    '_id':ObjectId(request.args.get('mid'))
                },             
                
                {
                    '$set':{ 
                        'coin':member_data['coin']-product_data['price']
                    }

                })
                dbs.product.update_one(
                {
                    '_id':ObjectId(product)
                },             
                
                {
                    '$set':{ 
                        'is_buy':True
                    }

                })
                dbs.order.insert_one(
                    {
                        'product_id':ObjectId(product),
                        'mid':ObjectId(request.args.get('mid')), 
                        'is_paid':False,   
                        'prove_img':'',
                        'status':False
                    }
                )

                return redirect(url_for('cart',product = 'all'))
            else:
                return render_template('cart_order.html',product_data=product_data,member_data=member_data)

    else:
        return redirect(url_for('login'))

@app.route('/admin_user', methods=['GET', 'POST'] )
def admin_user():
    if 'display_name' in session and session['display_name'] == '最高管理者':
        if request.method == 'POST':
            name = request.form['name']
            account = request.form['account']
            id = request.form['id']
            password = request.form['password']
            display_name = request.form['display_name']

            if id == '':
                user_data = dbs.admin.find_one({'account':account})
                if user_data != None:
                    return redirect('admin_user')
                salt = 'KKJNWSDJIJDJIWWIDJ'
                password_str = password + salt
                user_password = hashlib.sha1(password_str.encode('utf-8'))
                dbs.admin.insert_one({
                    'name': name,
                    'account':account,
                    'password':user_password.hexdigest(),
                    'salt':salt,
                    'display_name':display_name
                })
                return redirect('admin_user')
            else:
                user_data = dbs.admin.find_one({'_id':ObjectId(id)})
                if user_data['password'] != password:
                    password_str = password + user_data['salt']
                    user_password = hashlib.sha1(password_str.encode('utf-8'))
                    password = user_password.hexdigest()
                dbs.admin.update_one(
                    {
                      '_id':ObjectId(id)
                    },
                    {
                      '$set':{
                      'name': name,
                      'password':password,
                      'display_name':display_name

                      }
                    })
                return redirect('admin_user')
        else:
            if request.args.get('methods') == 'delete':
                dbs.admin.delete_one({"_id":ObjectId(request.args.get('id'))})
            user_data = []
            user_find = dbs.admin.find()
            for doc in user_find:
                doc['_id'] = str(doc['_id'])
                user_data.append(doc)
            return render_template('admin_user.html', user_data=user_data) 
    else:
        return redirect('admin_dashboard')

@app.route('/admin_order')
def admin_order():
    if 'display_name' and session['display_name'] == '最高管理者':
        if request.args.get('methods') == 'post':
            order_data = dbs.order.find_one(
                {
                  '_id':ObjectId(request.args.get('oid'))
                }
            )
            if order_data == None:
                session.clear()
                return redirect('admin_login')
            product_data = dbs.product.find_one({ '_id':ObjectId(order_data['product_id'])})
            member_data = dbs.member.find_one({ '_id':ObjectId(order_data['mid'])})

            dbs.member.update_one(
                {
                 '_id':ObjectId(member_data['_id'])
                },
                {
                 '$set':{
                    'real_coin':member_data['real_coin'] + int(product_data['price'])
                 }
                }
            )
            dbs.order.update_one(
                {
                  '_id':ObjectId(request.args.get('oid'))
                },
                {
                  '$set':{
                     'is_paid':True
                  }
                }
            )
           
            record_data = {
                'm_name':member_data['name'],
                'oId': str(order_data['_id']),
                'in_coin':  product_data['price'],
                'out_coin': 0,
                'in_bonus': 0,
                'out_bonus': 0
            }

            dbs.log_record.insert_one(record_data)

        elif request.args.get('methods') == 'delete':
            order_data = dbs.order.find_one(
                {
                  '_id':ObjectId(request.args.get('oid'))
                }
            )
            if order_data == None:
                session.clear()
                return redirect('admin_login')
            dbs.order.delete_one(
                {
                  '_id':ObjectId(request.args.get('oid'))
                }
            )

        order_data = []
        order_find = dbs.order.aggregate([
            {
                '$lookup':{
                    'from':'product',
                    'localField':'product_id',
                    'foreignField':'_id',
                    'as':'product'
                    }
            },
             {
                '$lookup':{
                    'from':'member',
                    'localField':'mid',
                    'foreignField':'_id',
                    'as':'member'
                    }
            },

        ])
        for doc in order_find:
            order_data.append(doc)

        return render_template('admin_order.html',order_data=order_data)
    else:
        return redirect('admin_login')


@app.route('/admin_verify', methods=['GET','PSOT'])
def admin_verify():
    if 'display_name' and session['display_name'] == '最高管理者':
        if request.args.get('id'):
            if request.args.get('is_verify') == '1':
                dbs.member.update_one(
                    {
                        '_id':ObjectId( request.args.get('id'))
                    },
                    {
                        '$set':{
                            'is_verify':1
                        }
                    }
                )
            else:
                dbs.member.update_one(
                    {
                        '_id':ObjectId( request.args.get('id'))
                    },
                    {
                        '$set':{
                            'is_verify':2
                        }
                    }
                )

            
            
            return redirect('admin_verify')

        member_data = []
        member_find = dbs.member.find({
        'is_verify':0
        })


        for doc in member_find:
            member_data.append(doc)

        return render_template('admin_verify.html', member_data = member_data)

    else:
        return redirect('admin_login')
@app.route('/admin_member',methods=['POST','GET'])
def admin_member():
    if 'display_name' and session['display_name'] == '最高管理者':
        if request.method == 'POST':
            real_coin = request.form['real_coin']
            bonus = request.form['bonus']
            bonus_rate = request.form['bonus_rate']
            name = request.form['name']
            coin = int(request.form['coin'])
            id = request.form['id']
            bankAccount = request.form['bankAccount']

            dbs.member.update_one(
                {
                    '_id':ObjectId(id)
                },
                {
                    '$set':{
                        'name':name,
                        'coin':coin,
                        'bankAccount':bankAccount,
                        'real_coin':int(real_coin),
                        'bonus':float(bonus),
                        'bonus_rate':float(bonus_rate)
                    }
                }
            )
            return redirect('admin_member')


        else:
            if request.args.get('methods') =='delete':
                dbs.member.delete_one(
                    {
                        '_id':ObjectId(request.args.get('id'))
                    }
                )
            
            member_data = []
            member_find = dbs.member.find(
                {
                    'is_verify':1
                },
                {
                    'password':0,
                    'status':0
                }
            )
            for doc in member_find:
                doc['_id'] = str(doc['_id'])
                member_data.append(doc)
            
            return render_template("admin_member.html" ,member_data=member_data)
    else:
        return redirect('admin_login')
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'display_name' in session:
        return render_template('admin_dashboard.html')
    else:
        return redirect('admin_login')

@app.route('/order_list')
def order_list():
    if 'id' in session:
        return render_template('order_custom.html')
    else:
        return redirect('login')


@app.route('/order')
def order():
    if 'id' in session:
        if request.args.get('method') == 'success':
            oId = request.args.get('oId')
            pId = request.args.get('pId')
            product_data = dbs.product.find_one({
                 '_id': ObjectId(pId),
            })
            order_data = dbs.order.find_one({
                 '_id': ObjectId(oId),
            })
            if order_data == None or product_data == None:
                return redirect('order')
            member_data = dbs.member.find_one({
                 '_id': ObjectId(session['id']),
            })
           
            record_data = {
                'm_name':member_data['name'],
                'oId': oId,
                'in_coin': 0,
                'out_coin': product_data['price'],
                'in_bonus':float(product_data['price'])*0.002,
                'out_bonus': 0
            }
            dbs.member.update_one(
                {
                    '_id':ObjectId(session['id']),
                },
                {
                    '$set':{
                        'bonus':member_data['bonus'] + float(product_data['price'])*0.002,
                        'real_coin':member_data['real_coin'] - product_data['price'],
                        'coin':member_data['coin'] + product_data['price']
                    }
                }
            )
            dbs.log_record.insert_one(record_data)
            dbs.order.update_one(
                {
                    '_id': ObjectId(oId)
                },
                {
                    '$set':{
                        'status':True
                    }
                }
            )
            return redirect('order')

        order_data = []
        order_find = dbs.order.aggregate([
            {
                '$match':{
                    'mid':ObjectId(session['id'])
                }
            },
            {
                '$lookup':{
                    'from':'product',
                    'localField':'product_id',
                    'foreignField':'_id',
                    'as':'product'
                    }
            }
        ])

        for doc in order_find:
            order_data.append(doc)
        return render_template('order.html',order_data=order_data)
    else:
        return redirect('login')



@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        admin_data=[]
        account = request.form['account']
        password = request.form['password']
        potp = request.form['potp']

        pottp_resul = verify_potp(potp)

        admin_find = dbs.admin.find({
            'account': account
        })
        for doc in admin_find:
             admin_data.append(doc)
        if len(admin_data) <= 0:
            return redirect('admin_login')
        password_str = password + admin_data[0]['salt']
        user_password = hashlib.sha1(password_str.encode('utf-8'))


        if admin_data[0]['password'] == user_password.hexdigest():
            session.permanent = True
            session['display_name'] = admin_data[0]['display_name']
            session['id'] = str(admin_data[0]['_id'])
            return redirect('admin_fakeData')
        else:
            return redirect('admin_login')            
    else:
        if 'display_name' in session:
            return redirect ('admin_fakeData')
        return render_template('admin_login.html')

@app.route('/admin_logout')
def admin_logout():
  session.clear()
  return redirect('/')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        member_data = []
        account = request.form["account"]
        password = request.form["password"]

        member_find = dbs.member.find({
            'account':account
        })

        for doc in member_find:
            member_data.append(doc)
        
        if len(member_data) <= 0:
            return redirect('login')
        
        password_str = password + member_data[0]['salt']
        user_password = hashlib.sha1(password_str.encode('utf-8'))



        if member_data[0]['password'] == user_password.hexdigest() and member_data[0]['is_verify'] == 1 :
            session.permanent = True
            session['name'] = member_data[0]['name']
            session['id'] = str(member_data[0]['_id'])
            
            return redirect('profile')
        else:
            return redirect('login')

    else:
        if 'id' in session:
          return  redirect('profile')
        return render_template('login.html')

@app.route('/admin_product',methods=['GET','POST'])
def admin_product():
    if 'display_name' in session:
        if request.method=='POST':
            potp = request.form['potp']
            potp_result = verify_potp(potp)
            potp_result = True
            if potp_result == True:
                name = request.form['name']
                price = int(request.form['price'])
                desc = request.form['desc']
                factory_name = request.form['factory_name']
                factory_bank = request.form['factory_bank']

                if request.form['id'] == '':
                    dbs.product.insert_one(
                        {
                            'name':name,
                            'price':price,
                            'desc':desc,
                            'factory_name':factory_name,
                            'factory_bank':factory_bank,
                            'is_buy':False
                        }
                    )
                else:
                     dbs.product.update_one(
                        {
                            '_id': ObjectId(request.form['id'])
                        },
                        {
                            '$set':{
                                'name':name,
                                'price':price,
                                'desc':desc,
                                'factory_name':factory_name,
                                'factory_bank':factory_bank
                            }
                        }
                    )

                return redirect('admin_product')
            else:
                return redirect('admin_product')
        else:
            if request.args.get('methods') == 'delete':
                dbs.product.delete_one(
                    {
                         '_id':ObjectId( request.args.get('id'))
                    }
                )
            product_data = []
            product_find = dbs.product.find()
            for doc in product_find:
                doc['_id'] = str(doc['_id'])
                if doc['is_buy'] == True:
                    doc['is_buy'] = 1
                else:
                    doc['is_buy'] = 0
                product_data.append(doc) 
            return render_template('admin_product.html',product_data = product_data)
    else:
        return redirect('admin_login')

@app.route('/admin_fakeData')
def admin_fakeData():
    if 'display_name' in session and session['display_name'] == '最高管理者':
        return render_template('admin_fakeData.html')
    else:
        return redirect('admin_login')





@app.route('/order_prove',methods=['POST'])
def order_prove():
    if'id' in session:
        oId = request.form['oId']
        f = request.files['prove_img']
        mid = session['id']
        member_data = dbs.member.find_one({ '_id':ObjectId(mid) })
        account = member_data['account']
        imgUrl = ''

        if f and allowed_file(f.filename):
            file_path = basedir + '\public\image' + f'\{account}'
            if not os.path.isdir(file_path):
                os.mkdir(file_path)
            f.save(os.path.join(file_path, f.filename))
            imgUrl = f'/image/{account}/{f.filename}'

        dbs.order.update_one(
            {
                '_id':ObjectId(oId)
            },
            {
                '$set':{
                    'prove_img': imgUrl
                }
            }
        )
 

        return redirect('order')
    else:
        return redirect('login')

@app.route('/profile', methods=['GET','POST'])
def profile():
    if 'id' in session:
        if request.args.get('method') == 'controlStatus':
            if request.arg.get('status') == "1":
                status = True
            else:
                status=False    
            dbs.memeber.update_one(
                {
                    '_id':ObjectId(session['id'])
                },
                {
                    '$set':{
                        'status':status
                    }
                }

            )       



        member_data = dbs.member.find_one(
            {
             '_id': ObjectId(session['id'])
            },
            {
                'password':0
            }
        )

                
            
           

    else :
        return redirect('login')
    return render_template('profile.html',member_data=member_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('login')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        account = request.form['account']
        password = request.form['password']
        name = request.form['name']
        resetPassword = request.form['resetPassword']
        IDcard = request.form['IDcard']
        bankName = request.form['bankName']
        bankAccount = request.form['bankAccount']

        account_repeat = dbs.member.find_one({'account':account})
        if account_repeat != None:
            return redirect('register')

        print(account, password,   name, resetPassword, IDcard, bankName, bankAccount)

        file_arr = []
        img_arr = []
        imgUrl = ''
        file_arr.append(request.files['IDcardImage'])
        file_arr.append(request.files['bankImage'])
        file_arr.append(request.files['creditImage'])

        for f in file_arr:
            print('step2')
            if f and allowed_file(f.filename):
                file_path = basedir + '\public\image' + f'\{account}'
                print(file_path)
                if not os.path.isdir(file_path):
                    os.mkdir(file_path)
                f.save(os.path.join(file_path, f.filename))
                imgUrl = f'/image/{account}/{f.filename}'
                img_arr.append(imgUrl)
            else:
                print('step3')
                return redirect('register')
        
        salt = '645464'
        password_str = password + salt
        user_password = hashlib.sha1(password_str.encode('utf-8'))

        dbs.member.insert_one({
            'account': account,
            'password': user_password.hexdigest(),
            'name':  name,
            'IDcard': IDcard,
            'bankName': bankName,
            'bankAccount': bankAccount,
            'coin':0,
            'img_arr': img_arr,
            'real_coin':0,
            'bonus':0.0,
            'bonus_rate':0.002,
            'status':False,
            'is_verify': 0,
            'salt':salt
        })


        return '注册成功'
    else:
        return render_template('register.html')

@app.route('/api/<name>',methods=['GET', 'POST'])
def api(name):
    if name == 'fake_data' and request.method == 'GET':
        count = int(request.args.get('count'))
        fake_data = []
        number_list = random_number(count)

        for number in number_list:
            fake_find = dbs.fake_data.find_one({'number': number },{'_id': 0})
            fake_data.append(fake_find)
        return jsonify(fake_data)    
    else:
        return redirect(url_for('login'))  
    
    
    
if __name__ == "__main__":
    app.run(debug=True)

