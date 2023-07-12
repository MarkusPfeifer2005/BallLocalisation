# usr/bin/env python3
import cv2
import matplotlib.pyplot as plt
import json
import pandas as pd
import warnings


def plot_trace(video_path: str):
    """Saves a plot at the same location as the video file."""
    warnings.filterwarnings("ignore", category=UserWarning)  # TODO: adjust code, so suppression is no longer needed.
    with open(video_path.replace(".mp4", ".json"), "r") as json_file:
        configuration = json.loads(json_file.read())
        x_start = configuration["x start"]
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
    success, frame = cap.read()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

    data = pd.read_csv(video_path.replace(".mp4", ".csv"))
    figure, axes = plt.subplots(ncols=2, figsize=(20, 10), dpi=200)
    axes[0].imshow(frame)
    axes[0].scatter(data["x [pixels]"]+x_start, data["y [pixels]"], color="red", s=2)
    axes[1].scatter(data["time [s]"], data["x [mm]"], color="blue", s=2)
    axes[1].plot(data["time [s]"], data["x [mm]"], color="blue", linewidth=1, label="x")
    axes[1].scatter(data["time [s]"], data["y [mm]"], color="orange", s=2)
    axes[1].plot(data["time [s]"], data["y [mm]"], color="orange", linewidth=1, label="y")

    axes[0].set_title("position per frame")
    axes[0].set_xlabel("x [pixels]")
    axes[0].set_ylabel("y [pixels]")
    axes[1].set_title("position over time")
    axes[1].set_xlabel("time [s]")
    axes[1].set_ylabel("position [mm]")
    axes[1].legend(loc="best")
    plt.savefig(video_path.replace(".mp4", ".png"))
    plt.close()
