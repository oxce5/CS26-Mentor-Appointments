
import os

from db import DatabaseConnection, User
DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")

with DatabaseConnection(DATABASE_PATH) as db:
    saved = db.insert_users([User(name="lalalal"), User(name="aaala")])
    print(saved)
    print(db.fetch_users())
