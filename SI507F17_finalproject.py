# import modules
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from datetime import datetime
import webbrowser
import json
from secret_data import client_id, client_secret
import csv
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from config import *
import sys



#### Part1: Setup Cache System ####
# referred to oauth1_twitter_caching.py
#constants
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
DEBUG = True
CACHE_FNAME = "cache_contents.json"


#load data cache
try:
    with open(CACHE_FNAME, 'r', encoding='utf-8') as cache_file:
        cache_json = cache_file.read()
        CACHE_DICTION = json.loads(cache_json)
except:
    CACHE_DICTION = {}


#Cache functions
def has_cache_expired(timestamp_str, expire_in_days):
    now = datetime.now()
    cache_timestamp = datetime.strptime(timestamp_str, DATETIME_FORMAT)
    delta = now - cache_timestamp
    delta_in_days = delta.days
    if delta_in_days > expire_in_days:
        return True 
    else:
        return False

def get_from_cache(identifier, dictionary):
    identifier = identifier.upper() 
    if identifier in dictionary:
        data_assoc_dict = dictionary[identifier]
        if has_cache_expired(data_assoc_dict['timestamp'],data_assoc_dict["expire_in_days"]):
            if DEBUG:
                print("Cache has expired for {}".format(identifier))
            del dictionary[identifier]
            data = None
        else:
            data = dictionary[identifier]['values']
    else:
        data = None
    return data


def set_in_data_cache(identifier, data, expire_in_days):
    identifier = identifier.upper()
    CACHE_DICTION[identifier] = {
        'values': data,
        'timestamp': datetime.now().strftime(DATETIME_FORMAT),
        'expire_in_days': expire_in_days
    }

    with open(CACHE_FNAME, 'w') as cache_file:
        cache_json = json.dumps(CACHE_DICTION,indent=4, sort_keys=True)
        cache_file.write(cache_json)




#### Part2： Setup oAuth System ####
# referred to facebook_oauth.py
#constant
CLIENT_ID = client_id 
CLIENT_SECRET = client_secret
TOKEN_URL = 'https://api.yelp.com/oauth2/token'
yelp_session = False


def get_saved_token():
     with open('token.json', 'r') as f:
        token_json = f.read()
        token_dict = json.loads(token_json)
        return token_dict


def save_token(token_dict):
    with open('token.json', 'w') as f:
        token_json = json.dumps(token_dict,indent=4, sort_keys=True)
        f.write(token_json)


def start_yelp_session():
    global yelp_session

    # get token from cache
    try:
        token = get_saved_token()
    except FileNotFoundError:
        token = None

    if token:
        yelp_session = OAuth2Session(CLIENT_ID, token=token)

    # get authorization
    else:
        client = BackendApplicationClient(client_id=CLIENT_ID)
        yelp_session = OAuth2Session(client=client)
        token = yelp_session.fetch_token(token_url=TOKEN_URL, client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET)
        # save token
        save_token(token)


def make_yelp_request(url, params=None):
    global yelp_session

    if not yelp_session:
        start_yelp_session()

    if not params:
        params = {}

    return yelp_session.get(url, params=params)



def create_request_identifier(url, params_diction):
    sorted_params = sorted(params_diction.items(),key=lambda x:x[0])
    params_str = "_".join([str(e) for l in sorted_params for e in l])
    total_ident = url + "?" + params_str
    return total_ident.upper() # create the identifier



def get_data_from_api(request_url, service_ident, params_diction, expire_in_days=7):
    ident = create_request_identifier(request_url, params_diction)
    data = get_from_cache(ident, CACHE_DICTION)
    if data:
        if DEBUG:
            print("Loading from data cache: {}... data".format(ident))
    else:
        if DEBUG:
            print("Fetching new data from {}".format(request_url))
        response = make_yelp_request(request_url, params_diction)
        data = response.json()
        set_in_data_cache(ident, data, expire_in_days)
    return data


### Part3: Extract Data from Yelp API ###
# create restaurant class
class Restaurant():
    def __init__(self, restaurant_dict):
        self.name = restaurant_dict['name']
        self.restaurant_id = restaurant_dict['id']
        for l in restaurant_dict['categories']:
            self.category = l['title']
        try:
            self.price = restaurant_dict['price']
        except KeyError:
            self.price = None
        self.rating = restaurant_dict['rating']
        self.review_count = restaurant_dict['review_count']

        self.phone_number = restaurant_dict['display_phone']
        self.address = restaurant_dict['location']['address1']

    def __repr__(self):
        return 'Restaurant:{}'.format(self.restaurant_id)

    def __contains__(self, term):
        return term in self.name

    def get_restaurant_diction(self):
        diction = {}
        diction['Name'] = self.name
        diction['Category'] = self.category
        diction['Price'] = self.price
        diction['Rating'] = self.rating
        diction['Review_Count'] = self.review_count
        diction['Phone_Number'] =self.phone_number
        diction['Address'] = self.address
        return diction



# creat review class
class Review():
    def __init__(self,review_dict):
        self.user_name = review_dict['user']['name']
        self.rating = review_dict['rating']
        self.review = review_dict['text']
        self.time_created = review_dict['time_created']

    def get_review_diction(self,restaurant_id):
        diction={}
        diction['User_Name'] = self.user_name
        diction['Rating'] = self.rating
        diction['Review'] = self.review
        diction['Time_Created'] = self.time_created
        diction['Resaurant_ID'] = restaurant_id
        return diction


# get data
def get_result_restaurants(location):
    yelp_search_baseurl = 'https://api.yelp.com/v3/businesses/search'
    yelp_search_params = {
        'location':location,
        'limit':50,
        'offset':100
    }
    yelp_result = get_data_from_api(yelp_search_baseurl, 'Yelp', yelp_search_params)
    return yelp_result['businesses']


