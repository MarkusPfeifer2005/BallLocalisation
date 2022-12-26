# Single Object Tracker

Usage:
1. Start the application. 
2. Select a mp4 file.
3. Select an object you want to track by holding the left mouse button pressed and create a bounding box.

The application then creates a csv file in the directory of the video.
The csv file has the following structure:

* Column 1: Index of the frame beginning at 0.
* Column 2: X-coordinate of the center pixel of the tracked object.
* Column 3: Y-coordinate of the center pixel of the tracked object.
