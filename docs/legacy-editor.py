import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import os
from PIL import Image, ImageTk

class OptionPreviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Option Preview Interface")

        # Create main frame
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Frame for Options
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Right Frame for Preview
        preview_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=2)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Options Header
        option_label = ttk.Label(options_frame, text="Options", font=("Arial", 10, "bold"))
        option_label.pack(anchor=tk.W, pady=(0, 10))

        # Scrollable Listbox for Options
        listbox_frame = ttk.Frame(options_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.options_listbox = tk.Listbox(listbox_frame, height=10, exportselection=False)
        self.options_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.options_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.options_listbox.config(yscrollcommand=scrollbar.set)

        # Populate Listbox
        for option in self.duckoptions():
            self.options_listbox.insert(tk.END, option["name"])

        # Bind selection event
        self.options_listbox.bind("<<ListboxSelect>>", self.update_parameters)

        # Parameters Frame
        self.parameters_frame = ttk.Frame(options_frame)
        self.parameters_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Preview Pane
        self.preview_canvas = tk.Canvas(preview_frame, width=320, height=320, bg="white")
        self.preview_canvas.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Button to Load Image
        load_button = ttk.Button(preview_frame, text="Load Hat", command=self.load_hat)
        load_button.pack(side=tk.LEFT, padx=5)
        save_button = ttk.Button(preview_frame, text="Save Hat", command=self.save_hat)
        save_button.pack(side=tk.LEFT, padx=5)
        strip_button = ttk.Button(preview_frame, text="Clear MetaPixels", command=self.strip_meta)
        strip_button.pack(side=tk.LEFT, padx=5)

        # Dropdown for Colors
        self.color_var = tk.StringVar(value="white")
        color_dropdown = ttk.Combobox(preview_frame, textvariable=self.color_var, state="readonly")
        color_dropdown["values"] = ["white", "yellow", "brown", "grey", "pink", "blue", "purple", "green"]
        color_dropdown.pack(side=tk.LEFT, padx=5)
        color_dropdown.bind("<<ComboboxSelected>>", self.update_background_color)

        # Initial Parameter Update
        self.options_listbox.selection_set(0)
        self.update_parameters()

        # Load Image Paths
        self.background_image_path = r"D:\\Projects\\DuckGameMeta\\Assets\\background.png"
        self.preview_image_path = r"D:\\Projects\\DuckGameMeta\\Assets\\preview.png"
        self.color_offset_map = {
            "white": 0,
            "yellow": 32,
            "brown": 64,
            "grey": 96,
            "pink": 128,
            "blue": 160,
            "purple": 192,
            "green": 224,
        }

        # Load Initial Images
        self.load_preview(0, 0)

        # Load Image Paths
        self.background_image_path = r"D:\\Projects\\DuckGameMeta\\Assets\\background.png"
        self.preview_image_path = r"D:\\Projects\\DuckGameMeta\\Assets\\preview.png"
        self.color_offset_map = {
            "white": 0,
            "yellow": 32,
            "brown": 64,
            "grey": 96,
            "pink": 128,
            "blue": 160,
            "purple": 192,
            "green": 224,
        }

    def duckoptions(self):
        return [
            {
                "id": 1,
                "name": "Hat Offset",
                "description": "Hat offset position in pixels.",
                "parameters": ["X", "Y"]
            },
            {
                "id": 2,
                "name": "Use Duck Color",
                "description": "If this metapixel exists, White (255, 255, 255) and Grey (157, 157, 157) will be recolored to duck colors.",
                "parameters": []
            },
            {
                "id": 10,
                "name": "Cape Offset",
                "description": "Cape offset position in pixels. Basically the same thing as metapixel 1.",
                "parameters": ["X", "Y"]
            },
            {
                "id": 11,
                "name": "Cape Is Foreground",
                "description": "If this metapixel exists, the cape will be drawn over the duck.",
                "parameters": []
            },
            {
                "id": 12,
                "name": "Cape Sway Modifier",
                "description": "It affects the length of the cape and the swing from left to right. "
                               "G determines the cape's rotation, clockwise or counterclockwise. To not rotate it at all, pick 128, the middle value. "
                               "A maxxed rotation in either direction leaves an otherwise downward-pointing cape pointing up and diagonally to the side. "
                               "B determines the cape's weight. 0 will have it flying straight upward. 255 will have it fall to the floor like lead. "
                               "This is applied before the rotation from G.",
                "parameters": ["Rotation", "Weight"]
            },
            {
                "id": 13,
                "name": "Cape Wiggle Modifier",
                "description": "Affects how much the cape wiggles in the wind.",
                "parameters": ["Wiggle Strength"]
            },
            {
                "id": 14,
                "name": "Cape Taper Start",
                "description": "Affects how narrow the cape/trail is at the top/beginning.",
                "parameters": ["Top Taper"]
            },
            {
                "id": 15,
                "name": "Cape Taper End",
                "description": "Affects how narrow the cape/trail is at the bottom/ending.",
                "parameters": ["Bottom Taper"]
            },
            {
                "id": 16,
                "name": "Cape Alpha Start",
                "description": "Affects how transparent the cape/trail is at the top/beginning.",
                "parameters": ["Alpha"]
            },
            {
                "id": 17,
                "name": "Cape Alpha End",
                "description": "Affects how transparent the cape/trail is at the bottom/ending.",
                "parameters": []
            },
            {
                "id": 20,
                "name": "Cape Is Trail",
                "description": "If this metapixel exists, the cape will be a trail instead of a cape (Like the rainbow trail left by the TV).",
                "parameters": []
            },
            {
                "id": 30,
                "name": "Particle Emitter Offset",
                "description": "The offset in pixels from the center of the hat (REMEMBER, G = X Coordinate (Horizontal) = 128, B = Y Coordinate (Vertical) = 128 is the center of the hat (128 and 128)) where particles will be emitted.",
                "parameters": ["X", "Y"]
            },
            {
                "id": 31,
                "name": "Particle Default Behavior",
                "description": "G defines a particle behavior from a list of presets:\n"
                               "0 = No Behavior\n1 = Spit\n2 = Burst\n3 = Halo\n4 = Exclamation",
                "parameters": []
            },
            {
                "id": 32,
                "name": "Particle Emit Shape",
                "description": "G values (How the particles are emitted):\n"
                               "0 = Point\n1 = Circle\n2 = Box\n"
                               "B values (Modifiers):\n"
                               "0 = Emit Around Shape Border Randomly\n"
                               "1 = Fill Shape Randomly\n"
                               "2 = Emit Around Shape Border Uniformly",
                "parameters": []
            },
            {
                "id": 33,
                "name": "Particle Emit Shape Size",
                "description": "X and Y size of the particle emitter (in pixels).",
                "parameters": ["X", "Y"]
            },
            {
                "id": 34,
                "name": "Particle Count",
                "description": "The number of particles to emit.",
                "parameters": []
            },
            {
                "id": 35,
                "name": "Particle Lifespan",
                "description": "Duration time of the particles, in seconds.",
                "parameters": []
            },
            {
                "id": 36,
                "name": "Particle Velocity",
                "description": "Initial velocity of the particle.",
                "parameters": []
            },
            {
                "id": 37,
                "name": "Particle Gravity",
                "description": "Gravity applied to the particle.",
                "parameters": []
            },
            {
                "id": 38,
                "name": "Particle Friction",
                "description": "Friction applied to the particle (The value it's velocity is multiplied by every frame).",
                "parameters": []
            },
            {
                "id": 39,
                "name": "Particle Alpha",
                "description": "G = Start alpha, B = End alpha.",
                "parameters": []
            },
            {
                "id": 40,
                "name": "Particle Scale",
                "description": "G = Start scale, B = End scale.",
                "parameters": []
            },
            {
                "id": 41,
                "name": "Particle Rotation",
                "description": "G = Start rotation, B = End rotation.",
                "parameters": []
            },
            {
                "id": 42,
                "name": "Particle Offset",
                "description": "Additional X Y offset of particle.",
                "parameters": ["X", "Y"]
            },
            {
                "id": 43,
                "name": "Particle Background",
                "description": "If this metapixel exists, particles will be rendered behind the duck.",
                "parameters": []
            },
            {
                "id": 44,
                "name": "Particle Anchor",
                "description": "If this metapixel exists, particles will stay anchored around the hat position when it's moving. This means the particles will stay in the same X coordinate to the hat.",
                "parameters": []
            },
            {
                "id": 45,
                "name": "Particle Animated",
                "description": "If this metapixel exists, particles will animate through their frames. Otherwise, a frame will be picked randomly.",
                "parameters": []
            },
            {
                "id": 46,
                "name": "Particle Animation Loop",
                "description": "If this metapixel exists, the particle animation will loop.",
                "parameters": []
            },
            {
                "id": 47,
                "name": "Particle Animation Random Frame",
                "description": "If this metapixel exists, the particle animation will start on a random frame.",
                "parameters": []
            },
            {
                "id": 48,
                "name": "Particle Animation Speed",
                "description": "How quickly the particle animates.",
                "parameters": []
            },
            {
                "id": 70,
                "name": "Wet Lips",
                "description": "Modifies the quack sound to sound like 'wet lips'.",
                "parameters": []
            },
            {
                "id": 71,
                "name": "Mechanical Lips",
                "description": "Modifies the quack to sound like 'mechanical lips'.",
                "parameters": []
            },
            {
                "id": 100,
                "name": "Randomize Parameter X",
                "description": "",
                "parameters": []
            },
            {
                "id": 101,
                "name": "Randomizer Parameter Y",
                "description": "",
                "parameters": []
            },
            {
                "id": 102,
                "name": "Randomize Parameter",
                "description": "",
                "parameters": []
            }
        ]

    def update_parameters(self, event=None):
        # Clear previous parameters
        for widget in self.parameters_frame.winfo_children():
            widget.destroy()

        # Get selected option
        selected_index = self.options_listbox.curselection()
        if not selected_index:
            return
        selected_option_name = self.options_listbox.get(selected_index)
        selected_option = next(opt for opt in self.duckoptions() if opt["name"] == selected_option_name)

        # Add toggle checkbox for the entire option
        toggle_frame = ttk.Frame(self.parameters_frame)
        toggle_frame.pack(fill=tk.X, pady=(5, 10))

        toggle_var = tk.BooleanVar(value=False)
        toggle_checkbox = ttk.Checkbutton(toggle_frame, text=f"Enable {selected_option['name']}", variable=toggle_var)
        toggle_checkbox.pack(anchor=tk.W)

        # Tooltip button for option description
        help_button = ttk.Button(toggle_frame, text="?", width=2, command=lambda desc=selected_option["description"]: self.show_tooltip(desc))
        help_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Display parameters dynamically
        if selected_option["parameters"]:
            for param in selected_option["parameters"]:
                frame = ttk.Frame(self.parameters_frame)
                frame.pack(fill=tk.X, pady=(5, 0))

                label = ttk.Label(frame, text=param, width=15, anchor=tk.W)
                label.pack(side=tk.LEFT, padx=(0, 5))

                entry_var = tk.StringVar(value="0")
                entry = ttk.Entry(frame, textvariable=entry_var, width=10)
                entry.pack(side=tk.LEFT)

                # Add slider if the parameter is numeric
                slider = ttk.Scale(
                    frame, from_=0, to=255, orient=tk.HORIZONTAL,
                    command=lambda value, var=entry_var: var.set(str(int(float(value))))
                )
                slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

                # Link text field to slider
                entry_var.trace_add("write", lambda *args, slider=slider, var=entry_var: slider.set(float(var.get()) if var.get().isdigit() else 0))

    def show_tooltip(self, description):
        # Show a message box with the description
        messagebox.showinfo("Option Info", description)

    def load_preview(self, duck_offset, back_offset):
        try:
            background_image = Image.open(self.background_image_path)
            background_image = background_image.crop((back_offset, 0, back_offset + 32, 32))  # Crop 32x32 pixels
            background_image = background_image.resize((320, 320), Image.NEAREST)  # Scale up by 1000%
            self.background_preview_image = ImageTk.PhotoImage(background_image)
            self.preview_canvas.create_image(0, 70, anchor=tk.NW, image=self.background_preview_image)
        except Exception as e:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                160, 160, text="Error\nLoading Background", anchor=tk.CENTER, font=("Arial", 10)
            )
        try:
            preview_image = Image.open(self.preview_image_path)
            preview_image = preview_image.crop((duck_offset, 0, duck_offset + 32, 32))  # Crop 32x32 pixels
            preview_image = preview_image.resize((320, 320), Image.NEAREST)  # Scale up by 1000%
            self.preview_image = ImageTk.PhotoImage(preview_image)
            # self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.background_preview_image)
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
        except Exception as e:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                160, 160, text="Error\nLoading Image", anchor=tk.CENTER, font=("Arial", 10)
            )
    def update_background_color(self, event):
        selected_color = self.color_var.get()
        offset = self.color_offset_map.get(selected_color, 0)
        self.load_preview(0, offset)

    def update_preview(self):
        preview_text = "Options Preview:\n"
        for option in self.options:
            name = option["name"]
            enabled = "Enabled" if option["enabled"].get() else "Disabled"
            param1 = option["param1"].get()
            param2 = option["param2"].get()
            preview_text += f"{name}: {enabled}, Param1={param1}, Param2={param2}\n"
        selected_color = self.color_var.get()
        preview_text += f"Selected Color: {selected_color}\n"
        print(preview_text)  # Preview text is now printed to the console for debugging

    def load_hat(self):
        # Implementation for loading preview image
        pass

    def save_hat(self):
        # Define the size of the image (97x56)
        image_width, image_height = 97, 56
        canvas_column = 96  # 0-indexed, corresponds to the 97th column

        # Create a blank image with a transparent background (RGBA)
        final_image = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
        pixels = final_image.load()

        # Iterate over all options and draw pixels for enabled ones
        for option in self.duckoptions():
            # Retrieve option's ID and parameters
            option_id = option["id"]
            parameters = option["parameters"]

            # Check if the option is enabled
            selected_index = self.options_listbox.curselection()
            if not selected_index:
                continue
            selected_option_name = self.options_listbox.get(selected_index)
            if option["name"] != selected_option_name:
                continue

            # Default parameter values
            param1 = 0
            param2 = 0

            # Get parameter values if they exist
            for widget in self.parameters_frame.winfo_children():
                if isinstance(widget, ttk.Entry):
                    param_value = widget.get()
                    try:
                        if parameters.index("X") == 0:  # X corresponds to parameter 1
                            param1 = int(param_value)
                        elif parameters.index("Y") == 1:  # Y corresponds to parameter 2
                            param2 = int(param_value)
                    except (ValueError, IndexError):
                        pass

            # Draw the pixel for the option in the 97th column
            pixels[canvas_column, option_id % image_height] = (option_id, param2, param1, 255)

        # Save the final image to the specified location
        save_path = r"C:\Users\Diome\Documents\DuckGame\Custom\Hats\export.png"
        final_image.save(save_path, "PNG")

        # Show confirmation to the user
        messagebox.showinfo("Save Complete", f"Image saved to {save_path}")

    def strip_meta(self):
        """
        Resets all options to their default state by disabling them and clearing parameters.
        """
        for option in self.options:
            # Disable the toggle for the entire option
            option["enabled"].set(False)

            # Reset all parameter fields (if any)
            for param in option.get("parameter_vars", []):
                if isinstance(param, tk.StringVar):
                    param.set("")  # Clear text fields
                elif isinstance(param, tk.IntVar):
                    param.set(0)  # Reset sliders to 0 or their default value

        # Clear the displayed parameters in the parameter frame
        for widget in self.param_frame.winfo_children():
            widget.destroy()

        # Optionally, display a default message in the parameter frame
        ttk.Label(self.param_frame, text="Select an option to edit parameters.").pack()


# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = OptionPreviewApp(root)
    root.mainloop()
