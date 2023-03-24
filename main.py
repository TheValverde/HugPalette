import requests
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading
import shutil
import os
import sys
from datetime import datetime
from io import BytesIO
import openai
import json
from config import OPENAI_API_KEY, DEEPAI_API_KEY

openai_response_received = threading.Event()

def get_hexcodes_from_chatgpt(description,):
    openai.api_key = OPENAI_API_KEY
    global gpt_hexcodes_json, prompt
    #I wonder if doing {description} is what is breaking my code.
    #I think it is. I need to figure out how to get the description into the prompt.
    prompt = f"You are an assistant that creates color palettes based on the input you are given. Your responses are only given in a json format and only have hexcodes. You will not include any label in the json output, nor will you use the word 'color' or 'colors' in your output ever. You will only list the hexcodes, dont even label them. Give me 6 hexcodes that would be good for the following description in json formatting: {description})"
    openai_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[#{"role": "system", "content": "You are an assitant that creates color palettes based on the messages the users send you. You always format your responses like json files, and only ever provide hexcodes as a response."},
                 {"role": "user", "content":prompt}
                    ],
    )
    openai_reply = openai_response["choices"][0]["message"]["content"]
    gpt_hexcodes_json = openai_reply
    print(gpt_hexcodes_json)
    openai_response_received.set()
    openai_response_received.clear()

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


        # Get the user's Documents folder path
        #hpalette_folder = os.path.join(os.path.expanduser('~'), 'Documents', 'HugPalette')
        # Create the HPalette folder if it doesn't exist
        #if not os.path.exists(hpalette_folder):
        #    os.makedirs(hpalette_folder)

if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, use the bundle directory as the base path
    base_path = sys._MEIPASS
else:
    # If the application is run from the command line, use the directory containing the script as the base path
    base_path = os.path.abspath(os.path.dirname(__file__))

icon_path = os.path.join(base_path, "icon.ico")

# Get the user's Pictures folder path
pictures_folder = os.path.join(os.path.expanduser('~'), 'Pictures')

# Create the HPalette folder if it doesn't exist
picexport_folder = os.path.join(pictures_folder, 'HPalette')
if not os.path.exists(picexport_folder):
    os.makedirs(picexport_folder)


def save_image():
    global image_response
    # Get the current date and time
    now = datetime.now()
    date_string = now.strftime("%Y-%m-%d %H-%M-%S")

    # Save the image to the HPalette folder
    filename = f"HugPalette {date_string}.jpg"
    filepath = os.path.join(picexport_folder, filename)
    with open(filepath, 'wb') as f:
        f.write(image_response.content)

    # Show a success message
    messagebox.showinfo("Saved", f"The image has been saved to {filepath}.")


def generate_palette():
    description = description_entry.get()

    if not description:
        messagebox.showerror("Error", "Please enter a description.")
        return

    # Disable the generate button and show a progress bar
    generate_button.config(state="disabled")
    #progress_bar.grid(columnspan=2, padx=10, pady=10)


    # Start the API request in a separate thread
    t1 = threading.Thread(target=get_hexcodes_from_chatgpt, args=(description,))
    t1.start()
    openai_response_received.wait()

    t2 = threading.Thread(target=generate_palette_thread, args=(description,))
    t2.start()




def generate_palette_thread(description):
    print("generate_palette_thread called")
    global image_response
    global gpt_hexcodes_json

    hex_codes_list = json.loads(gpt_hexcodes_json)
    hex_code_string = ', '.join(hex_codes_list)
    
    print(hex_codes_list)
    print(hex_code_string)
    try:
        response = requests.post(
            "https://api.deepai.org/api/text2img",
            data={
                'text': f"Use ONLY the following hex codes to create a preview of how they would look in an elegant painting of a {description}: {hex_code_string}. The output must be limited to only the colors",
                'grid_size': '1',
                'width, height': '1280, 1280',
            },
            headers={'api-key': DEEPAI_API_KEY}
        )
        response_json = response.json()
        print(response_json)
        # Retrieve the output_url from the API response
        output_url = response_json['output_url']

        # Download the image from the output_url
        img_response = requests.get(output_url)
        image = Image.open(BytesIO(img_response.content))

        # Extract colors from the image
        # Extract colors from the image
        colors = image.getcolors(image.size[0] * image.size[1])
        sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True) # Sort colors by pixel count in descending order
        top_colors = sorted_colors[:6] # Get the top 6 colors
        hex_codes = [rgb_to_hex(color[1]) for color in top_colors]

        # Update the color palette display
        for i, hex_code in enumerate(hex_codes_list):
            color_label = tk.Label(hex_frame, text=hex_code, bg=hex_code)
            color_label.grid(row=0, column=i, padx=5, pady=5)

            color_label.bind("<Button-1>", copy_hex_code)

        # resize the image
        resized_image = image.resize((200, 200), resample=Image.BOX)
        # Update the image display
        palette_image = ImageTk.PhotoImage(resized_image)
        palette_label.config(image=palette_image)
        palette_label.image = palette_image

        # Store the image response for later use
        image_response = img_response

    except requests.exceptions.RequestException:
        messagebox.showerror("Error", "An error occurred while generating the color palette.")

    finally:
        #Re-enable the generate button and hide the progress bar
        generate_button.config(state="normal")
        #progress_bar.grid_forget()





def copy_hex_code(event):
    hex_code = event.widget["text"]
    root.clipboard_clear()
    root.clipboard_append(hex_code)
    messagebox.showinfo("Copied", f"{hex_code} copied to clipboard.")


# Create the main window
root = tk.Tk()
root.title("HugPalette")

root.iconbitmap(icon_path)
# Create and pack the description entry
description_entry = tk.Entry(root, width=40)
description_entry.pack(padx=10, pady=10)


# Create and pack the generate button
generate_button = tk.Button(root, text="Generate Palette", command=generate_palette)
generate_button.pack(padx=10, pady=10)

# Create and pack the hex frame
hex_frame = tk.Frame(root)
hex_frame.pack(padx=10, pady=10)

# Create and pack the palette label
palette_label = tk.Label(root)
palette_label.pack(padx=10, pady=10)

# Create and pack the progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=200, mode="indeterminate")
progress_bar.pack(padx=10, pady=10)

# Create and pack the save button
save_button = tk.Button(root, text="Save Image", command=save_image)
save_button.pack(padx=10, pady=10)


# Use grid() to layout color labels in hex_frame
for i in range(6):
    hex_frame.columnconfigure(i, weight=1)
color_labels = []
for i in range(6):
    color_label = tk.Label(hex_frame, text="", width=8, height=3, relief="groove")
    color_label.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
    color_labels.append(color_label)

root.mainloop()

