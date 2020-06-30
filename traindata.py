import face_recognition as fr
from mysql import connector
import pickle

mydb = connector.connect(host="localhost",user="root",passwd="",database="atomatedattendance")
mycursor = mydb.cursor()
mycursor.execute("SELECT uname,upic FROM studentregisteration")
myresult = mycursor.fetchall()

face_encoding_data = []
student_names = []
for data in myresult:
    student_names.append(data[0])
    face_encoding_data.append(fr.face_encodings(fr.load_image_file(data[1]))[0])
print(student_names,face_encoding_data)
with open('trainedmodels/student_names.pkl', 'wb') as f:
    pickle.dump(student_names, f)
f.close()
print("%s student names witten to file"%(len(student_names)))
with open('trainedmodels/face_encoding_data.pkl', 'wb') as f:
    pickle.dump(face_encoding_data, f)
f.close()
print("encodings written to file")
