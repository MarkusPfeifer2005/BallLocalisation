# usr/bin/env python3

import tkinter as tk
from tkinter import filedialog
import cv2
import os
import threading
from PIL import Image, ImageTk
import math
from functools import partial
import json

from matplotlib import pyplot as plt

from backend_functions import plot_trace


class DistanceMenu(tk.Frame):
    def __init__(self, root, working_directory: str):
        tk.Frame.__init__(self, root)
        self.points = []
        self.reference_image = None
        self.is_active = False
        self.entered_distance = None  # [mm]
        self.working_directory = working_directory

        self.canvas = tk.Canvas(self, background="#fff")
        self.canvas.pack(anchor="n")
        self.canvas.bind("<Button-1>", self.on_mouseclick)

        self.distance_form = tk.Frame(self)
        self.label = tk.Label(self.distance_form, text="Enter length [mm]:")
        self.label.pack(side="left")
        self.entry = tk.Entry(self.distance_form)
        self.entry.bind('<Return>', self.submit)
        self.entry.pack(expand=True, fill="both", side="left")
        self.button = tk.Button(self.distance_form, text="submit", command=self.submit)
        self.button.pack(side="right")
        self.distance_form.pack()

        self.scale = tk.Scale(self, orient="horizontal", command=self.refresh_canvas_image)
        self.scale.pack(expand=True, fill="both", side="bottom")

    def _draw_canvas_image(self):
        if not os.path.isdir(self.working_directory):  # TODO: remove duplicate
            os.makedirs(self.working_directory)
        video_path = [os.path.join(self.working_directory, file)
                      for file in os.listdir(self.working_directory) if file.endswith(".mp4")][0]
        cap = cv2.VideoCapture(video_path)
        success, image = cap.read()
        image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.canvas.configure(height=image.shape[0], width=image.shape[1])
        self.scale.configure(to=image.shape[1])
        image = Image.fromarray(image)
        self.reference_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.reference_image)

    def _draw_points(self):
        for point in self.points:
            self.canvas.create_oval(*point, *point, width=7, fill="#f00", outline="#f00")
            self.canvas.create_text(point[0]+40, point[1]+10, text=str(point), fill="#f00")

    def _draw_line(self):
        self.canvas.create_line(self.scale.get(), 0, self.scale.get(), self.canvas.winfo_width(), fill="#00f", width=2)

    def on_mouseclick(self, event):
        if len(self.points) > 1:
            self.points = []
            self._draw_canvas_image()
        self.points.append((event.x, event.y))
        self._draw_points()

    def refresh_canvas_image(self, event=None):
        self.canvas.delete("all")
        self._draw_canvas_image()
        self._draw_points()
        self._draw_line()

    def show(self):
        self.pack(side="right", fill="none", anchor="nw", expand=False)
        self.is_active = True
        self._draw_canvas_image()

    def hide(self) -> float or None:
        self.is_active = False
        self.pack_forget()
        self._draw_canvas_image()
        if len(self.points) > 1 and self.entered_distance is not None:
            pixel_length = math.sqrt(abs(self.points[0][0] - self.points[1][0])**2
                                     + abs(self.points[0][1] - self.points[1][1])**2)
            return self.entered_distance / pixel_length

    def submit(self, event=None):
        user_input = self.entry.get()
        self.entry.delete(first=0, last="end")
        try:
            self.entered_distance = float(user_input)
            self.entry.insert(0, f"Length is set to: {self.entered_distance} mm")
            self.entry["background"] = "#3f3"
        except ValueError:
            self.entry.insert(0, "Only floats are allowed!")
            self.entry["background"] = "#f33"

    @property
    def x_start(self):
        return self.scale.get()


class Workspace(tk.Frame):
    def __init__(self, root, icon_path: str, name: str, change_workspace):
        tk.Frame.__init__(self, root)
        self.icon_path = icon_path  # TODO: remove?
        self.name = name

        self.status_bar = tk.Frame(self)
        self.home_button_image = tk.PhotoImage(file="images/house.png")
        self.home_button = tk.Button(self.status_bar, image=self.home_button_image, command=self.go_home)
        self.photo_icon = tk.PhotoImage(file=self.icon_path)
        self.icon = tk.Label(self.status_bar, image=self.photo_icon)
        self.name_tag = tk.Label(self.status_bar, text=self.name)
        self.home_button.pack(anchor="w", side="left")
        self.icon.pack(anchor="center")
        self.name_tag.pack(anchor="center")
        self.status_bar.pack(fill="x")

        self.change_workspace = change_workspace

    def go_home(self):
        self.change_workspace(0)


