from flask import Flask, redirect, url_for, session, jsonify, request
import requests
from flask_oauthlib.client import OAuth
import pymysql
import random
import string

app = Flask(__name__)

def generate_secret_key(length=16):
    characters = string.ascii_letters + string.digits + string.punctuation
    secret_key = ''.join(random.choice(characters) for _ in range(length))
    return secret_key

app.secret_key = generate_secret_key()
print(app.secret_key)

oauth = OAuth(app)

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'Root#04'
DB_NAME = 'customers'

db = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
cursor = db.cursor()

shopify = oauth.remote_app(
    'shopify',
    consumer_key='d221b8a80b22e239997c925d209fc0c0',
    consumer_secret='8f398cd9e7c70bf0edff56d81bf404f1',
    request_token_params={'scope': ('read_products', 'read_orders')},
    base_url='https://testingapp.myshopify.com/admin/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://testingapp.myshopify.com/admin/oauth/access_token',
    authorize_url='https://testingapp.myshopify.com/admin/oauth/authorize',
)

@app.route('/')
def home():
    return 'Hello, Shopify App!'

@app.route('/login')
def login():
    return shopify.authorize(callback=url_for('authorized', _external=True))

@app.route('/logout')
def logout():
    session.pop('shopify_token', None)
    return 'Logged out successfully!'

@app.route('/login/authorized')
def authorized():
    response = shopify.authorized_response()
    print(response)
    if response is None or response.get('access_token') is None:
        return 'Access denied: reason={} error={}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )

    session['shopify_token'] = (response['access_token'], '')
    
    store_access_token(response['access_token'])

    user_info = shopify.get('shop.json')
    shop_name = user_info.data['name']
    
    customer_data = get_shopify_customer_data(shop_name, response['access_token'])
    
    return 'Logged in as id={} name={}. Customer Data: {}'.format(user_info.data['id'], user_info.data['name'], customer_data)

def store_access_token(access_token):
    try:
        query = "INSERT INTO access_tokens (token) VALUES (%s) ON DUPLICATE KEY UPDATE token = %s"
        cursor.execute(query, (access_token, access_token))
        db.commit()
    except Exception as e:
        print("Error storing access token in the database:", e)
        db.rollback()

def get_shopify_customer_data(shop_name, access_token):
    try:
        response = requests.get('https://{}/admin/shop.json'.format(shop_name), headers={'Authorization': 'Bearer ' + access_token})
        customer_data = response.json()
        return customer_data
    except Exception as e:
        return "Error fetching customer data from Shopify: {}".format(e)

@shopify.tokengetter
def get_shopify_oauth_token():
    query = "SELECT token FROM access_tokens ORDER BY id DESC LIMIT 1"
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return result[0]

if __name__ == '__main__':
    print("Server is running!")
    app.run(debug=True)
