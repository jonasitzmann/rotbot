import redis
import os

db = redis.Redis(
  host='redis-19410.c265.us-east-1-2.ec2.cloud.redislabs.com',
  port=19410,
  password=os.environ.get('REDISPWD'))

def get_key_names():
    return db.get('keys')