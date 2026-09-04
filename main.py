"""Detector OpenCV que exibe e publica a ocupacao das vagas."""

from __future__ import annotations

import json
import os
import pickle
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import cv2
import cvzone
import numpy as np

from app.config import load_env
from app.domain import ParkingReading, classify_counts

ROOT = Path(__file__).resolve().parent
load_env(ROOT / ".env")
WIDTH, HEIGHT = 107, 48
PIXEL_THRESHOLD = int(os.getenv("PARKING_PIXEL_THRESHOLD", "900"))
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL_SECONDS", "5"))
API_URL = os.getenv("PARKING_API_URL", "").rstrip("/")
INGEST_KEY = os.getenv("PARKING_INGEST_KEY", "")
SOURCE_NAME = os.getenv("PARKING_SOURCE", "video-principal")


def video_source():
    configured = os.getenv("PARKING_VIDEO_SOURCE", str(ROOT / "video.mp4"))
    return int(configured) if configured.isdigit() else configured


def publish(reading: ParkingReading) -> None:
    """Envia uma leitura ao backend; falha de rede nao interrompe a deteccao."""
    if not API_URL:
        return
    request = Request(
        f"{API_URL}/api/readings",
        data=json.dumps(reading.to_dict()).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "X-Ingest-Key": INGEST_KEY},
    )
    try:
        with urlopen(request, timeout=5) as response:
            if response.status != 201:
                print(f"API retornou status {response.status}")
    except (URLError, TimeoutError) as error:
        print(f"Nao foi possivel publicar a leitura: {error}")


def inspect_spaces(processed_image, display_image, positions) -> ParkingReading:
    counts = []
    for x, y in positions:
        crop = processed_image[y : y + HEIGHT, x : x + WIDTH]
        counts.append(cv2.countNonZero(crop))

    spaces = classify_counts(counts, PIXEL_THRESHOLD)
    for (x, y), space in zip(positions, spaces):
        color = (0, 255, 0) if space["is_free"] else (0, 0, 255)
        thickness = 5 if space["is_free"] else 2
        cv2.rectangle(display_image, (x, y), (x + WIDTH, y + HEIGHT), color, thickness)
        cvzone.putTextRect(
            display_image,
            str(space["pixel_count"]),
            (x, y + HEIGHT - 3),
            scale=1,
            thickness=2,
            offset=0,
            colorR=color,
        )

    free_spaces = sum(space["is_free"] for space in spaces)
    cvzone.putTextRect(
        display_image,
        f"Livres: {free_spaces}/{len(positions)}",
        (100, 50),
        scale=3,
        thickness=5,
        offset=20,
        colorR=(0, 200, 0),
    )
    return ParkingReading.create(
        total_spaces=len(positions),
        free_spaces=free_spaces,
        spaces=spaces,
        source=SOURCE_NAME,
    )


def main() -> None:
    capture = cv2.VideoCapture(video_source())
    if not capture.isOpened():
        raise FileNotFoundError("Nao foi possivel abrir o video ou a camera configurada.")

    with (ROOT / "CarParkPos").open("rb") as positions_file:
        positions = pickle.load(positions_file)

    last_publish = 0.0
    try:
        while True:
            success, image = capture.read()
            if not success or image is None:
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, image = capture.read()
                if not success or image is None:
                    print("Erro ao ler o video.")
                    break

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (3, 3), 1)
            threshold = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16
            )
            median = cv2.medianBlur(threshold, 5)
            processed = cv2.dilate(median, np.ones((3, 3), np.uint8), iterations=1)
            reading = inspect_spaces(processed, image, positions)

            now = time.monotonic()
            if now - last_publish >= PUBLISH_INTERVAL:
                publish(reading)
                last_publish = now

            cv2.imshow("SmartParking", image)
            if cv2.waitKey(10) & 0xFF == 27:
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
