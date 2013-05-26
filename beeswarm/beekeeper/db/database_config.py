from pony.orm import Database, sql_debug, commit
db = None


def setup_db(path):
    global db
    db = Database('sqlite', path, create_db=True)
    #This needs to be read from file.
    from database import Classification
    c1 = Classification(type='dummy', description_short='dummy classificaiton', description_long='dummy classificaiton')
    commit()
