from flask import Flask, render_template, request, jsonify
from chatbot import dialogue_mgmt_system

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    if not user_message:
        return jsonify({'response': 'Please enter a valid message.'})
    
    response = dialogue_mgmt_system(user_message)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)
