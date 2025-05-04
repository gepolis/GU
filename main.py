from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('templates', 'test.htm')

@app.route('/setup/')
def setup():
    return render_template('setup.html')

@app.route('/profile/personal/id-doc')
def id_doc():
    return send_from_directory('templates', 'pass_data.htm')
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)