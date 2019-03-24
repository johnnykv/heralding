import json
import sqlite3

# inserting a user:
# sqlite3 db.sqlite3
# > insert into authkeys (owner, ident, secret, pubchans, subchans)
#      values ('owner', 'ident', 'secret', '["chan1"]', '["chan1"]');


class Authenticator(object):

    def __init__(self, path):
        self.sql = sqlite3.connect(path)
        self.check_db()

    def check_db(self):
        with self.sql:
            try:
                self.sql.execute("select * from logs, authkeys where 1=0")
            except sqlite3.OperationalError:
                print("setting up tables...")
                # create tables
                self.sql.execute("""
                create table logs (id integer primary key autoincrement,
                    data TEXT)
                """)
                self.sql.execute("""
                create table stats (id integer primary key autoincrement,
                    ak TEXT, uid TEXT, data TEXT)
                """)
                self.sql.execute("""
                create table authkeys (id integer primary key autoincrement,
                    owner TEXT, ident TEXT, secret TEXT,
                    pubchans TEXT, subchans TEXT)
                """)

    def close(self):
        self.sql.close()

    def get_authkey(self, ident):
        c = self.sql.cursor()
        try:
            c.execute("select * from authkeys where ident=?", (ident,))
            res = c.fetchone()
        except Exception:
            import traceback
            traceback.print_exc()
            return None
        finally:
            c.close()

        if not res:
            return None

        ak, owner, ident, secret, pubchans, subchans = res

        pubchans = json.loads(pubchans)
        subchans = json.loads(subchans)

        return dict(
            secret=secret,
            ident=ident,
            pubchans=pubchans,
            subchans=subchans,
            owner=owner,
        )
