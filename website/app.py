from flask import Flask

# Initiate app
app = Flask(__name__)


# Import routes
from routes import index

if __name__ == '__main__':
    app.run()