"""
This module initializes the Flask application and loads a JSON graph file.

The Flask application is created using the Flask class from the flask module.
The JSON graph file is loaded and stored in the GRAPH variable.

The routes module is imported to register the routes for the application.
"""

import json
from flask import Flask

app = Flask(__name__)

with open("app/graph.json") as f:
    GRAPH = json.load(f)


from app import routes
