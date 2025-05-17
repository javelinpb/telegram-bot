from flask import Flask
import logging

app = Flask(__name__)

@app.route('/')
def index():
    return "Бот запущен!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
