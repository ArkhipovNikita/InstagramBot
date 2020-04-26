import psycopg2
from src.database import Database
from src.instagram_bot import InstagramBot
import environ


env = environ.Env()
environ.Env.read_env(env_file='.env')

USERNAME = env.str('USERNAME')
PASSWORD = env.str('PASSWORD')
conn = psycopg2.connect(
    dbname=env.str('DBNAME'),
    user=env.str('DBUSER'),
    password=env.str('DBPASSWORD'),
    host=env.str('DBHOST'),
    port=env.str('DBPORT'))
cursor = conn.cursor()

db = Database(cursor, conn, USERNAME)
bot = InstagramBot(USERNAME, PASSWORD, USERNAME, db)
bot.run()
