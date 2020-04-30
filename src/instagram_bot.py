import os
import re
import time
import urllib.parse
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class InstagramBot:
    """
    Recursively walk over all users that tagged
    with a username begging with given start_username
    until it passes user_quantity.
    Then write to the database all users it visited
    and who tagged whom.
    """
    url = 'https://www.instagram.com/'
    user_visiting_amount = 150

    def __init__(self, username, password, start_username, db):
        self.username = username
        self.password = password
        self.start_username = start_username
        self.db = db
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])
        self.driver = webdriver.Chrome(os.path.abspath('../chromedriver'), options=chrome_options)

    def get_user_url(self, username):
        """
        Return absolute url of given username in instagram
        """
        return urllib.parse.urljoin(self.url, username) + '/'

    def get_tagged_url(self, username):
        """
        Return absolute url of given username's '
        tagged' section  in instagram
        """
        return urllib.parse.urljoin(self.get_user_url(username), 'tagged')

    def get_photo_url(self, photo_url):
        """
        Return absolute url of given photo_url in instagram
        """
        return urllib.parse.urljoin(self.url, photo_url)

    def login(self):
        """
        Login in instagram with given usernamme and password.
        Close pop-up box of notification after loggining
        """
        self.driver.get(self.url)
        time.sleep(2)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'username'))
        ).send_keys(self.username)
        self.driver.find_element_by_name('password').send_keys(self.password)
        self.driver.find_element_by_xpath("//button[@type='submit']").click()
        time.sleep(3)
        self.close_notification_box()

    def close_notification_box(self):
        """
        Close pop-up box of notification if it appears
        """
        try:
            not_now = self.driver.find_element_by_css_selector(
                'body > div.RnEpo.Yx5HN > div > div > div.mt3GC > button.aOOlW.HoLwm')
            not_now.click()
        except Exception as ex:
            return

    @staticmethod
    def contains_photos(photo_grid):
        """
        Check if profile contains photos in 'tagged' section
        """
        try:
            photo_grid.find_element_by_tag_name('article')
            return True
        except Exception as ex:
            return False

    # private photos aren't showed in tagged section
    @staticmethod
    def is_public(photo_grid):
        """
        Check if profile is public
        """
        try:
            photo_grid.find_element_by_css_selector('div._4Kbb_')
            return False
        except Exception as ex:
            return True

    def run(self):
        """
        Launch program
        """
        self.login()
        current_username = self.start_username
        # until the current user doesn't exist and
        # unless the necessary quantity of users passes
        while self.db.passed_users_count != self.user_visiting_amount and current_username:
            self.driver.get(self.get_tagged_url(current_username))
            # wait 10 sec until grid with photos appears
            photo_grid = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div._2z6nI'))
            )
            # if profile doesn't contain any tagged photo or it's private then continue
            if not self.contains_photos(photo_grid) or not self.is_public(photo_grid):
                current_username = self.db.get_next_user()
                continue
            usernames = self.get_list_usernames()
            self.db.add_tagging_users(usernames)
            current_username = self.db.get_next_user()
            time.sleep(1)
        self.quit()

    def get_list_usernames(self):
        """
        Return a set of usernames who tagged a user in the current page
        """
        usernames = set()
        # 'tokens' that are necessary for getting info
        query_hash = self.get_query_hash(self.driver.find_elements_by_xpath("//head/script[@type='text/javascript']"))
        user_id = self.get_user_id(self.driver.find_elements_by_xpath("//body/script[@type='text/javascript']"))
        # print('query_hash: %s, user_id: %s' % (query_hash, user_id))
        url_pattern = ('https://www.instagram.com/graphql/query/?query_hash={0}&variables=%7B%22id%22%3A%22{'
                       '1}%22%2C%22first%22%3A12%').format(query_hash, user_id)
        first_query_url = url_pattern + '7D'
        others_queries_url_pattern = url_pattern + '2C%22after%22%3A%22{0}%3D%3D%22%7D'
        query_url = first_query_url
        # an error occurs in the response for large amount of photos
        try:
            while True:
                response = requests.get(query_url).json()
                print('new request for tagged data')
                edge = response['data']['user']['edge_user_to_photos_of_you']
                page_info = edge['page_info']
                has_next_page = page_info['has_next_page']
                after = page_info['end_cursor']
                usernames = usernames.union(self.retrieve_usernames_from_json(edge['edges']))
                if not has_next_page:
                    break
                query_url = others_queries_url_pattern.format(after[:-2])
                time.sleep(1)
        except Exception as ex:
            pass
        return usernames

    def retrieve_usernames_from_json(self, edges):
        """
        Get all usernames contained in response
        :param edges: key of json where information
        about photos is located
        """
        usernames = set()
        for e in edges:
            usernames.add(e['node']['owner']['username'])
        return usernames

    def get_query_hash(self, scripts):
        """
        Get query hash
        :param scripts: scripts located in <head>
        """
        # try to find necessary src straight off with beautiful soup
        script = [sp for sp in scripts if 'ProfilePageContainer' in sp.get_attribute('src')][0]
        script_url = urllib.parse.urljoin(self.url, script.get_attribute('src'))
        headers = {'user-agent': self.driver.execute_script('return navigator.userAgent;')}
        response = requests.get(script_url, headers=headers).text
        for i, res in enumerate(re.finditer('queryId:"\w*"', response)):
            if i == 1:
                match = res.group()
                query_hash = re.search('"(\w*)"', match).group()[1:-1]
                return query_hash
        raise Exception("Query hash wasn't found")

    def get_user_id(self, scripts):
        """
        Get user id
        :param scripts: scripts located in <body>
        """
        try:
            match = ''
            for sp in scripts:
                text = sp.get_attribute('innerHTML')
                if 'window._sharedData' in text:
                    match = text
                    break
            match = re.search('"owner":{"id":"\d*"', match).group()
            return re.search('"(\d*)"', match).group()[1:-1]
        except Exception as ex:
            raise Exception("User id wasn't found")

    def quit(self):
        """
        Close all connections
        """
        self.driver.quit()
        self.db.close()
