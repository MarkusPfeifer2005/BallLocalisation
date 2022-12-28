#!/usr/bin/env python3.9

import cv2
import csv
import numpy as np
import tkinter as tk
from tkinter.filedialog import askopenfilename
from collections.abc import Generator


class Image:
    def __init__(self, pixels: np.ndarray, time: float, center: tuple[int, int] = None, bbox: tuple[int] = None):
        self.pixels = pixels
        self.center = center
        self.bbox = bbox
        self.time = time


class Video:
    def __init__(self, path: str, fps: float):
        self.images = cv2.VideoCapture(path)
        self.time_per_image = 1. / fps
        self._time = 0.

    def watch(self) -> Generator[Image]:
        try:
            while cv2.getWindowProperty("img", 1) != -1:
                success, img = self.images.read()
                if success:
                    yield Image(pixels=img, time=self._time)
                else:
                    break
                self._time += self.time_per_image
        except cv2.error:
            print("Application was closed by the user.")

    def get_frame(self) -> Image:
        _, img = self.images.read()
        self._time += self.time_per_image
        return Image(img, time=self._time - self.time_per_image)


def main():
    # Define fps.
    fps: float = 100.

    # Select file.
    window = tk.Tk()
    window.withdraw()
    filename = askopenfilename()
    if not filename.endswith(".mp4"):
        print(f"File '{filename}' is invalid. It must be an mp4 file.")
        exit(0)

    video = Video(filename, fps=fps)
    tracker = cv2.TrackerCSRT_create()

    image = video.get_frame().pixels
    bbox = cv2.selectROI("img", image, showCrosshair=True)
    tracker.init(image, bbox)

    with open(filename.replace(".mp4", ".csv"), 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')
        csv_writer.writerow(["time [s]", "x pixel coordinate", "y pixel coordinate"])

        for image in video.watch():
            success, bbox = tracker.update(image.pixels)
            if success:
                image.pixels = cv2.rectangle(image.pixels, rec=bbox, color=(255, 0, 0))
                csv_writer.writerow([image.time, bbox[0] + bbox[1] / 2, bbox[2] + bbox[3] / 2])
            else:
                break
            cv2.imshow("img", image.pixels)
            cv2.waitKey(1)

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
