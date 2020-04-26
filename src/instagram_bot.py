import os
import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from src.database import Database


class InstagramBot:
    """
    Recursively walk over all users that tagged
    with a username begging with given start_username
    until it passes user_quantity.
    Then write to the database all users it visited
    and who tagged whom.
    """
    url = 'https://www.instagram.com/'
    user_quantity = 1

    def __init__(self, username, password, start_username, db: Database):
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

    def scroll(self):
        """
        Scroll page up to the end (last photo)
        """
        old_page_height = self.driver.execute_script('return document.documentElement.scrollTop')
        step = 600
        scroll_to = step
        while True:
            self.driver.execute_script('document.documentElement.scrollTo(0, %s);' % scroll_to)
            time.sleep(1)
            scroll_to += step
            new_page_height = self.driver.execute_script('return document.documentElement.scrollTop')
            if new_page_height == old_page_height:
                break
            old_page_height = new_page_height

    @staticmethod
    def contains_photos(photo_grid):
        """
        Check if profile contains photos in 'tagged' section
        """
        try:
            photo_grid.find_elements_by_tag_name('article')
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

    def get_list_usernames(self, photo_grid):
        """
        Return a set of usernames who tagged photos in given photo grid (box)
        """
        usernames = set()
        photo_divs = photo_grid.find_elements_by_css_selector('div.v1Nh3.kIKUG._bz0w')
        photo_urls = [photo_div.find_element_by_tag_name('a').get_attribute('href') for photo_div in photo_divs]
        for photo_url in photo_urls:
            self.driver.get(self.get_photo_url(photo_url))
            username = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.sqdOP.yWX7d._8A5w5.ZIAjV'))
            ).text
            usernames.add(username)
        return usernames

    def run(self):
        """
        Launch program
        """
        self.login()
        current_username = self.start_username
        while self.db.passed_users_count != self.user_quantity:
            self.driver.get(self.get_tagged_url(current_username))
            # wait 10 sec until grid with photos appears
            photo_grid = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div._2z6nI'))
                )
            # if profile doesn't contain any tagged photo then continue
            if not self.contains_photos(photo_grid):
                continue
            self.scroll()
            # get grid with all loaded photos
            photo_grid = self.driver.find_element_by_css_selector('div._2z6nI')
            usernames = self.get_list_usernames(photo_grid)
            self.db.add_tagging_users(usernames)
            current_username = self.db.get_next_user()
        self.quit()

    def quit(self):
        """
        Close all connections
        """
        self.driver.quit()
        self.db.close()
