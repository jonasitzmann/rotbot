import redis
import os
import json



db = redis.Redis(
    host="redis-19410.c265.us-east-1-2.ec2.cloud.redislabs.com",
    port=19410,
    password=os.environ.get("REDISPWD"),
    decode_responses=True,
)


def get_key_names(ctx=None):
    return list(db.get("keys").split(","))


class DbDict(dict):
    def __init__(self, db_name, db: redis.Redis=db):
        self.db = db
        self.db_name = db_name
        initial_dict = {}
        db_content = self.db.get(self.db_name)
        if db_content is not None:
            initial_dict = json.loads(db_content)
        super().__init__(initial_dict)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        json_str = json.dumps(self)
        self.db.set(self.db_name, json_str)
