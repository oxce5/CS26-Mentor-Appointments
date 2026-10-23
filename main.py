from db import *

DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")

with DatabaseConnection(DATABASE_PATH) as users:
    print(users.fetch_users())

