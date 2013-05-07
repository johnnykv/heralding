from pony.orm import Database, sql_debug
#sql_debug(True)
db = None


def setup_db(path):
    global db
    db = Database('sqlite', path, create_db=True)