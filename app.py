from flask import Flask

app = Flask(__name__)

@app.route('/poster/<template_name>')
def get_poster_template(template_name):
    return f"Placeholder for poster template: {template_name}"

if __name__ == '__main__':
    app.run(debug=True)
