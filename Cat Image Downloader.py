import os
import tkinter as tk
import json
import logging
import flickrapi
import queue
import requests
import threading
from tkinter import messagebox, ttk
from flickrapi import FlickrError
from tkinter import filedialog
from queue import Queue, Empty
from dotenv import find_dotenv, load_dotenv
from threading import Thread 
 

progress_bar = None
images_entry = None
folder_selected = ""
num_images_label = None

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('cat_image_downloader.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
logger.addHandler(file_handler)

# Find the .env file
dotenv_path = find_dotenv()
if dotenv_path is not None:
    load_dotenv(dotenv_path)
else:
    logger.info("Could not find .env file")

# Flickr API setup
FLICKR_API_KEY = str(os.getenv('FLICKR_API_KEY'))
API_SECRET = str(os.getenv('FLICKR_API_SECRET'))
logger.info(f"FLICKR_API_KEY: {FLICKR_API_KEY}")
logger.info(f"API_SECRET: {API_SECRET}")

# Create an instance of the flickrapi module
try:
    flickr = flickrapi.FlickrAPI(FLICKR_API_KEY, API_SECRET, format='parsed-json')
    logger.info("Successfully created flickr instance")
except FlickrError as e:
    logger.error(f"Flickr API Error: {e}")
    print(f"Flickr API Error: {e}")

serial_number = 0
folder_selected = ""
queue = Queue()


def select_folder():
    global folder_selected
    folder_selected = filedialog.askdirectory()

def get_starting_serial_number():
    global folder_selected  # Declare folder_selected as global
    url_file_path = os.path.join(folder_selected, 'image_urls.txt')
    last_serial_number = 0

    if os.path.exists(url_file_path):
        with open(url_file_path, 'r') as url_file:
            lines = url_file.readlines()
            if lines:
                last_line = lines[-1]
                try:
                    last_serial_number = int(last_line.split(",")[0].split(":")[1].strip())
                except ValueError:
                    pass

    return last_serial_number + 1

def start_download_thread():
    thread = Thread(target=start_download)
    thread.start()



def start_download():
    global folder_selected, serial_number, progress_bar  # Add progress_bar here
    
    if not folder_selected:
        messagebox.showerror("Error", "Please select a folder.")
        return

    serial_number = get_starting_serial_number()
    number_of_images = int(images_entry.get())
    progress_bar["maximum"] = number_of_images  # Set the maximum value for the progress bar

    
    if not folder_selected:
        messagebox.showerror("Error", "Please select a folder.")
        return

    serial_number = get_starting_serial_number()
    number_of_images = int(images_entry.get())

    images_per_page = 500
    pages_needed = (number_of_images + images_per_page - 1) // images_per_page
    remaining_images = number_of_images

    print(f"Starting download... Number of images to download: {number_of_images}")

    for page in range(1, pages_needed + 1):
        images_to_fetch = min(remaining_images, images_per_page)
        try:
            photos = flickr.photos.search(
                text='cat',
                license='1,2,3,4,5,6',
                per_page=str(images_to_fetch),
                page=page
            )
        except FlickrError as e:
            logger.error(f"Flickr API Error: {e}")
            print(f"Flickr API Error: {e}")
            return

        total_images = len(photos['photos']['photo'])
        print(f"Total images in this batch: {total_images}")

        with open(os.path.join(folder_selected, 'image_urls.txt'), 'a') as url_file:
            for i, photo in enumerate(photos['photos']['photo']):
                try:
                    url = f"https://farm{photo['farm']}.staticflickr.com/{photo['server']}/{photo['id']}_{photo['secret']}.jpg"
                    response = requests.get(url)
                    if response.status_code != 200:
                        logger.warning(f"Failed to download image from URL: {url}")
                        continue

                    url_file.write(f"Serial Number: {serial_number}, URL: {url}\n")

                    with open(os.path.join(folder_selected, f'cat_{serial_number}.jpg'), 'wb') as file:
                        file.write(response.content)
                        serial_number += 1

                    queue.put(number_of_images - (page * images_per_page + i + 1))
                    remaining_images -= 1

                    if serial_number >= 100:  # Add download limit of 100 images
                        logger.info("Download limit of 100 images reached.")
                        queue.put(-1)
                        return

                except requests.exceptions.RequestException as e:
                    logger.error(f"Network Error: {e}")

    logger.info("Download finished!")
    queue.put(-1)


def check_queue(queue):
    try:
        remaining_images = queue.get_nowait()
        if remaining_images >= 0:
            countdown_label.config(text=f"Images Remaining: {remaining_images}")
            root.after(100, check_queue, queue)
        else:
            countdown_label.config(text="")
            select_button.config(state=tk.NORMAL)
            download_button.config(state=tk.NORMAL)
            num_images_label.config(text="")
    except Empty:
        root.after(100, check_queue, queue)


def get_starting_serial_number():
    global folder_selected
    url_file_path = os.path.join(folder_selected, 'image_urls.txt')
    last_serial_number = 0

    if os.path.exists(url_file_path):
        with open(url_file_path, 'r') as url_file:
            lines = url_file.readlines()
            if lines:
                last_line = lines[-1]
                try:
                    last_serial_number = int(last_line.split(",")[0].split(":")[1].strip())
                except ValueError:
                    pass

    return last_serial_number + 1

root = tk.Tk()
root.title('Cat Images Downloader')

select_button = tk.Button(root, text="Select Folder", command=select_folder)
select_button.pack(pady=10)

# Initialize images_entry
images_entry = tk.Entry(root)
images_entry.pack(pady=5)

# Initialize Progress Bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=10)

download_button = tk.Button(root, text="Start Download", command=start_download_thread)
download_button.pack(pady=10)

countdown_label = tk.Label(root, text="")
countdown_label.pack()

root.mainloop()


