# usr/bin/env python3

import tkinter as tk
from tkinter import filedialog
import cv2
import os
import threading
from PIL import Image, ImageTk
import math
from functools import partial


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
        for video_path in [os.path.join(self.working_directory, file) for file in os.listdir(self.working_directory) if
                           file.endswith(".mp4")]:
            if not self.is_running:
                break
            with open(video_path.replace(".mp4", ".csv"), "w") as csv_file:
                csv_file.write("time [s],x [pixels],y [pixels], x [mm], y [mm]\n")
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


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Tracker")
        self.icon = tk.PhotoImage(file="images/crosshair.png")
        self.iconphoto(False, self.icon)

        workspaces = [
            BrightnessTracker(self, self.change_workspace)
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
