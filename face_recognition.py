import cv2, dlib

video_capture = cv2.VideoCapture(0)
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

while True:
    # capture
    ret, frame = video_capture.read()

    # optimise
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    clahe_image = clahe.apply(gray)

    # detect
    detections = detector(clahe_image, 1)
    for k,d in enumerate(detections):
        shape = predictor(clahe_image, d)
        for i in range(1,68):
            cv2.circle(frame, (shape.part(i).x, shape.part(i).y), 1, (0,0,255), thickness=2)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Display the resulting frame
    cv2.imshow('Insure Ride - Face Recognition', frame)

# When everything is done, release the capture
video_capture.release()
cv2.destroyAllWindows()