class Home(Workspace):
    def __init__(self, root, change_workspace, workspaces):
        super().__init__(root, "images/house.png", "home", change_workspace)

        self.label = tk.Label(self, text="Select your workspace:", font=("arial", 20), padx=20, pady=20)
        self.label.pack()

        self.workspaces = []
        for index, workspace in enumerate(workspaces):
            frame = tk.Frame(self)
            button = tk.Button(frame, image=workspace.photo_icon, command=partial(workspace.change_workspace, index+1))
            label = tk.Label(frame, text=workspace.name, padx=30)
            self.workspaces.append(frame)

            button.pack(side="left")
            label.pack(side="right")
            frame.pack()


class BrightnessTracker(Workspace):
    def __init__(self, root, change_workspace):
        super().__init__(root, "images/sun.png", "brightness tracker", change_workspace)

        self.working_directory = "./Videos"
        self.is_running = False
        self.current_frame = None
        self.lock = threading.Lock()
        self.pixel_length = 1.  # [mm]

        self.palette = tk.Frame(self, background="red")
        self.palette.pack(side="left", anchor="nw", fill="both", expand=False)

        self.working_directory_button = tk.Button(self.palette, text="select directory",
                                                  command=self.open_working_directory)
        self.working_directory_button.pack(anchor="n", padx=10, pady=10)
        self.working_directory_display = tk.Label(self.palette,
                                                  text=f"Selected working directory:\n{self.working_directory}")
        self.working_directory_display.pack(padx=10, pady=10)
        self.start_button = tk.Button(self.palette, text="start", command=self.start, background="#090",
                                      activebackground="#070", padx=10, pady=10)
        self.start_button.pack()
        self.get_reference_button = tk.Button(self.palette, text="get reference", command=self.show_reference_menu)
        self.get_reference_button.pack(padx=10, pady=10)
        self.pixel_length_label = tk.Label(self.palette, text=f"Length per pixel:\n{self.pixel_length} mm")
        self.pixel_length_label.pack(padx=10, pady=10)

        self.stage = tk.Label(self, background="#555")
        self.stage.pack(side="right", fill="both", anchor="nw", expand=True)

        self.reference_menu = DistanceMenu(self, self.working_directory)

    def start(self):
        if not self.is_running:
            self.start_button["text"] = "stop"
            self.start_button["background"] = "#f00"
            self.start_button["activebackground"] = "#c00"
            self.is_running = True
            threading.Thread(target=self.extract_positions).start()
            self.get_reference_button["state"] = self.working_directory_button["state"] = "disabled"
        else:
            self.stop()

    def stop(self):
        self.start_button["text"] = "start"
        self.start_button["background"] = "#090"
        self.start_button["activebackground"] = "#070"
        self.is_running = False
        self.get_reference_button["state"] = self.working_directory_button["state"] = "normal"

    def extract_positions(self):
        frames_per_second = 480  # captured with camera from huawei mate 20 lite
        time_per_frame = 1 / frames_per_second

        if not os.path.isdir(self.working_directory):
            os.makedirs(self.working_directory)
        video_paths = [os.path.join(self.working_directory, file) for file in os.listdir(self.working_directory) if
                       file.endswith(".mp4")]
        for video_path in video_paths:
            new_directory = video_path.replace(".mp4", "")
            os.mkdir(new_directory)
            new_video_path = os.path.join(new_directory, os.path.basename(video_path))
            os.rename(video_path, new_video_path)
            video_path = new_video_path
            if not self.is_running:
                break
            with open(video_path.replace(".mp4", ".json"), "w") as json_file:
                json_file.write(json.dumps({"x start": self.reference_menu.x_start}))
            with open(video_path.replace(".mp4", ".csv"), "w") as csv_file:
                csv_file.write("time [s],x [pixels],y [pixels],x [mm],y [mm],\n")
            cap = cv2.VideoCapture(video_path)
            frame_number = 0
            while self.is_running:
                success, image = cap.read()
                if not success:
                    break
                frame_number += 1
                image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                output_image = image.copy()
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _, image = cv2.threshold(image, 250, 255, cv2.THRESH_BINARY)
                contours, hierarchy = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                if contours:
                    contours = list(contours)
                    contours.sort(key=cv2.contourArea, reverse=True)
                    cv2.drawContours(output_image, contours, 0, (200, 0, 0), 1)
                    moments = cv2.moments(contours[0])
                    try:
                        center = (int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"]))
                        if center[0] > self.reference_menu.x_start:
                            with open(video_path.replace(".mp4", ".csv"), "a") as csv_file:
                                csv_file.write(f"{frame_number * time_per_frame},"
                                               f"{center[0]-self.reference_menu.x_start},{center[1]},"
                                               f"{(center[0]-self.reference_menu.x_start)*self.pixel_length},"
                                               f"{center[1]*self.pixel_length},\n")
                            cv2.circle(output_image, center, 2, (0, 255, 0), 3)
                        else:
                            cv2.circle(output_image, center, 2, (0, 0, 255), 3)
                    except ZeroDivisionError:
                        pass
                cv2.line(output_image, (self.reference_menu.x_start, 0),
                         (self.reference_menu.x_start, output_image.shape[0]), (0, 0, 255), 2)
                output_image = Image.fromarray(output_image)
                self.lock.acquire()
                self.current_frame = ImageTk.PhotoImage(image=output_image)
                self.stage.configure(image=self.current_frame)
                self.stage.image = self.current_frame
                self.lock.release()

        self.stop()

    def open_working_directory(self):
        new_directory = filedialog.askdirectory(initialdir=self.working_directory)
        if new_directory:
            self.working_directory = self.reference_menu.working_directory = new_directory
            self.working_directory_display["text"] = f"Selected working directory:\n{self.working_directory}"

    def show_reference_menu(self):
        if not self.reference_menu.is_active:
            self.stage.pack_forget()
            self.get_reference_button["text"] = "finish"
            self.reference_menu.show()
            self.start_button["state"] = "disabled"
        else:
            self.hide_reference_menu()

    def hide_reference_menu(self):
        if new_pixel_length := self.reference_menu.hide():
            self.pixel_length = new_pixel_length
        self.pixel_length_label["text"] = f"Length per pixel:\n{self.pixel_length} mm"
        self.stage.pack(side="right", fill="both", anchor="nw", expand=True)
        self.get_reference_button["text"] = "get reference"
        self.start_button["state"] = "normal"


class TracePlotter(Workspace):
    def __init__(self, root, change_workspace):
        super().__init__(root, "images/trace.png", "trace plotter", change_workspace)
        self.working_directory = "./Videos"
        self.is_running = False

        self.working_directory_button = tk.Button(self, text="select directory", command=self.open_working_directory)
        self.working_directory_button.pack(anchor="n", padx=10, pady=10)
        self.working_directory_display = tk.Label(self, text=f"Selected working directory:\n{self.working_directory}")
        self.working_directory_display.pack(padx=10, pady=10)
        self.start_button = tk.Button(self, text="start", background="#090", activebackground="#070",padx=10, pady=10,
                                      command=self.start)
        self.start_button.pack()

    def start(self):
        if not self.is_running:
            self.start_button["text"] = "stop"
            self.start_button["background"] = "#f00"
            self.start_button["activebackground"] = "#c00"
            self.is_running = True
            threading.Thread(target=self.plot_traces).start()
            self.working_directory_button["state"] = "disabled"
        else:
            self.stop()

    def stop(self):
        self.start_button["text"] = "start"
        self.start_button["background"] = "#090"
        self.start_button["activebackground"] = "#070"
        self.is_running = False
        self.working_directory_button["state"] = "normal"

    def plot_traces(self):
        video_directory_paths = [os.path.join(self.working_directory, video_directory) for video_directory
                                 in os.listdir(self.working_directory)
                                 if os.path.isdir(os.path.join(self.working_directory, video_directory))]
        for video_directory_path in video_directory_paths:
            if not self.is_running:
                break
            video_path = os.path.join(video_directory_path, os.path.basename(video_directory_path)) + ".mp4"
            plot_trace(video_path)
        self.stop()

    def open_working_directory(self):
        new_directory = filedialog.askdirectory(initialdir=self.working_directory)
        if new_directory:
            self.working_directory = new_directory
            self.working_directory_display["text"] = f"Selected working directory:\n{self.working_directory}"



# def get_distance(point1: tuple[int, int], point2: tuple[int, int]) -> float:
#     return round(math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2))
#
#
# def get_bbox_center(bbox: list[int]) -> tuple[int, int]:
#     return bbox[0] + round(bbox[2] / 2), bbox[1] + round(bbox[3] / 2)
#
#
# class Image:
#     scale = None  # Length per pixel.
#     origin = None
#
#     def __init__(self, pixels: np.ndarray, time: float):
#         self.pixels = pixels
#         self.time = time
#         self.bbox = None
#         self._line = []
#
#     def _draw_line(self, event, x, y, flags, param):
#         if event == cv2.EVENT_LBUTTONDBLCLK:
#             if len(self._line) < 2:
#                 self._line.append((x, y))
#             else:
#                 self._line = [(x, y)]
#
#     def set_scale(self):
#         print("Select two points by double clicking, and press enter to continue.")
#         cv2.namedWindow("img")
#         cv2.setMouseCallback("img", self._draw_line)
#         try:
#             while cv2.getWindowProperty("img", 1) != -1:
#                 cv2.imshow("img", self.numpy)
#                 if cv2.waitKey(33) == 13:  # If enter is pressed.
#                     break
#         except cv2.error:
#             pass
#         finally:
#             if len(self._line) != 2:
#                 print(f"Not exactly two points were selected! Selected: {self._line}.")
#                 cv2.destroyAllWindows()
#                 exit(0)
#
#             cv2.imshow("img", self.numpy)
#             cv2.waitKey(1)
#             distance = get_distance(self._line[0], self._line[1])
#             cm = float(input("Enter length of the marked line in cm: "))
#             Image.scale = cm / distance  # Changes class attribute!
#
#             cv2.destroyAllWindows()
#
#     @property
#     def center_of_mass(self) -> tuple:
#         return get_bbox_center(self.bbox)
#
#     def get_elongation(self, direction: str) -> float:
#         if direction.lower() == 'x':
#             return (self.center_of_mass[0] - self.origin[0]) * self.scale
#         elif direction.lower() == 'y':
#             return (self.center_of_mass[1] - self.origin[1]) * self.scale
#         else:
#             raise ValueError(f"Direction '{direction}' is invalid; must be 'x' or 'y'!")
#
#     @staticmethod
#     def _select_point(event, x, y, flags, param):
#         if event == cv2.EVENT_LBUTTONDBLCLK:
#             Image.origin = (x, y)
#
#     def set_origin(self):
#         print("Select origin by double clicking, and press enter to continue.")
#         cv2.namedWindow("img")
#         cv2.setMouseCallback("img", self._select_point)
#         try:
#             while cv2.getWindowProperty("img", 1) != -1:
#                 cv2.imshow("img", self.numpy)
#                 if cv2.waitKey(33) == 13:  # If enter is pressed.
#                     break
#         except cv2.error:
#             pass
#         finally:
#             cv2.destroyAllWindows()
#             if not self.origin:
#                 print("No origin was selected!")
#                 exit(0)
#
#     @property
#     def numpy(self):
#         pixels = self.pixels.copy()
#         #  Apply transformations on the image.
#         if self.bbox:
#             pixels = cv2.rectangle(pixels, rec=self.bbox, color=(255, 0, 0))
#             pixels = cv2.circle(pixels, self.center_of_mass, 2, color=(255, 0, 0), thickness=2)
#             pixels = cv2.putText(pixels, f"({round(self.get_elongation('x'), 1)}|{round(self.get_elongation('y'), 1)})",
#                                  self.center_of_mass, cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 0, 0), 1)
#         if len(self._line) == 2:
#             pixels = cv2.line(pixels, self._line[0], self._line[1], (255, 0, 0), 3)
#         if self.origin:
#             length = 3
#             top_point = (self.origin[0], self.origin[1] + length)
#             bottom_point = (self.origin[0], self.origin[1] - length)
#             right_point = (self.origin[0] + length, self.origin[1])
#             left_point = (self.origin[0] - length, self.origin[1])
#             pixels = cv2.line(pixels, top_point, bottom_point, (255, 0, 0), 1)
#             pixels = cv2.line(pixels, left_point, right_point, (255, 0, 0), 1)
#         return pixels
#
#     @center_of_mass.setter
#     def center_of_mass(self, value):
#         self._center_of_mass = value
#
#
# class Video:
#     fps: float = 100.
#
#     def __init__(self, path: str):  # Loads whole video into memory!
#         time_per_image = 1. / self.fps
#         self.images = []
#         cap = cv2.VideoCapture(path)
#         success = True
#         time = 0
#         while success:
#             success, image = cap.read()
#             if success:
#                 self.images.append(Image(image, time))
#                 time += time_per_image
#
#     def __iter__(self):
#         for image in self.images:
#             yield image
#
#     def __getitem__(self, item):
#         return self.images[item]
#
#     def __len__(self):
#         return self.images.get(cv2.CAP_PROP_FRAME_COUNT)
#
#
# class BBoxTracker(Workspace):
#     def __init__(self, root, change_workspace):
#         super().__init__(root, "images/box.png", "bbox tracker (beta)", change_workspace)
#         self.video_path = ""
#         self.is_running = False
#
#         self.palette = tk.Frame(self, background="#00f")
#         self.video_path_display = tk.Label(self.palette,
#                                            text=f"Selected working directory:\n{self.video_path}")
#         self.video_path_button = tk.Button(self.palette, text="select directory", command=self.open_video)
#         self.start_button = tk.Button(self.palette, text="start", command=..., background="#090",
#                                       activebackground="#070", padx=10, pady=10)
#
#         self.palette.pack(side="left", anchor="nw", fill="both", expand=False)
#         self.video_path_display.pack(padx=10, pady=10)
#         self.video_path_button.pack(anchor="n", padx=10, pady=10)
#         self.start_button.pack()
#
#     def open_video(self):
#         new_path = filedialog.askopenfilename(initialdir="Videos", filetypes=[("MP4 files", "*.mp4")])
#         if new_path:
#             self.video_path = new_path
#             self.video_path_display["text"] = f"Selected working directory:\n{self.video_path}"
#
#     def extract_positions(self):
#         video = Video(self.video_path)
#         tracker = cv2.TrackerMIL.create()
#
#         video[0].set_scale()
#         video[-1].set_origin()
#
#         # Initialize the tracker.
#         image = video[0]
#         bbox = cv2.selectROI("img", image.numpy, showCrosshair=True)
#         tracker.init(image.pixels, bbox)
#
#         with open(self.video_path_button.replace(".mp4", ".csv"), 'w', newline='') as csv_file:
#             csv_writer = csv.writer(csv_file, delimiter=',')
#             csv_writer.writerow(["time [s]", "x elongation [cm]", "y elongation [cm]"])
#             try:
#                 for image in video:
#                     success, bbox = tracker.update(image.pixels)
#                     if success and cv2.getWindowProperty("img", 1) != -1:
#                         image.bbox = bbox
#                         csv_writer.writerow([image.time, image.get_elongation('x'), image.get_elongation('y')])
#                     else:
#                         break
#                     cv2.imshow("img", image.numpy)
#                     cv2.waitKey(1)
#             except cv2.error:
#                 print("Program was closed by the user.")
#             finally:
#                 cv2.destroyAllWindows()
#

class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Tracker")
        self.icon = tk.PhotoImage(file="images/crosshair.png")
        self.iconphoto(False, self.icon)

        workspaces = [
            BrightnessTracker(self, self.change_workspace),
            TracePlotter(self, self.change_workspace)
        ]
        workspaces.insert(0, Home(self, self.change_workspace, workspaces))
        self.workspaces = workspaces
        self.active_workspace = 0

        self.workspaces[self.active_workspace].pack(fill="x")

    def change_workspace(self, new_workspace: int):
        self.workspaces[self.active_workspace].pack_forget()
        self.workspaces[new_workspace].pack(fill="x")
        self.active_workspace = new_workspace


def main():
    root = App()
    root.mainloop()


if __name__ == "__main__":
    main()
