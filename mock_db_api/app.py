from flask import Flask, jsonify, request
from mysql.connector import connect, Error
from config import DB_HOST, DB_PASSWORD, DB_USER
import subprocess

app = Flask(__name__)
API_KEY = "test-key-12345"

def get_db_connection():
    return connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database='card_issuance')

def require_api_key(f):
    def decoreate_function(*args, **kwargs):
        if request.headers.get("X-API-Key") != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    
    return decoreate_function

@app.route('/students/<reg_number>', methods=['GET'])
@require_api_key
def get_student(reg_number):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE reg_number = %s", (reg_number,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()

    if student:
        return jsonify(student), 200
    return jsonify({"error": "Student not found"}), 404

if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000")
    print("API Key required: X-API-Key: test-key-12345")
    app.run(debug=True, host='0.0.0.0', port=5000)