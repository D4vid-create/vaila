# --------------------------------------------------
# Script Name: getpixelvideo.py
# Version: 0.0.7
# Last Updated: August 9, 2024
# Description: A tool for marking and saving pixel
# coordinates in a video with zoom functionality. 
# Now allows loading and displaying pre-marked points from a CSV file.
# --------------------------------------------------
# Usage Instructions:
# - Press 'Space' to toggle play/pause of the video.
# - Press 'Escape' to close the video and exit the application.
# - Press 'A' or 'Left Arrow' to go to the previous frame.
# - Press 'D' or 'Right Arrow' to go to the next frame.
# - Press 'W' or 'Up Arrow' to jump to the last frame.
# - Press 'S' or 'Down Arrow' to jump to the first frame.
# - Press 'Ctrl m' to zoom in on the video.
# - Press 'Ctrl l' to zoom out on the video.
# - Press 'Ctrl h' to reset the zoom.
# - Left-click to mark a point on the video.
# - Right-click to remove the last marked point.
# - Optionally, load a CSV with pre-marked points.
# --------------------------------------------------

import cv2
import os
import pandas as pd
from tkinter import filedialog, Tk, Toplevel, Scale, HORIZONTAL, Button, messagebox
import numpy as np

def show_help_message():
    root = Tk()
    root.withdraw()
    messagebox.showinfo(
        "Help",
        "This tool allows you to mark and save pixel coordinates in a video.\n\n"
        "Instructions:\n"
        "- Press 'Space' to toggle play/pause of the video.\n"
        "- Press 'Escape' to close the video and exit the application.\n"
        "- Press 'A' or 'Left Arrow' to go to the previous frame.\n"
        "- Press 'D' or 'Right Arrow' to go to the next frame.\n"
        "- Press 'W' or 'Up Arrow' to jump to the last frame.\n"
        "- Press 'S' or 'Down Arrow' to jump to the first frame.\n"
        "- Press 'Ctrl m' to zoom in on the video.\n"
        "- Press 'Ctrl l' to zoom out on the video.\n"
        "- Press 'Ctrl h' to reset the zoom.\n"
        "- Left-click to mark a point on the video.\n"
        "- Right-click to remove the last marked point.\n\n"
        "Note: To control the video with zoom and player, you must select the control window.\n\n"
        "For more detailed help, click the link below:\n"
        "docs/help.html",
        icon='info'
    )

