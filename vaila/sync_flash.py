# sync_flash.py

import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageTk


def get_sync_info_flash(video_files: List[str]) -> Tuple[List[List], str, int, int]:
    """
    Perform flash-based synchronization and return synchronization data.

    :param video_files: List of video filenames.
    :return: Tuple containing sync_data, main_video, frame_initial, frame_final.
    """

    sync_data = []

    class FlashSyncDialog(tk.Toplevel):
        def __init__(self, master, video_files):
            super().__init__(master)
            self.video_files = video_files
            self.sync_data = []
            self.bbox_data = {}
            self.main_video = None
            self.frame_initial = 0
            self.frame_final = 0

            self.title("Flash-Based Video Synchronization")
            self.geometry("800x600")

            self.create_widgets()

        def create_widgets(self):
            tk.Label(
                self, text="Flash-Based Video Synchronization", font=("Arial", 16)
            ).pack(pady=10)

            # Button to select bounding boxes for each video
            tk.Button(
                self,
                text="Select Bounding Boxes",
                command=self.select_bounding_boxes,
                width=30,
                height=2
            ).pack(pady=10)

            # Button to proceed to main video selection
            tk.Button(
                self,
                text="Select Main Video and Frame Range",
                command=self.select_main_video,
                width=30,
                height=2
            ).pack(pady=10)

            # Button to finalize synchronization
            tk.Button(
                self,
                text="Finalize Synchronization",
                command=self.finalize_sync,
                width=30,
                height=2
            ).pack(pady=10)

        def select_bounding_boxes(self):
            for video in self.video_files:
                bbox, _, _ = self.draw_bounding_box(video)
                self.bbox_data[video] = bbox
            messagebox.showinfo("Info", "Bounding boxes selected for all videos.")

        def draw_bounding_box(self, video_file: str) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[int], Optional[int]]:
            """
            Allow the user to draw a bounding box on the first frame of the video.

            :param video_file: The video filename.
            :return: Bounding box coordinates as (x, y, w, h), min_brightness, max_brightness.
            """
            cap = cv2.VideoCapture(video_file)
            if not cap.isOpened():
                messagebox.showerror("Error", f"Cannot open video file: {video_file}")
                return None, None, None

            ret, frame = cap.read()
            cap.release()
            if not ret:
                messagebox.showerror("Error", f"Cannot read frame from video: {video_file}")
                return None, None, None

            # Resize frame for display if it's too large
            max_dim = 800
            height, width = frame.shape[:2]
            scaling_factor = min(max_dim / width, max_dim / height, 1)
            display_width = int(width * scaling_factor)
            display_height = int(height * scaling_factor)
            resized_frame = cv2.resize(frame, (display_width, display_height))

            bbox = {}
            min_brightness = max_brightness = None

            # Create a Tkinter window for bounding box selection
            bbox_window = tk.Toplevel()
            bbox_window.title(f"Select Bounding Box for {video_file}")
            bbox_window.grab_set()  # Make it modal

            canvas = tk.Canvas(bbox_window, width=display_width, height=display_height)
            canvas.pack()

            # Convert the image to Tkinter-compatible format
            image = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            img = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img_pil)
            canvas.create_image(0, 0, anchor='nw', image=imgtk)

            rect = None
            start_x = start_y = end_x = end_y = 0

            def on_button_press(event):
                nonlocal start_x, start_y
                start_x = event.x
                start_y = event.y

            def on_move_press(event):
                nonlocal rect
                current_x, current_y = event.x, event.y
                if rect:
                    canvas.delete(rect)
                rect = canvas.create_rectangle(start_x, start_y, current_x, current_y, outline='red')

            def on_button_release(event):
                nonlocal rect, bbox, min_brightness, max_brightness
                end_x, end_y = event.x, event.y
                x1, y1 = start_x, start_y
                x2, y2 = end_x, end_y
                x = int(min(x1, x2) / scaling_factor)
                y = int(min(y1, y2) / scaling_factor)
                w = int(abs(x2 - x1) / scaling_factor)
                h = int(abs(y2 - y1) / scaling_factor)
                bbox = (x, y, w, h)

                # Calculate brightness statistics within the bounding box
                roi = frame[y:y+h, x:x+w]
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                min_brightness = int(gray_roi.min())
                max_brightness = int(gray_roi.max())

                bbox_window.destroy()

            canvas.bind("<ButtonPress-1>", on_button_press)
            canvas.bind("<B1-Motion>", on_move_press)
            canvas.bind("<ButtonRelease-1>", on_button_release)

            # Instructions
            tk.Label(bbox_window, text="Draw a rectangle around the flasher and release the mouse button.").pack()

            bbox_window.wait_window()  # Wait until the bounding box window is closed

            if not bbox:
                messagebox.showwarning("Warning", f"No bounding box selected for {video_file}. All frames will be processed.")
                return None, None, None

            return bbox, min_brightness, max_brightness

        def select_main_video(self):
            """
            Allows the user to select the main video and input frame_initial and frame_final.
            """
            self.withdraw()
            main_dialog = MainVideoDialog(self, self.video_files)
            self.main_video, self.frame_initial, self.frame_final = main_dialog.get_selection()
            self.deiconify()

        def finalize_sync(self):
            """
            Perform synchronization based on selected bounding boxes and main video.
            """
            if not self.main_video:
                messagebox.showerror("Error", "Main video not selected.")
                return

            # Detect flash frames for all videos
            flash_info = {}
            for video in self.video_files:
                video_path = os.path.join(os.getcwd(), video)
                bbox = self.bbox_data.get(video, None)
                flashes = detect_flash_frames(video_path, min_brightness=180, bbox=bbox)
                flash_info[video] = flashes

            reference_flashes = flash_info.get(self.main_video, [])
            if not reference_flashes:
                messagebox.showerror("Error", f"No flash frames detected in the reference video: {self.main_video}")
                return

            frame_initial = reference_flashes[0]
            frame_final = frame_initial + 100  # Adjust as needed

            for video, flashes in flash_info.items():
                if video == self.main_video:
                    sync_data.append([video, f"{os.path.splitext(video)[0]}_0_{frame_initial}_{frame_final}.mp4", frame_initial, frame_final])
                    continue

                if not flashes:
                    print(f"Warning: No flash frames detected in {video}. Setting keyframe to 0.")
                    sync_data.append([video, f"{os.path.splitext(video)[0]}_0_{frame_initial}_{frame_final}.mp4", 0, 0])
                    continue

                # Find the first flash after at least 10 non-flash frames
                offset = reference_flashes[0] - flashes[0]
                initial_frame = frame_initial - offset
                final_frame = frame_final - offset
                sync_data.append([video, f"{os.path.splitext(video)[0]}_{offset}_{initial_frame}_{final_frame}.mp4", initial_frame, final_frame])

            self.destroy()

    class MainVideoDialog(tk.Toplevel):
        def __init__(self, master, video_files):
            super().__init__(master)
            self.video_files = video_files
            self.main_video = None
            self.frame_initial = 0
            self.frame_final = 0

            self.title("Select Main Video and Frame Range")
            self.geometry("600x400")

            self.create_widgets()

        def create_widgets(self):
            tk.Label(
                self, text="Select the Main Video for Synchronization", font=("Arial", 14)
            ).pack(pady=10)

            # Listbox to select main video
            self.main_video_listbox = tk.Listbox(self, selectmode=tk.SINGLE, width=50)
            self.main_video_listbox.pack(pady=10)
            for video in self.video_files:
                self.main_video_listbox.insert(tk.END, video)

            # Frame inputs
            frame = tk.Frame(self)
            frame.pack(pady=10)

            tk.Label(frame, text="Start Frame:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
            self.start_frame_entry = tk.Entry(frame, width=15)
            self.start_frame_entry.grid(row=0, column=1, padx=5, pady=5)

            tk.Label(frame, text="End Frame:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
            self.end_frame_entry = tk.Entry(frame, width=15)
            self.end_frame_entry.grid(row=1, column=1, padx=5, pady=5)

            # OK button
            tk.Button(self, text="OK", command=self.on_ok, width=20).pack(pady=20)

        def on_ok(self):
            selected = self.main_video_listbox.curselection()
            if not selected:
                messagebox.showerror("Error", "Please select the main video.")
                return

            try:
                frame_initial = int(self.start_frame_entry.get())
                frame_final = int(self.end_frame_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Please enter valid start and end frames.")
                return

            self.main_video = self.video_files[selected[0]]
            self.frame_initial = frame_initial
            self.frame_final = frame_final
            self.destroy()

        def get_selection(self):
            self.wait_window()
            return self.main_video, self.frame_initial, self.frame_final


    # Initialize main Tkinter window
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Create and display the synchronization dialog
    sync_dialog = FlashSyncDialog(root, video_files)
    sync_dialog.mainloop()

    # After the dialog is closed, retrieve the synchronization data
    return sync_dialog.sync_data, sync_dialog.main_video, sync_dialog.frame_initial, sync_dialog.frame_final


def detect_flash_frames(video_path: str, min_brightness: int = 180, bbox: Optional[Tuple[int, int, int, int]] = None) -> List[int]:
    """
    Detect flash frames based on two methods:
    1. Brightness cutoff for top 10 pixels.
    2. Average brightness cutoff for top 10 pixels.

    If both methods agree, act accordingly.
    If there's a discrepancy, display ROI and prompt user for confirmation.

    :param video_path: Path to the video file.
    :param min_brightness: Unused parameter for now.
    :param bbox: Bounding box (x, y, w, h) to focus on a specific region.
    :return: List of frame indices where flashes are detected.
    """
    print(f"Starting flash detection for: {os.path.basename(video_path)}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video file: {video_path}")
        return []

    flash_frames = []
    frame_idx = 0
    non_flash_count = 0
    min_non_flash = 10  # Minimum number of non-flash frames before a flash

    while True:
        ret, frame = cap.read()  # ret: bool, frame: numpy.ndarray
        if not ret:
            break

        if bbox:
            x, y, w, h = bbox  # x: int, y: int, w: int, h: int
            roi = frame[y:y+h, x:x+w]  # roi: numpy.ndarray
        else:
            roi = frame  # roi: numpy.ndarray

        # **Display the ROI Image Every 15 Frames**
        if frame_idx % 15 == 0:
            # Check if ROI has valid size
            if roi.size != 0:
                cv2.imshow('ROI', roi)  # Display the ROI in a window titled 'ROI'

                # **Convert ROI to Grayscale and Sort Pixels**
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)  # Convert ROI to grayscale
                pixels = gray.flatten()  # Flatten the grayscale image to a 1D array
                sorted_pixels = sorted(pixels, reverse=True)  # Sort pixel values in descending order

                # **Extract Top 10 Brightest Pixels**
                top_10_pixels = sorted_pixels[:10] if len(sorted_pixels) >= 10 else sorted_pixels
                if len(top_10_pixels) < 10:
                    print(f"Frame {frame_idx}: Not enough pixels to perform flash detection.")
                    cv2.destroyWindow('ROI')
                    frame_idx += 1
                    continue

                # **Method 1: Check if ALL Top 10 Pixels > 240**
                method1_flash = all(pixel > 240 for pixel in top_10_pixels)

                # **Method 2: Check if Average of Top 10 Pixels > 245**
                average_brightness_10 = sum(top_10_pixels) / len(top_10_pixels)
                method2_flash = average_brightness_10 > 245

                # **Print Metrics**
                print(f"Frame {frame_idx}: Top 10 pixel values: {top_10_pixels}")
                print(f"Frame {frame_idx}: Average brightness of top 10 pixels: {average_brightness_10:.2f}")
                print(f"Frame {frame_idx}: Brightness cutoff (240) and Average cutoff (245)")

                # **Determine Flash Detection**
                if method1_flash and method2_flash:
                    # Both methods agree on flash detection
                    flash_frames.append(frame_idx)
                    non_flash_count = 0
                    print(f"Flash detected at frame {frame_idx} in {os.path.basename(video_path)}")
                elif not method1_flash and not method2_flash:
                    # Both methods agree on no flash
                    non_flash_count += 1
                else:
                    # Discrepancy detected between methods
                    print("Discrepancy detected between flash detection methods.")
                    print(f"Frame {frame_idx}: Top 10 pixel values: {top_10_pixels}")
                    print(f"Frame {frame_idx}: Average brightness of top 10 pixels: {average_brightness_10:.2f}")
                    print(f"Frame {frame_idx}: Method 1 (All > 240): {'Yes' if method1_flash else 'No'}")
                    print(f"Frame {frame_idx}: Method 2 (Avg > 245): {'Yes' if method2_flash else 'No'}")

                    # **Prompt User for Confirmation**
                    user_confirm = prompt_user(frame_idx, top_10_pixels, average_brightness_10)
                    if user_confirm:
                        flash_frames.append(frame_idx)
                        print(f"User confirmed flash at frame {frame_idx}.")
                        non_flash_count = 0
                    else:
                        print(f"User did not confirm flash at frame {frame_idx}.")
                        non_flash_count += 1

                # **Pause Execution Until User Continues**
                print("Press SPACE to continue or 'q' to quit.")
                while True:
                    key = cv2.waitKey(1) & 0xFF  # Wait for 1 ms
                    if key == ord('q'):
                        print("Exiting flash detection.")
                        cap.release()
                        cv2.destroyAllWindows()
                        return flash_frames
                    elif key == ord(' '):
                        print("Continuing to next frames...\n")
                        break
            else:
                print(f"Frame {frame_idx}: Invalid ROI size. Skipping display.")

        frame_idx += 1  # Move to the next frame

    cap.release()
    cv2.destroyAllWindows()  # Close all OpenCV windows
    print(f"Finished flash detection for: {os.path.basename(video_path)}. Flash frames found: {len(flash_frames)}")
    return flash_frames  # Return the list of detected flash frames

def prompt_user(frame_idx: int, top_pixels: List[int], average_brightness: float) -> bool:
    """
    Prompt the user to confirm if a frame is a flash when there is a discrepancy between methods.

    :param frame_idx: The index of the frame being evaluated.
    :param top_pixels: List of the top 10 brightest pixel values.
    :param average_brightness: The average brightness of the top 10 pixels.
    :return: True if user confirms flash, False otherwise.
    """
    # Create a new Tkinter window
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Prepare the message
    message = (
        f"Discrepancy detected in flash detection for frame {frame_idx}.\n\n"
        f"Top 10 pixel values: {top_pixels}\n"
        f"Average brightness of top 10 pixels: {average_brightness:.2f}\n\n"
        f"Method 1 (All > 240): {'Yes' if all(pixel > 240 for pixel in top_pixels) else 'No'}\n"
        f"Method 2 (Avg > 245): {'Yes' if average_brightness > 245 else 'No'}\n\n"
        f"Do you confirm this frame as a flash?"
    )

    # Prompt the user with Yes and No buttons
    result = messagebox.askyesno("Flash Confirmation", message)

    root.destroy()  # Close the Tkinter window

    return result
