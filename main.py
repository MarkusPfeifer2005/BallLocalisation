#!/usr/bin/env python3.9

import cv2
import csv
from tkinter import Tk
from tkinter.filedialog import askopenfilename


def main():
    Tk().withdraw()
    filename = askopenfilename()
    if not filename.endswith(".mp4"):
        print(f"File '{filename}' is invalid. It must be an mp4 file.")
        exit(0)
    vid = cv2.VideoCapture(filename)
    tracker = cv2.TrackerCSRT_create()

    _, img = vid.read()
    bbox = cv2.selectROI("img", img, showCrosshair=True)
    tracker.init(img, bbox)

    with open(filename.replace(".mp4", ".csv"), 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')
        csv_writer.writerow(["index of frame", "x pixel coordinate", "y pixel coordinate"])
        try:
            frame_idx = 0
            while cv2.getWindowProperty("img", 1) != -1:
                success, img = vid.read()
                if success:
                    success, bbox = tracker.update(img)
                    if success:
                        img = cv2.rectangle(img, rec=bbox, color=(255, 0, 0))
                        csv_writer.writerow([frame_idx, bbox[0] + bbox[1]/2, bbox[2] + bbox[3]/2])
                    else:
                        break
                    cv2.imshow("img", img)
                    cv2.waitKey(1)
                else:
                    break
                frame_idx += 1
        except cv2.error:
            print("Application was closed by the user.")
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
