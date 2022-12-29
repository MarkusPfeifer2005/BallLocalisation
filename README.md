# Single Object Tracker

Usage:
1. Start the application. 
2. Select a mp4 file.
3. Select two points by double-clicking twice on the image and confirming with [enter].
4. Enter a reference value (in cm) of the selected distance.
5. Select an object you want to track by holding the left mouse button pressed and create a bounding box.

The application then creates a csv file in the directory of the video.
Be aware that the video is displayed upside down. Since this has no effect on the intended usage, it
remains unchanged. The csv file has the following structure:

* Column 1: Index of the frame beginning at 0.
* Column 2: X-elongation of the center pixel of the tracked object.
* Column 3: Y-elongation of the center pixel of the tracked object.
