#!/usr/bin/env python3.9

import cv2
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

    try:
        while cv2.getWindowProperty("img", 1) != -1:
            success, img = vid.read()
            if success:
                success, bbox = tracker.update(img)
                if success:
                    img = cv2.rectangle(img, rec=bbox, color=(255, 0, 0))
                else:
                    break
                cv2.imshow("img", img)
                cv2.waitKey(1)
            else:
                break
    except cv2.error:
        print("Application was closed by the user.")
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
