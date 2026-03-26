from flask import Flask, jsonify, request
from datetime import datetime
import os

app = Flask(__name__)
API_KEY = 'dev-api-key-12345'

def generate_student_email(first_name, surname, registration_number):
    """Generate a default university email from student's credentials"""
    year_suffix = registration_number[:4][-2:]
    first_name_l = first_name.lower()
    surname_l = surname.lower()
    return f"{first_name_l}.{surname_l}_{year_suffix}@student.udsm.ac.tz"

STUDENTS = {
    '2022-04-09050': {
        'registration_number': '2022-04-09050',
        'first_name': 'Samuel',
        'surname': 'Musyani',
        'email': generate_student_email('Samuel', 'Musyani', '2022-04-09050'),
        'date_of_birth': "14/04/2004",
        'nationality': 'Tanzanian',
        'programme': 'BSc. Electronics Engineering',
        'faculty': 'College of Information and Communication Technologies',
        'phone_number': '+255773422381',
        'registration_status': 'active',
        'year_of_study': 4,
    },

    '2022-04-12357': {
        'registration_number': '2022-04-12357',
        'first_name': 'Godson',
        'surname': 'Shirima',
        'email': generate_student_email('Godson', 'Shirima', '2022-04-12357'),
        'date_of_birth': "10/03/2002",
        'nationality': 'Tanzanian',
        'programme': 'BSc. Telecommunications Engineering',
        'faculty': 'College of Information and Communication Technologies',
        'phone_number': '+255755981777',
        'registration_status': 'active',
        'year_of_study': 4,
    },
    
    '2022-04-05392': {
        'registration_number': '2022-04-05392',
        'first_name': 'Devotha',
        'surname': 'Lyakurwa',
        'email': generate_student_email('Devotha', 'Lyakurwa', '2022-04-05392'),
        'date_of_birth': "30/07/2002",
        'nationality': 'Tanzanian',
        'programme': 'BSc. Telecommunications Engineering',
        'faculty': 'College of Information and Communication Technologies',
        'phone_number': '+255783632556',
        'registration_status': 'active',
        'year_of_study': 4,
    },
}