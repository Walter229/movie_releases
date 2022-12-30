from flask import render_template
from app import app

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/donate')
def donate():
    return render_template('donate.html')

# CSS Styling
@app.route('/static/style.css')
def style():
    return app.send_static_file('style.css')

# Background
@app.route('/static/cinema_background.png')
def background():
    return app.send_static_file('cinema_background.png')