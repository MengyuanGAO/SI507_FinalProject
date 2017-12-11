import unittest
import os
from SI507F17_finalproject import *



class Test_Yelp_API(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        try:
            os.remove('cache_contents.json')
        except OSError:
            pass

        self.location = 'San Francisco'
        self.restaurants = get_result_restaurants(self.location)
        self.contents_json_file = open('cache_contents.json', 'r', encoding='utf-8')
        self.cache_diction = json.loads(self.contents_json_file.read())
        self.restaurants_list = []
        for restaurant_dict in self.restaurants:
            self.restaurants_list.append(Restaurant(restaurant_dict))
        write_to_csv_res(self.location, self.restaurants_list)
        self.csv_file = open(self.location + '.csv', 'r', encoding='utf-8')


    def test_cache_expire(self):
        cache_diction = self.cache_diction['HTTPS://API.YELP.COM/V3/BUSINESSES/SEARCH?LIMIT_50_LOCATION_SAN FRANCISCO_OFFSET_100']
        cache_timestamp = datetime.strptime(cache_diction["timestamp"], DATETIME_FORMAT)
        hasexpired = has_cache_expired(cache_diction["timestamp"], cache_diction["expire_in_days"])
        delta = datetime.now() - cache_timestamp
        self.assertEqual(delta.days > cache_diction["expire_in_days"], hasexpired)


    def test_cache_success(self):
        self.assertFalse(os.fstat(self.contents_json_file.fileno()).st_size == 0)
        self.assertIsInstance(self.cache_diction, dict)


    def test_get_result_restaurants_success(self):
        for rt in self.restaurants_list:
            self.assertIsInstance(rt,Restaurant)
            self.assertIsInstance(rt.name, str)
            self.assertIsInstance(rt.restaurant_id, str)
            self.assertIsInstance(rt.category, str)
            try:
                self.assertIsInstance(rt.price, str)
            except AssertionError:
                pass
            self.assertIsInstance(rt.rating, float)
            self.assertIsInstance(rt.review_count, int)
            self.assertIsInstance(rt.phone_number, str)
            self.assertIsInstance(rt.address, str)


    def test_get_result_reviews_success(self):
        for rt in self.restaurants_list:
            for review_dict in get_result_reviews(rt.restaurant_id):
                rw = Review(review_dict)
                self.assertIsInstance(rw,Review)
                self.assertIsInstance(rw.user_name, str)
                self.assertIsInstance(rw.rating, int)
                self.assertIsInstance(rw.review, str)
                self.assertIsInstance(rw.time_created, str)


    def test_write_to_csv_success(self):
        self.assertFalse(os.fstat(self.csv_file.fileno()).st_size == 0)



    def test_get_restaurant_diction(self):
        for rt in self.restaurants:
            rt = Restaurant(rt)
            self.assertIsInstance(rt.get_restaurant_diction(), dict)


    def test_get_review_diction(self):
        for rt in self.restaurants:
            rt = Restaurant(rt)
            for review_dict in get_result_reviews(rt.restaurant_id):
                rw = Review(review_dict)
                self.assertIsInstance(rw.get_review_diction(rt.restaurant_id), dict)


    @classmethod
    def tearDownClass(self):
        self.contents_json_file.close()
        self.csv_file.close()



class Test_Yelp_Database(unittest.TestCase):

    def setUp(self):
        db_connection, db_cursor = None, None
        conn, cur = get_connection_and_cursor()
   

    def test_restaurants_db(self):
        cur.execute("""SELECT "Name" FROM "Restaurants" """)
        location = cur.fetchone()["Name"]
        self.assertEqual(location, "Izzy's Hoagie Shop")
        

    def test_review_db(self):
        cur.execute("""SELECT "User_Name" FROM "Reviews" """)
        user_name = cur.fetchone()["User_Name"]
        self.assertEqual(user_name, "Soleil K.")


    def test_table_relation(self):
        cur.execute("""SELECT "ID" FROM "Restaurants" """)
        ID = cur.fetchone()["ID"]
        cur.execute("""SELECT "Resaurant_ID" FROM "Reviews" """)
        Restaurant_ID = cur.fetchone()["Resaurant_ID"]
        self.assertEqual(ID, Restaurant_ID)


    def test_table_count(self):
        cur.execute("""SELECT COUNT(*) FROM "Restaurants" WHERE "Rating" = 3 """)
        number = cur.fetchone()['count']
        self.assertEqual(number,0)


    def tearDown(self):
        pass





if __name__ == "__main__":
    unittest.main(verbosity=2)