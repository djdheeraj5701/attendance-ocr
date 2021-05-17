import sqlite3
import urllib.request
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import sqlalchemy as db
import requests
import os
import json
import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.sqlite'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS

column_headers=['id','year','div','lec','date','absent']

engine=db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'],connect_args={"check_same_thread":False})
connection = engine.connect()
metadata = db.MetaData()
'''
        id | year | div | lec | date | absent |
'''
table=db.Table('attendance', metadata,
                        db.Column(column_headers[0],db.Integer, primary_key=True),
                        db.Column(column_headers[1],db.String(2)),
                        db.Column(column_headers[2],db.String(2)),
                        db.Column(column_headers[3],db.String(6)),
                        db.Column(column_headers[4],db.String(10)),  # yyyy-mm-dd
                        db.Column(column_headers[5],db.String(200)),  # rr,rr,...
                    )

metadata.create_all(engine)

@app.route('/')
def index():
    query="SELECT * FROM attendance"
    result_proxy = connection.execute(query)
    results=result_proxy.fetchall()
    return render_template('index.html', results=results)

def ocrPosting(filename):
    url_api= "https://api.ocr.space/parse/image"
    payload = {
        'isOverlayRequired': False,
        "apikey": "helloworld",
        "language": "eng",
        "OCREngine":2
    }
    with open(filename,'rb') as f:
        var = requests.post(url_api,files={filename:f} ,data=payload)
    var1 = var.content.decode()
    results = json.loads(var1)
    parsed_results=results.get("ParsedResults")
    if parsed_results!=[]:
        parsed_text=parsed_results[0].get("ParsedText")
        return parsed_text
    else:
        return "Error"

@app.route("/nextQn",methods=['POST'])
def nextQn(id):
    query = f"SELECT * FROM attendance WHERE id={id+1}"
    result_proxy = connection.execute(query)
    results = result_proxy.fetchall()
    return render_template('index.html', results=results)

@app.route('/insert',methods=['POST'])
def insert():
    file = request.files['file']
    if file and allowed_file(file.filename):
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], "filename.png"))
        results=ocrPosting(app.config['UPLOAD_FOLDER']+"filename.png")
        if results == "Error":
            return redirect("/")
        date = str(datetime.datetime.now().date())
        results=results.split('\n')
        i=1
        while i<len(results):
            if results[i][:3] not in ["FE-","SE-","TE-","BE-"]:
                results[i-1]+=" "+results[i]
                results.pop(i)
            else:
                i+=1
        print(results)
        for result in results:
            try:
                year=result[:2]
                i=3
                div=""
                while result[i] not in [" ","\n"]:
                    div+=result[i]
                    i+=1
                lec=""
                while result[i]==" ":
                    i+=1
                while result[i]!=" ":
                    lec+=result[i]
                    i+=1
                while result[i]==" ":
                    i+=1
                absent=result[i:]
                query="INSERT INTO attendance (year,div,lec,date,absent) VALUES (?,?,?,?,?)"
                connection.execute(query,(year,div,lec,date,absent))
            except:
                pass
    return redirect("/")

@app.route('/delete/<id>')
def delete(id):
    query='DELETE FROM attendance WHERE id=?'
    connection.execute(query,id)
    return redirect(url_for('index'))

@app.route('/update/<id>',methods=["POST"])
def update(id):
    topic,change=request.form['req'].split(":")
    query=f'UPDATE attendance SET {topic}=? WHERE id=?'
    connection.execute(query,(change,id))
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False)



