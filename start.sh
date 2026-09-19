#!/bin/bash

python app.py &
exec gunicorn --bind 0.0.0.0:$PORT app:flask_app
