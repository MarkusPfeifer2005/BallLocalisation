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

    def __init__(self, pixels: np.ndarray, time: float):
        self.pixels = pixels
        self.time = time
        self.bbox = None

        self._line = []

    def _draw_line(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDBLCLK:
            if len(self._line) < 2:
                self._line.append((x, y))
            else:
                self._line = [(x, y)]

    def get_scale(self):
        print("Select two points by double clicking, and press enter to continue.")
        cv2.namedWindow("img")
        cv2.setMouseCallback("img", self._draw_line)
        try:
            while cv2.getWindowProperty("img", 1) != -1:
                cv2.imshow("img", self.numpy)
                if cv2.waitKey(33) == 13:  # If enter is pressed.
                    break
        except cv2.error:
            pass
        finally:
            if len(self._line) != 2:
                print(f"Not exactly two points were selected! Selected: {self._line}.")
                cv2.destroyAllWindows()
                exit(0)

            print(self._line)
            cv2.imshow("img", self.numpy)
            cv2.waitKey(1)
            distance = get_distance(self._line[0], self._line[1])
            cm = float(input("Enter length of the marked line in cm: "))
            Image.scale = cm / distance  # Changes class attribute!

            cv2.destroyAllWindows()

    @property
    def center_of_mass(self) -> tuple:
        return get_bbox_center(self.bbox)

    def get_elongation(self, direction: str) -> float:
        if direction.lower() == 'x':
            return (self.center_of_mass[0] - self.center[0]) * self.scale
        elif direction.lower() == 'y':
            return (self.center_of_mass[1] - self.center[1]) * self.scale
        else:
            raise ValueError(f"Direction '{direction}' is invalid; must be 'x' or 'y'!")

    @property
    def numpy(self):
        pixels = self.pixels.copy()
        #  Apply transformations on the image.
        if self.bbox:
            pixels = cv2.rectangle(pixels, rec=self.bbox, color=(255, 0, 0))
            pixels = cv2.circle(pixels, self.center_of_mass, 2, color=(255, 0, 0), thickness=2)
            pixels = cv2.putText(pixels, f"({round(self.get_elongation('x'), 1)}|{round(self.get_elongation('y'), 1)})",
                                 self.center_of_mass, cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 0, 0), 1)
        if len(self._line) == 2:
            pixels = cv2.line(self.pixels, self._line[0], self._line[1], (255, 0, 0), 3)
        return pixels

    @center_of_mass.setter
    def center_of_mass(self, value):
        self._center_of_mass = value


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
                image.bbox = bbox
                csv_writer.writerow([image.time, image.get_elongation('x'), image.get_elongation('y')])
            else:
                break
            cv2.imshow("img", image.numpy)
            cv2.waitKey(1)

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