def get_result_reviews(restaurant_id):
    yelp_search_baseurl = 'https://api.yelp.com/v3/businesses/{}/reviews'.format(restaurant_id)
    yelp_search_params = {'locale':'en_US'}
    yelp_result = get_data_from_api(yelp_search_baseurl, 'Yelp', yelp_search_params)
    return yelp_result['reviews']


# store data into csv files
def write_to_csv_res(location, restaurant_list):
    FIELD_NAMES = ['name', 'category', 'price', 'rating','review_count', 'phone_number', 'address']
    file_name = '{}.csv'.format(location)
    with open(file_name, 'w', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, FIELD_NAMES)
        writer.writeheader()
        for restaurant in restaurant_list:
            writer.writerow({
                'name': restaurant.name,
                'category':restaurant.category,
                'price':restaurant.price,
                'rating':restaurant.rating,
                'review_count':restaurant.review_count,
                'phone_number':restaurant.phone_number,
                'address': restaurant.address,
            })


def write_to_csv_reviews(location, review_list):
    FIELD_NAMES = ['user_name', 'rating', 'review','time_created']
    file_name = '{}_review.csv'.format(location)
    with open(file_name, 'w', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, FIELD_NAMES)
        writer.writeheader()
        for review in review_list:
                writer.writerow({
                    'user_name':review.user_name,
                    'rating': review.rating,
                    'review':review.review,
                    'time_created':review.time_created                
                })


#### Part4: Store Data into Database ####
# Set up database connection and cursor
# referred to twitter_database.py
db_connection, db_cursor = None, None

def get_connection_and_cursor():
    global db_connection, db_cursor
    if not db_connection:
        try:
            if db_password != "":
                db_connection = psycopg2.connect("dbname='{0}' user='{1}' password='{2}'".format(db_name, db_user, db_password))
                print("Success connecting to database")
            else:
                db_connection = psycopg2.connect("dbname='{0}' user='{1}'".format(db_name, db_user))
        except:
            print("Unable to connect to the database. Check server and credentials.")
            sys.exit(1) 

    if not db_cursor:
        db_cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    return db_connection, db_cursor
conn, cur = get_connection_and_cursor()


#create tables 
def setup_database():
    cur.execute('DROP TABLE IF EXISTS "Restaurants" CASCADE')
    cur.execute('DROP TABLE IF EXISTS "Reviews" CASCADE')


    cur.execute(""" CREATE TABLE IF NOT EXISTS "Restaurants"(
        "ID" SERIAL PRIMARY KEY,
        "Name" VARCHAR(40) NOT NULL UNIQUE,
        "Category" VARCHAR(128),
        "Price" VARCHAR(40),
        "Rating" FLOAT(8),
        "Review_Count" INTEGER,
        "Phone_Number" VARCHAR(128),
        "Address" VARCHAR(255)
    )""")

    cur.execute(""" CREATE TABLE IF NOT EXISTS "Reviews"(
        "ID" SERIAL PRIMARY KEY,
        "User_Name" VARCHAR(40),
        "Rating" FLOAT(8), 
        "Review" TEXT,
        "Time_Created" VARCHAR(128),
        "Resaurant_ID" INTEGER REFERENCES "Restaurants"("ID")
    )""")

    conn.commit()
    print('Setup database complete')


#insert data into database
def insert(connection, cursor, table, data_dict, no_return = True):
    column_names = data_dict.keys()
    #print(column_names)

    if not no_return:
        query = sql.SQL('INSERT INTO "{0}"({1}) VALUES({2}) ON CONFLICT DO NOTHING RETURNING "ID"').format(
            sql.SQL(table),
            sql.SQL(', '). join(map(sql.Identifier, column_names)),
            sql.SQL(', ').join(map(sql.Placeholder, column_names))
        )

    else:
        query = sql.SQL('INSERT INTO "{0}"({1}) VALUES({2}) ON CONFLICT DO NOTHING').format(
            sql.SQL(table),
            sql.SQL(', '). join(map(sql.Identifier, column_names)),
            sql.SQL(', ').join(map(sql.Placeholder, column_names))
        )

    sql_string = query.as_string(connection)
    #print(sql_string)
    cursor.execute(sql_string, data_dict)

    if not no_return:
        print (cursor.fetchone()["ID"])



#### Part5: Invoke the functions ####
# invoke the functions
if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        print("You need to fill in client_key and client_secret in the secret_data.py file.")
        exit()
    if not TOKEN_URL:
        print("You need to fill in this API's specific OAuth2 URLs in this file.")
        exit()

# get a list of instances of Restaurant
    restaurants = get_result_restaurants('Ann Arbor') # a list of dictionaries 
    restaurants_list = []
    review_list = []
    for restaurant_dict in restaurants:
        restaurants_list.append(Restaurant(restaurant_dict))

    setup_database()

    for rt in restaurants_list:
        insert(conn, cur, "Restaurants", rt.get_restaurant_diction())
        cur.execute(""" SELECT "ID" FROM "Restaurants" WHERE "Name"=%s""", (rt.name,))
        restaurant_result = cur.fetchone()
        restaurant_db_id = restaurant_result["ID"]

        for review_dict in get_result_reviews(rt.restaurant_id):
            rw = Review(review_dict)
            review_list.append(rw)
            insert(conn, cur, "Reviews", rw.get_review_diction(restaurant_db_id))

    conn.commit()
    print("Insert data into database")

    write_to_csv_res('Ann Arbor',restaurants_list)  
    write_to_csv_reviews('Ann Arbor',review_list)




