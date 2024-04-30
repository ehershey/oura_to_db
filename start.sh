#!/bin/sh
gunicorn serve:app -b :8080