def get_video_path():
    root = Tk()
    root.withdraw()
    video_path = filedialog.askopenfilename(title="Select Video File", filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
    return video_path

def load_existing_coordinates(video_path):
    root = Tk()
    root.withdraw()
    csv_path = filedialog.askopenfilename(title="Select CSV File with Pre-marked Points", filetypes=[("CSV Files", "*.csv")])
    if csv_path:
        df = pd.read_csv(csv_path)

        # Identify the frame column dynamically
        frame_column = df.columns[0]
        coordinates = {}

        for _, row in df.iterrows():
            frame_num = int(row[frame_column])
            points = []
            for i in range(1, len(row) // 2):
                x = row.get(f'p{i}_x')
                y = row.get(f'p{i}_y')
                if pd.notna(x) and pd.notna(y):
                    points.append((int(x), int(y)))
            coordinates[frame_num] = points
        return coordinates
    return None

def save_coordinates(video_path, coordinates, total_frames):
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    video_dir = os.path.dirname(video_path)
    output_file = os.path.join(video_dir, f"{base_name}_getpixel.csv")

    columns = ['frame'] + [f'p{i}_{c}' for i in range(1, 101) for c in ['x', 'y']]
    df = pd.DataFrame(np.nan, index=range(total_frames), columns=columns)
    df['frame'] = df.index

    for frame_num, points in coordinates.items():
        for i, (x, y) in enumerate(points):
            df.at[frame_num, f'p{i+1}_x'] = x
            df.at[frame_num, f'p{i+1}_y'] = y

    # Determine the last marked point
    last_point = 0
    for frame_num, points in coordinates.items():
        if points:
            last_point = max(last_point, len(points))

    # Remove columns beyond the last marked point
    if last_point < 100:
        df = df.iloc[:, :1 + 2 * last_point]

    df.to_csv(output_file, index=False)
    print(f"Coordinates saved to {output_file}")

def get_pixel_coordinates(video_path, initial_coordinates=None):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0
    coordinates = initial_coordinates if initial_coordinates else {i: [] for i in range(total_frames)}
    paused = True
    frame = None
    zoom_level = 1.0

    def draw_point(frame, x, y, num):
        outer_color = (0, 0, 0)  # Black for the border
        inner_color = (0, 255, 0)  # Green for the inner point
        outer_radius = 7  # Radius for the border circle
        inner_radius = 5  # Radius for the inner circle
        thickness = -1  # Filled circle

        # Draw the outer circle (border)
        cv2.circle(frame, (x, y), outer_radius, outer_color, thickness)
        # Draw the inner circle (point)
        cv2.circle(frame, (x, y), inner_radius, inner_color, thickness)
        cv2.putText(frame, f'{num}', (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, inner_color, 1)

    def apply_zoom(frame, zoom_level):
        height, width = frame.shape[:2]
        new_width = int(width * zoom_level)
        new_height = int(height * zoom_level)
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

        # Center the frame
        if zoom_level > 1.0:
            x_offset = (new_width - width) // 2
            y_offset = (new_height - height) // 2
            frame = frame[y_offset:y_offset+height, x_offset:x_offset+width]

        return frame

    def click_event(event, x, y, flags, param):
        nonlocal frame
        if event == cv2.EVENT_LBUTTONDOWN:
            coordinates[frame_count].append((x, y))
            draw_point(frame, x, y, len(coordinates[frame_count]))
            cv2.imshow('Frame', frame)
        elif event == cv2.EVENT_RBUTTONDOWN:
            if coordinates[frame_count]:
                coordinates[frame_count].pop()
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
                ret, frame = cap.read()
                if ret:
                    frame = apply_zoom(frame, zoom_level)
                    for i, point in enumerate(coordinates[frame_count]):
                        draw_point(frame, point[0], point[1], i + 1)
                    cv2.imshow('Frame', frame)

    def update_frame(new_frame_count):
        nonlocal frame_count, frame, paused
        frame_count = new_frame_count
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        ret, frame = cap.read()
        if ret:
            frame = apply_zoom(frame, zoom_level)
            for i, point in enumerate(coordinates[frame_count]):
                draw_point(frame, point[0], point[1], i + 1)
            cv2.imshow('Frame', frame)
            window.title(f'Frame {frame_count}')
        paused = True

    def on_key(event):
        nonlocal paused, zoom_level
        key = event.keysym.lower()
        if key == 'space':
            toggle_play_pause()
        elif key == 'escape':
            cap.release()
            cv2.destroyAllWindows()
            window.quit()
        elif key in ['a', 'left']:
            update_frame(max(frame_count - 1, 0))
        elif key in ['d', 'right']:
            update_frame(min(frame_count + 1, total_frames - 1))
        elif key in ['w', 'up']:
            update_frame(total_frames - 1)
        elif key in ['s', 'down']:
            update_frame(0)
        elif event.state == 4:  # Ctrl is pressed
            if key == 'm':  # Ctrl m
                zoom_level *= 1.2
                update_frame(frame_count)
            elif key == 'l':  # Ctrl l
                zoom_level /= 1.2
                update_frame(frame_count)
            elif key == 'h':  # Ctrl h
                zoom_level = 1.0
                update_frame(frame_count)
        slider.set(frame_count)

    def play_video():
        nonlocal frame_count, frame
        if not paused:
            frame_count += 1
            if frame_count >= total_frames:
                frame_count = 0
            ret, frame = cap.read()
            if ret:
                frame = apply_zoom(frame, zoom_level)
                for i, point in enumerate(coordinates[frame_count]):
                    draw_point(frame, point[0], point[1], i + 1)
                cv2.imshow('Frame', frame)
                window.title(f'Frame {frame_count}')
                slider.set(frame_count)
            window.after(30, play_video)  # Adjust delay as needed
        else:
            window.after(30, play_video)

    def toggle_play_pause():
        nonlocal paused
        paused = not paused

    def close_video():
        cap.release()
        cv2.destroyAllWindows()
        window.quit()

    root = Tk()
    root.withdraw()

    window = Toplevel(root)
    window.title('Frame Viewer')
    window.bind('<KeyPress>', on_key)
    window.geometry('800x100')

    slider = Scale(window, from_=0, to=total_frames-1, orient=HORIZONTAL, command=lambda pos: update_frame(int(pos)))
    slider.pack(fill='x', expand=True)

    play_pause_button = Button(window, text="Next Frame", command=toggle_play_pause)
    play_pause_button.pack(side='left')

    close_button = Button(window, text="Close Video", command=close_video)
    close_button.pack(side='right')

    cv2.namedWindow('Frame')
    cv2.setMouseCallback('Frame', click_event)

    update_frame(0)  # Start with the first frame paused

    window.after(30, play_video)
    window.mainloop()

    return coordinates, total_frames

def main():
    show_help_message()  # Show the help message and open the help file
    video_path = get_video_path()
    if video_path:
        root = Tk()
        root.withdraw()
        load_csv = messagebox.askyesno("Load CSV", "Do you want to load an existing CSV file with pre-marked points?")
        if load_csv:
            initial_coordinates = load_existing_coordinates(video_path)
            coordinates, total_frames = get_pixel_coordinates(video_path, initial_coordinates)
        else:
            coordinates, total_frames = get_pixel_coordinates(video_path)
        save_coordinates(video_path, coordinates, total_frames)

if __name__ == "__main__":
    main()
