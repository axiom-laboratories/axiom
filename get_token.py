import sqlite3
import uuid
import base64
import json

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
import datetime

DATABASE_URL = "postgresql://puppet:masterpassword@localhost:5432/puppet_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

t = uuid.uuid4().hex
session.execute(text("INSERT INTO tokens (token, created_at, used) VALUES (:t, :created_at, :used)"), {"t": t, "created_at": datetime.datetime.utcnow(), "used": False})
session.commit()

import subprocess
ca = open('secrets/ca/root_ca.crt').read()
payload = {'t': t, 'ca': ca}
token_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
print(token_b64)
