import os
from pony.orm import Database, sql_debug, commit
import json
db = None


def setup_db(path):
    global db
    if not db:
        db = Database('sqlite', path, create_db=True)

        from database import Classification
        db_path = os.path.dirname(__file__)

        #bootstrapping the db with classifications types
        json_file = open(os.path.join(db_path, 'bootstrap.json'))
        data = json.load(json_file)
        #making sure that entities does not fall out of scope before commit
        classifications = {}
        for entry in data['classifications']:
            c = Classification.get(type=entry['type'])
            if not c:
                classifications[entry['type']] = Classification(type=entry['type'],
                                                                description_short=entry['description_short'],
                                                                description_long=entry['description_long'])
            else:
                c.description_short = entry['description_short']
                c.description_long = entry['description_long']
        commit()

def clear_db():
    db.entities.clear()
