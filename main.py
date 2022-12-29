#!/usr/bin/env python3.9

import cv2
import csv
import numpy as np
import tkinter as tk
from tkinter.filedialog import askopenfilename
from collections.abc import Generator
import math


def get_distance(point1: tuple[int, int], point2: tuple[int, int]) -> float:
    return round(math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2))


def get_bbox_center(bbox: list[int]) -> tuple[int, int]:
    return bbox[0] + round(bbox[2] / 2), bbox[1] + round(bbox[3] / 2)


class Image:
    scale = None  # Length per pixel.
    center = None

    def __init__(self, pixels: np.ndarray,
                 time: float,
                 bbox: tuple[int] = None):
        self.pixels = pixels
        self.bbox = bbox
        self.time = time

        self._line = []
        self._backup = None

    def _select_pixel(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDBLCLK:
            if len(self._line) < 2:
                self._line.append((x, y))
            else:
                self.pixels = self._backup.copy()
                self._line = [(x, y)]
            if len(self._line) == 2:
                self._backup = self.pixels.copy()
                self.pixels = cv2.line(self.pixels, self._line[0], self._line[1], (255, 0, 0), 3)
            return x, y

    def get_scale(self):
        print("Select two points by double clicking, and close this window to continue.")
        cv2.namedWindow("img")
        cv2.setMouseCallback("img", self._select_pixel)
        try:
            while cv2.getWindowProperty("img", 1) != -1:
                cv2.imshow("img", self.pixels)
                if cv2.waitKey(33) == 13:  # If enter is pressed.
                    break
        except cv2.error:
            pass
        finally:
            if len(self._line) != 2:
                print(f"Not exactly two points were selected! Selected: {self._line}.")
                cv2.destroyAllWindows()
                exit(0)

            cv2.imshow("img", self.pixels)
            cv2.waitKey(1)
            distance = get_distance(self._line[0], self._line[1])
            cm = float(input("Enter length of the marked line in cm: "))
            Image.scale = cm / distance  # Changes class attribute!

            self.pixels = self._backup.copy()
            self._backup = None
            cv2.destroyAllWindows()


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

    # Define Video and Tracker.
    video = Video(filename, fps=fps)
    tracker = cv2.TrackerCSRT_create()

    # Extract first frame.
    image = video.get_frame()

    # Get scale.
    image.get_scale()

    # Initialize tracker.
    bbox = cv2.selectROI("img", image.pixels, showCrosshair=True)
    Image.center = get_bbox_center(bbox)
    tracker.init(image.pixels, bbox)

    with open(filename.replace(".mp4", ".csv"), 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')
        csv_writer.writerow(["time [s]", "x elongation [cm]", "y elongation [cm]"])

        for image in video.watch():
            success, bbox = tracker.update(image.pixels)
            if success:
                center_of_mass = get_bbox_center(bbox)
                image.pixels = cv2.circle(image.pixels, center_of_mass, 2, color=(255, 0, 0), thickness=2)
                image.pixels = cv2.rectangle(image.pixels, rec=bbox, color=(255, 0, 0))

                assert isinstance(image.scale, float) and isinstance(image.center, tuple)
                x_elongation = (center_of_mass[0] - image.center[0]) * image.scale
                y_elongation = (center_of_mass[1] - image.center[1]) * image.scale
                image.pixels = cv2.putText(image.pixels, f"({round(x_elongation, 1)}|{round(y_elongation, 1)})",
                                           center_of_mass, cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 0, 0), 1)
                csv_writer.writerow([image.time, x_elongation, y_elongation])
            else:
                break
            cv2.imshow("img", image.pixels)
            cv2.waitKey(1)

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
