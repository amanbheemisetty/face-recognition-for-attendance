import io
import cv2
import os
import pickle
import datetime
import shutil
from mysql import connector
import face_recognition as fr
from flask import Flask, render_template, Response,request,redirect,url_for,session
from flask_mail import Mail,Message

app = Flask(__name__)
app.config.update(
    DEBUG=True,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME='',
    MAIL_PASSWORD=''
)
app.secret_key="amanfromsvitcollege"
mail = Mail(app)
mydb = connector.connect(host="localhost",user="root",passwd="",database="atomatedattendance")
mycursor = mydb.cursor()
vc = cv2.VideoCapture(0)
current_date=datetime.datetime.now().strftime('%Y-%m-%d')

with open('trainedmodels/student_names.pkl', 'rb') as f:
    student_names=pickle.load(f)
f.close()
with open('trainedmodels/face_encoding_data.pkl', 'rb') as f:
    face_encoding_data=pickle.load(f)
f.close()

@app.route('/')
def index():
    return render_template('index.html')

def gen():
    process_this_frame = True
    while True:
        read_return_code, frame = vc.read()
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]
        if process_this_frame:
            face_locations = fr.face_locations(rgb_small_frame)
            face_encodings = fr.face_encodings(rgb_small_frame, face_locations)
            face_names = []
            try:
                for face_encoding in face_encodings:
                    matches = fr.compare_faces(face_encoding_data, face_encoding)
                    if True in matches:
                        first_match_index = matches.index(True)
                        name = student_names[first_match_index]
                        face_names.append(name)
                    else:continue
            except:pass
        process_this_frame = not process_this_frame

        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            sql = "SELECT * FROM attendance where student_id=(SELECT id FROM studentregisteration WHERE uname=%s) and login=%s"
            mycursor.execute(sql, (name,current_date))
            myresult = mycursor.fetchall()
            if(len(myresult) < 1):
                sql = "insert into attendance(student_id,login) VALUES((SELECT id FROM studentregisteration WHERE uname=%s),%s)"
                val = (name,current_date)
                mycursor.execute(sql, val)
                mydb.commit()
        encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(),mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_register():
    while True:
        read_return_code, frame = vc.read()
        encode_return_code, image_buffer = cv2.imencode('.jpg', frame)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')

@app.route('/register_feed')
def register_feed():
    return Response(gen_register(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/captureimage')
def captureimage():
    if 'user' not in session:
        return redirect('/')
    read_return_code, frame = vc.read()
    shutil.rmtree('static/temp')
    os.mkdir('static/temp')
    img_path='static/temp/'+str(datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))+'.jpg'
    cv2.imwrite(img_path, frame)
    try:
        person_identified=fr.face_encodings(fr.load_image_file(img_path))[0]
        if len(person_identified) > 0:
            return img_path
        else:return 'static/error_face.jpg'
    except:
        return 'static/error_face.jpg'

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        try:
            userdetails=request.form
            sql="SELECT * FROM user where username=%s and password=%s"
            mycursor.execute(sql,(userdetails['name'],userdetails['password']))
            myresult = mycursor.fetchone()
            if myresult:
                session['user']=myresult[0]
                return redirect(url_for('adminpanel'))
        except:pass
    return render_template('index.html',message="Invalid Username or password")

@app.route('/adminpanel', methods=['GET','POST'])
def adminpanel():
    if 'user' not in session:
        return redirect('/')
    mycursor.execute("SELECT * FROM studentregisteration;")
    myresult = mycursor.fetchall()
    mycursor.execute("SELECT sr.id FROM studentregisteration sr,attendance a WHERE sr.id=a.student_id and login='"+current_date+"'")
    today_attendance = mycursor.fetchall()
    today_attendance=[a[0] for a in today_attendance]
    if 'message' in session:
        message=session['message']
        session.pop('message',None)
        return render_template('dashboard.html', adminpanel=myresult, attendance=today_attendance,message=message)
    return render_template('dashboard.html',adminpanel=myresult,attendance=today_attendance)

@app.route('/sendMail/<id>')
def sendMail(id):
    if 'user' not in session:
        return redirect('/')
    try:
        sql = "SELECT * FROM studentregisteration WHERE id="+id
        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        student_info=myresult[0]
        msg = Message("Attendance Status: SVIT college",sender="parvam.apps@gmail.com",recipients=[str(student_info[4])])
        msg.html = "<h1>Sai Vidya Institute of Technology</h1><h2>Attendance Report:</h2><br>"+\
                   "<h3>student name :"+str(student_info[1])+"<br>Absent Date:"+str(current_date)+"</h3>"+\
                   "<p>parents are requested to answer back with proper reason if leave not because of Illness, Injury," \
                   " Dental appointment, Medical appointment, Approved educational activity, Religious/cultural ceremony</p><br>" \
                   "<h4>Thank you</h4>"
        mail.send(msg)
        session['message']='Mail sent'
        return redirect(url_for('adminpanel'))
    except Exception as e:
        session['message'] = 'Unable to Send Mail'
        return redirect(url_for('adminpanel'))
@app.route('/showattendance/<id>')
def showattendance(id):
    if 'user' not in session:
        return redirect('/')
    mycursor = mydb.cursor()
    sql="SELECT @a:=@a+1 serial_number,login FROM attendance,(SELECT @a:= 0) AS a where student_id="+id
    mycursor.execute(sql)
    myresult = mycursor.fetchall()
    return render_template('studentattendance.html', studentattendance=myresult)

@app.route('/register', methods=['GET','POST'])
def register():
    if 'user' not in session:
        return redirect('/')
    if request.method=='POST':
        try:
            userdetails=request.form
            shutil.move(userdetails['imagepath'],'static/studentimages')
            file_path=os.path.join('static/studentimages', os.path.basename(userdetails['imagepath']))

            sql = "INSERT INTO studentregisteration(uname, upic, phone, email, addr ) VALUES (%s, %s, %s, %s,%s)"
            val = (userdetails['uname'], file_path, userdetails['phone'], userdetails['email'], userdetails['addr'])
            mycursor.execute(sql, val)
            mydb.commit()
            mycursor.execute("SELECT uname,upic FROM studentregisteration")
            myresult = mycursor.fetchall()

            face_encoding_data.clear()
            student_names.clear()

            for data in myresult:
                student_names.append(data[0])
                face_encoding_data.append(fr.face_encodings(fr.load_image_file(data[1]))[0])

            with open('trainedmodels/student_names.pkl', 'wb') as f:
                pickle.dump(student_names, f)
            f.close()
            print("%s student names written to file" % (len(student_names)))
            with open('trainedmodels/face_encoding_data.pkl', 'wb') as f:
                pickle.dump(face_encoding_data, f)
            f.close()
            print("encodings written to file")

            return render_template('register.html',message='success')
        except Exception as e:
            print(e)
            return render_template('register.html')
    return render_template('register.html')

@app.route('/generatereport',methods=['GET','POST'])
def generatereport():
    if 'user' not in session:
        return redirect('/')
    if request.method=='POST':
        try:
            userdetails=request.form
            sql = "SELECT @a:=@a+1 serial_number,uname,login FROM attendance ac , studentregisteration sr,(SELECT @a:= 0) AS a  WHERE sr.id=ac.student_id and login >=%s and login <=%s ORDER BY login ASC"
            mycursor.execute(sql,(userdetails['fromdate'],userdetails['todate']))
            myresult = mycursor.fetchall()
            return render_template('reports.html',attendance=myresult)
        except:pass
    return render_template('reports.html')

@app.route('/logout', methods=['GET','POST'])
def logout():
    session.pop('user',None)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)