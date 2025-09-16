#! /usr/bin/env python3

from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.getenv('DB_URL')

engine = create_engine(DB_URL)

from database import Base
from sqlalchemy_schemadisplay import create_schema_graph

graph = create_schema_graph(
    metadata=Base.metadata,
    engine=engine,
    show_datatypes=False,
    show_indexes=False,
    rankdir='LR'
)

graph.write_png('models_erd.png')