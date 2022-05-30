from os import environ

from databases import Database
from dotenv import load_dotenv  # type: ignore
from sqlalchemy import MetaData

load_dotenv()

database = Database(environ["DB_URI"])
metadata = MetaData()
