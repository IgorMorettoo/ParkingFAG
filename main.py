import cv2
import pickle
import cvzone
import numpy as np

# Video feed
cap = cv2.VideoCapture('video.mp4')

# Verifica se o vídeo foi aberto
if not cap.isOpened():
    raise FileNotFoundError(
        "Não foi possível abrir 'Testvideo.mp4'. "
        "Verifique se o arquivo está na mesma pasta do main.py."
    )

with open('CarParkPos', 'rb') as f:
    posList = pickle.load(f)

width, height = 107, 48


def checkParkingSpace(imgPro, img):
    spaceCounter = 0

    for pos in posList:
        x, y = pos

        imgCrop = imgPro[y:y + height, x:x + width]
        count = cv2.countNonZero(imgCrop)

        if count < 900:
            color = (0, 255, 0)
            thickness = 5
            spaceCounter += 1
        else:
            color = (0, 0, 255)
            thickness = 2

        cv2.rectangle(
            img,
            pos,
            (x + width, y + height),
            color,
            thickness
        )

        cvzone.putTextRect(
            img,
            str(count),
            (x, y + height - 3),
            scale=1,
            thickness=2,
            offset=0,
            colorR=color
        )

    cvzone.putTextRect(
        img,
        f'Free: {spaceCounter}/{len(posList)}',
        (100, 50),
        scale=3,
        thickness=5,
        offset=20,
        colorR=(0, 200, 0)
    )


while True:

    success, img = cap.read()

    # Se chegou ao final ou houve falha na leitura,
    # volta para o começo do vídeo
    if not success or img is None:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        success, img = cap.read()

        if not success or img is None:
            print("Erro ao ler o vídeo.")
            break

    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    imgBlur = cv2.GaussianBlur(
        imgGray,
        (3, 3),
        1
    )

    imgThreshold = cv2.adaptiveThreshold(
        imgBlur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        25,
        16
    )

    imgMedian = cv2.medianBlur(
        imgThreshold,
        5
    )

    kernel = np.ones(
        (3, 3),
        np.uint8
    )

    imgDilate = cv2.dilate(
        imgMedian,
        kernel,
        iterations=1
    )

    checkParkingSpace(imgDilate, img)

    cv2.imshow("Image", img)

    # ESC para fechar
    if cv2.waitKey(10) & 0xFF == 27:
        break


cap.release()
cv2.destroyAllWindows()