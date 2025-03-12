import tkinter as tk
from tkinter import ttk, messagebox
import qrcode
from PIL import Image, ImageTk
import json
import os
import requests
from datetime import datetime
import uuid
import base64

class XeroxQRGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Xerox Shop QR Code Generator")
        self.root.geometry("800x650")
        self.root.resizable(False, False)
        
        # Set app icon
        try:
            self.root.iconbitmap("printer_icon.ico")
        except:
            pass
            
        # Variables
        self.shop_id = tk.StringVar()
        self.shop_name = tk.StringVar()
        self.server_url = tk.StringVar()
        self.server_url.set("https://")
        self.qr_generated = False
        self.qr_image = None
        
        # Flask server status (for admin verification)
        self.server_running = False
        
        self.create_widgets()
        self.check_server_connection()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Xerox Shop QR Code Generator", 
                               font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)
        
        # Form frame
        form_frame = ttk.LabelFrame(main_frame, text="Shop Information", padding=15)
        form_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Shop ID
        shop_id_frame = ttk.Frame(form_frame)
        shop_id_frame.pack(fill=tk.X, pady=5)
        
        shop_id_label = ttk.Label(shop_id_frame, text="Shop ID:", width=15)
        shop_id_label.pack(side=tk.LEFT)
        
        shop_id_entry = ttk.Entry(shop_id_frame, textvariable=self.shop_id)
        shop_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Generate unique ID button
        generate_id_button = ttk.Button(shop_id_frame, text="Generate Unique ID", 
                                      command=self.generate_unique_id)
        generate_id_button.pack(side=tk.RIGHT, padx=5)
        
        # Shop Name
        shop_name_frame = ttk.Frame(form_frame)
        shop_name_frame.pack(fill=tk.X, pady=5)
        
        shop_name_label = ttk.Label(shop_name_frame, text="Shop Name:", width=15)
        shop_name_label.pack(side=tk.LEFT)
        
        shop_name_entry = ttk.Entry(shop_name_frame, textvariable=self.shop_name)
        shop_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Server URL
        server_url_frame = ttk.Frame(form_frame)
        server_url_frame.pack(fill=tk.X, pady=5)
        
        server_url_label = ttk.Label(server_url_frame, text="Server URL:", width=15)
        server_url_label.pack(side=tk.LEFT)
        
        server_url_entry = ttk.Entry(server_url_frame, textvariable=self.server_url)
        server_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Server status indicator
        self.server_status_frame = ttk.Frame(form_frame)
        self.server_status_frame.pack(fill=tk.X, pady=5)
        
        server_status_label = ttk.Label(self.server_status_frame, text="Server Status:", width=15)
        server_status_label.pack(side=tk.LEFT)
        
        self.server_status_indicator = ttk.Label(self.server_status_frame, text="Checking...", 
                                            foreground="gray")
        self.server_status_indicator.pack(side=tk.LEFT)
        
        check_server_button = ttk.Button(self.server_status_frame, text="Check Connection", 
                                      command=self.check_server_connection)
        check_server_button.pack(side=tk.RIGHT)
        
        # Button Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        generate_button = ttk.Button(button_frame, text="Generate QR Code", 
                                  command=self.generate_qr)
        generate_button.pack(side=tk.LEFT, padx=5)
        
        save_button = ttk.Button(button_frame, text="Save QR Code", 
                              command=self.save_qr)
        save_button.pack(side=tk.LEFT, padx=5)
        
        register_button = ttk.Button(button_frame, text="Register with Server", 
                                  command=self.register_with_server)
        register_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = ttk.Button(button_frame, text="Clear", 
                               command=self.clear_form)
        clear_button.pack(side=tk.RIGHT, padx=5)
        
        # QR Display Frame
        self.qr_frame = ttk.LabelFrame(main_frame, text="Generated QR Code", padding=15)
        self.qr_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.qr_display = ttk.Label(self.qr_frame)
        self.qr_display.pack(fill=tk.BOTH, expand=True)
        
        # QR Info display
        self.qr_info = ttk.Label(self.qr_frame, text="QR code will appear here", justify=tk.CENTER)
        self.qr_info.pack(fill=tk.X, pady=10)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def generate_unique_id(self):
        # Generate a unique shop ID
        unique_id = f"shop_{uuid.uuid4().hex[:8]}"
        self.shop_id.set(unique_id)
        self.status_bar.config(text=f"Generated unique ID: {unique_id}")
    
    def check_server_connection(self):
        # Try to connect to the server URL
        url = self.server_url.get()
        if not url or url == "https://":
            self.server_status_indicator.config(text="No URL provided", foreground="orange")
            return
            
        try:
            self.status_bar.config(text=f"Checking connection to {url}...")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                self.server_status_indicator.config(text="Connected", foreground="green")
                self.server_running = True
                self.status_bar.config(text=f"Successfully connected to {url}")
            else:
                self.server_status_indicator.config(text=f"Error: {response.status_code}", 
                                                 foreground="red")
                self.server_running = False
        except Exception as e:
            self.server_status_indicator.config(text="Connection Failed", foreground="red")
            self.server_running = False
            self.status_bar.config(text=f"Connection error: {str(e)}")
    
    def generate_qr(self):
        # Validate inputs
        shop_id = self.shop_id.get().strip()
        shop_name = self.shop_name.get().strip()
        server_url = self.server_url.get().strip()
        
        if not shop_id:
            messagebox.showerror("Error", "Shop ID is required")
            return
            
        if not server_url or server_url == "https://":
            messagebox.showerror("Error", "Server URL is required")
            return
        
        # Create QR code data
        qr_data = {
            "shop_id": shop_id,
            "server_url": server_url
        }
        
        if shop_name:
            qr_data["shop_name"] = shop_name
            
        # Add timestamp for uniqueness
        qr_data["generated_at"] = datetime.now().isoformat()
        
        # Convert to JSON string
        json_data = json.dumps(qr_data)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(json_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to PhotoImage for display
        self.qr_image = qr_img
        photo_image = ImageTk.PhotoImage(qr_img)
        
        # Display the QR code
        self.qr_display.config(image=photo_image)
        self.qr_display.image = photo_image  # Keep a reference
        
        # Update QR info
        self.qr_info.config(text=f"Shop ID: {shop_id}\nServer: {server_url}")
        
        self.qr_generated = True
        self.status_bar.config(text="QR code generated successfully")
    
    def save_qr(self):
        if not self.qr_generated or not self.qr_image:
            messagebox.showerror("Error", "No QR code has been generated yet")
            return
            
        shop_id = self.shop_id.get().strip()
        # Create filename
        filename = f"xerox_shop_{shop_id}_qr.png"
        
        try:
            # Save the image
            self.qr_image.save(filename)
            self.status_bar.config(text=f"QR code saved as {filename}")
            messagebox.showinfo("Success", f"QR code saved as {filename}")
        except Exception as e:
            self.status_bar.config(text=f"Error saving QR code: {str(e)}")
            messagebox.showerror("Error", f"Failed to save QR code: {str(e)}")
    
    def register_with_server(self):
        if not self.qr_generated:
            messagebox.showerror("Error", "Generate a QR code first")
            return
            
        if not self.server_running:
            messagebox.showerror("Error", "Cannot connect to server")
            return
            
        shop_id = self.shop_id.get().strip()
        shop_name = self.shop_name.get().strip()
        server_url = self.server_url.get().strip()
        
        # Convert QR image to base64 for sending
        import io
        buffered = io.BytesIO()
        self.qr_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Prepare data for sending
        data = {
            "shop_id": shop_id,
            "shop_name": shop_name,
            "server_url": server_url,
            "qr_code_image": img_str
        }
        
        try:
            self.status_bar.config(text="Registering with server...")
            response = requests.post(f"{server_url}/api/register_shop", json=data, timeout=10)
            
            if response.status_code == 200:
                self.status_bar.config(text="Successfully registered with server")
                messagebox.showinfo("Success", "Shop registered successfully with the server")
            else:
                error_msg = f"Server returned error: {response.status_code}"
                try:
                    error_msg += f" - {response.json().get('error', '')}"
                except:
                    pass
                    
                self.status_bar.config(text=error_msg)
                messagebox.showerror("Error", error_msg)
                
        except Exception as e:
            self.status_bar.config(text=f"Error registering with server: {str(e)}")
            messagebox.showerror("Error", f"Failed to register with server: {str(e)}")
    
    def clear_form(self):
        self.shop_id.set("")
        self.shop_name.set("")
        self.server_url.set("https://")
        self.qr_generated = False
        self.qr_display.config(image="")
        self.qr_info.config(text="QR code will appear here")
        self.status_bar.config(text="Form cleared")

if __name__ == "__main__":
    root = tk.Tk()
    app = XeroxQRGenerator(root)
    root.mainloop()
