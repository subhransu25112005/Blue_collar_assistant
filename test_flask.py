from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "Flask is running!"

if __name__ == "_main_":
    app.run(debug=True)