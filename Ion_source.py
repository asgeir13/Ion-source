import tkinter as tk
from tkinter import messagebox
import serial
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter.filedialog import asksaveasfilename
from datetime import datetime

class MaxiGauge:
    def __init__(self, port, baudrate=9600, timeout=1):
        """Initialize the MaxiGauge connection."""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    def connect(self):
        """Establish a connection to the MaxiGauge."""
        try:
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
        except serial.SerialException as e:
            print(f"Failed to connect to MaxiGauge: {e}")
            self.connection = None

    def disconnect(self):
        """Close the connection to the MaxiGauge."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("Disconnected from MaxiGauge.")

    def send_command(self, command):
        """Send a command to the MaxiGauge and return the response."""
        if not self.connection or not self.connection.is_open:
            print("MaxiGauge is not connected. Please check the connection.")
            return None

        try:
            # Send the command with \r\n
            full_command = f"{command}\r\n".encode('utf-8')
            self.connection.write(full_command)
            time.sleep(0.1)  # Small delay to allow the device to process the command

            # Read the first byte
            first_byte = self.connection.read_until(b'\r\n')
            # if first_byte == b'\x06':  # If ACK is received
            #     print("Command acknowledged.")
            # elif first_byte:  # If the first byte is part of the response
            #     print(f"Unexpected byte received: {first_byte}. Assuming it's part of the response.")
            #     response = first_byte + self.connection.read_until(b'\r\n')
            #     return response.decode('utf-8').strip()
            # else:
            #     print("No acknowledgment or response received.")
            #     return None

            # Send \x05\r\n to demand data transfer
            self.connection.write(b"\x05\r\n")
            time.sleep(0.1)

            # Read the response using read_until
            response = self.connection.read_until(b'\r\n').decode('utf-8').strip().split(',')[1]
            if not response:
                print("No response received from MaxiGauge.")
            return response
        except serial.SerialTimeoutException:
            print("Timeout occurred while communicating with MaxiGauge.")
            return None
        except Exception as e:
            print(f"Error communicating with MaxiGauge: {e}")
            return None

    def get_pressure(self, sensor):
        """Get the pressure reading from a specific sensor."""
        if not (1 <= sensor <= 6):
            print("Invalid sensor number. Must be between 1 and 6.")
            return None

        if not self.connection or not self.connection.is_open:
            print("MaxiGauge is not connected. Cannot retrieve pressure.")
            return None

        command = f"PR{sensor}"  # Command to read pressure from the specified sensor
        response = self.send_command(command)
        if response:
            return float(response)  # Convert the response to a float
        else:
            print("No response from MaxiGauge.")
            return None

def connect_to_device():
    global device
    try:
        # Specify the serial port and settings
        port = '/dev/cu.usbserial-1110'  # Replace with your device's serial port
        baudrate = 9600
        timeout = 1  # Timeout in seconds

        # Open the serial connection
        device = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        print(f"Connected to {port} successfully.")

        # Configure device settings
        device.write(b"A\r")  # Send an identification query
        time.sleep(0.5)  # Wait for the device to respond
        response = device.read_all().decode('utf-8').strip()  # Read the response
        print(f"Device Response: {response}")

        # Show the response in a message box
        if response:
            messagebox.showinfo("Connection Successful", f"Device Response: {response}")
        else:
            messagebox.showwarning("Connection Warning", "No response from the device.")
    except serial.SerialException as e:
        messagebox.showerror("Connection Failed", f"Serial Error: {e}")
    except Exception as e:
        messagebox.showerror("Connection Failed", f"Error: {e}")

def connect_to_maxigauge():
    """Connect to the Pfeiffer MaxiGauge."""
    global maxigauge
    try:
        # Specify the serial port and settings for the MaxiGauge
        port = '/dev/cu.usbserial-114410'  # Replace with your MaxiGauge's serial port
        baudrate = 9600
        timeout = 1  # Timeout in seconds

        # Open the serial connection
        maxigauge = MaxiGauge(port, baudrate, timeout)
        maxigauge.connect()
    except serial.SerialException as e:
        messagebox.showerror("Connection Failed", f"Failed to connect to MaxiGauge: {e}")
        maxigauge = None
    except Exception as e:
        messagebox.showerror("Connection Failed", f"Error: {e}")
        maxigauge = None

def parse_reading(data):
    """Parse the RC response string into a dictionary."""
    try:
        # Clean the data by removing unwanted characters
        cleaned_data = data.replace('\n', '').replace('\r', '').replace('\x04', '').replace(' ', '').strip()

        # Remove the RC prefix if present
        if cleaned_data.startswith("RC"):
            cleaned_data = cleaned_data[2:].strip()

        # Split the cleaned string by commas
        values = cleaned_data.split(',')

        # Helper function to safely parse float values
        def safe_float(value):
            try:
                # If the value starts with 'E' or 'e', prepend '1'
                if value.startswith(('E', 'e')):
                    value = '1' + value
                return float(value)
            except ValueError:
                return 0.0  # Default to 0.0 if parsing fails

        # Map the parsed values to their respective keys
        parsed_data = {
            "Cathode Current (A)": safe_float(values[0]) if len(values) > 0 else 0.0,
            "Discharge Current (A)": safe_float(values[1]) if len(values) > 1 else 0.0,
            "Discharge Voltage (V)": safe_float(values[2]) if len(values) > 2 else 0.0,
            "Beam Current (mA)": safe_float(values[3]) if len(values) > 3 else 0.0,
            "Beam Voltage (V)": safe_float(values[4]) if len(values) > 4 else 0.0,
            "Accelerator Current (mA)": safe_float(values[5]) if len(values) > 5 else 0.0,
            "Accelerator Voltage (V)": safe_float(values[6]) if len(values) > 6 else 0.0,
            "Emission Current (mA)": safe_float(values[7]) if len(values) > 7 else 0.0,
            "Neutralizer Filament Current (A)": safe_float(values[8]) if len(values) > 8 else 0.0,
            "HC Keeper Voltage (V)": safe_float(values[9]) if len(values) > 9 else 0.0,
            "HCN Keeper Voltage (V)": safe_float(values[10]) if len(values) > 10 else 0.0,
            "Fatal Error Code": int(values[11]) if len(values) > 11 and values[11].isdigit() else 0,
            "Power Supply Mode": int(values[12]) if len(values) > 12 and values[12] else "Unknown",
        }
        print(parsed_data)
        return parsed_data
    except (IndexError, ValueError) as e:
        print(f"Error parsing data: {e}")
        return None

def parse_rh_reading(data):
    """Parse the RH response string into a dictionary."""
    try:
        # Remove leading/trailing whitespace and split by spaces
        values = data.strip().split(' ')
        
        # Extract and clean the relevant fields
        time_values = values[0].split(':')  # Extract Hr:Min:Sec
        cathode_filament_current = float(values[1])  # DD.DD
        discharge_current = float(values[2])  # E.EE
        discharge_voltage = float(values[3])  # FFF.F
        beam_current = int(values[4])  # GGG
        beam_voltage = int(values[5])  # HHHH
        accelerator_voltage = int(values[6])  # IIII
        accelerator_current = int(values[7])  # JJJ
        emission_current = int(values[8])  # KKK
        neutralizer_filament_current = float(values[9])  # LL.LL

        # Create a dictionary with parsed values
        parsed_data = {
            "Time (Hr:Min:Sec)": f"{time_values[0]}:{time_values[1]}:{time_values[2]}",
            "Cathode Filament Current (A)": cathode_filament_current,
            "Discharge Current (A)": discharge_current,
            "Discharge Voltage (V)": discharge_voltage,
            "Beam Current (mA)": beam_current,
            "Beam Voltage (V)": beam_voltage,
            "Accelerator Voltage (V)": accelerator_voltage,
            "Accelerator Current (mA)": accelerator_current,
            "Emission Current (mA)": emission_current,
            "Neutralizer Filament Current (A)": neutralizer_filament_current,
        }
        return parsed_data
    except (IndexError, ValueError) as e:
        print(f"Error parsing RH data: {e}")
        return None

# Global variables to track the states
source_on = False
reading_active = False

# Global variables to store data for plotting
timestamps = []
discharge_currents = []
beam_currents = []
pressure = []

# Global variable to track the start time
start_time = None

# Global variable to track the beam state
beam_on = False

# Global variable for data logging
data_log_file = None

def initialize_data_logging():
    """Prompt the user for a file to log data and open it for writing."""
    global data_log_file

    # Ask the user for a file name
    file_name = asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        title="Select Data Log File"
    )
    if not file_name:
        messagebox.showerror("Error", "No file selected for data logging. Exiting.")
        root.destroy()  # Exit the program if no file is selected
        return

    try:
        # Open the file in append mode
        data_log_file = open(file_name, "a")
        # Write the header to the file
        data_log_file.write("Ion Source Data Log\n")
        data_log_file.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n")
        data_log_file.write(f"Time: {datetime.now().strftime('%H:%M:%S')}\n")
        data_log_file.write("Columns: Time, Discharge Current (A), Beam Current (mA), Pressure (mbar)\n\n")
        print(f"Data will be logged to: {file_name}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open file for logging: {e}")
        root.destroy()  # Exit the program if the file cannot be opened

def read_values(force_read=False):
    """Send RC command, read response, parse it, and update the plot."""
    global device, maxigauge, ax, ax_pressure, canvas, reading_active, timestamps, discharge_currents, beam_currents, pressure, start_time
    try:
        if not device or not device.is_open:
            messagebox.showerror("Error", "Device is not connected.")
            return

        if not maxigauge or not maxigauge.connection or not maxigauge.connection.is_open:
            print("MaxiGauge is not connected.")
            pressure_sensor_3 = None  # No pressure reading available
        else:
            # Query the MaxiGauge for pressure at sensor 3
            pressure_sensor_3 = maxigauge.get_pressure(3)
            if pressure_sensor_3 is not None:
                print(f"Pressure at Sensor 3: {pressure_sensor_3} mbar")
            else:
                print("Failed to get pressure reading from MaxiGauge.")

        # Skip the reading loop if not active, unless forced
        if not reading_active and not force_read:
            print("Reading loop stopped.")
            return

        # Send the RC command to the other device
        device.write(b"RC\r")
        time.sleep(0.8)  # Wait for the device to respond
        response = device.read_all().decode('utf-8').strip()
        print(f"Received: {response}")

        # Remove the RC prefix (if present)
        if response.startswith("RC"):
            response = response[response.index("\n") + 1:].strip()  # Remove "RC\n\r" prefix
            print(f"Cleaned Response: {response}")

        # Parse the response
        parsed_data = parse_reading(response)
        if parsed_data:
            # Calculate elapsed time since the source was turned on
            elapsed_time = time.time() - start_time  # Elapsed time in seconds
            elapsed_time_formatted = f"{int(elapsed_time // 60)}:{int(elapsed_time % 60):02d}"  # Format as MM:SS

            # Update the data lists
            timestamps.append(elapsed_time_formatted)
            discharge_currents.append(parsed_data["Discharge Current (A)"])
            beam_currents.append(parsed_data["Beam Current (mA)"])
            pressure.append(pressure_sensor_3)

            # Log the pressure reading (if available)
            if pressure_sensor_3 is not None:
                print(f"Pressure at Sensor 3: {pressure_sensor_3} mbar")

            # Update the plot
            ax.clear()
            ax.plot(timestamps, discharge_currents, label="Discharge Current (A)", marker="o", color="blue")
            ax.plot(timestamps, beam_currents, label="Beam Current (mA)", marker="o", color="green")
            ax.set_title("Discharge and Beam Current Over Time")
            ax.set_xlabel("Time (MM:SS)")
            ax.set_ylabel("Current")
            ax.legend(loc="upper left")

            ax_pressure.clear()
            ax_pressure.plot(timestamps, pressure, label="Pressure (mbar)", marker="o", color="red")
            ax_pressure.set_ylabel("Pressure (mbar)", color="red")
            ax_pressure.tick_params(axis="y", labelcolor="red")
            ax_pressure.legend(loc="upper right")

            canvas.draw()

            # Log the data to the file
            if data_log_file:
                data_log_file.write(f"{elapsed_time_formatted}, {parsed_data['Discharge Current (A)']}, {parsed_data['Beam Current (mA)']}, {pressure_sensor_3}\n")

        # Schedule the next reading if not forced
        if not force_read:
            root.after(1000, read_values)  # Call this function again after 1 second
    except Exception as e:
        print(f"Error reading values: {e}")

def toggle_reading():
    """Toggle the reading loop on or off."""
    global reading_active, start_time
    if reading_active:
        # Stop the reading loop
        reading_active = False
        reading_button.config(text="Start Reading Values")
        print("Reading loop stopped.")
    else:
        # Start the reading loop
        reading_active = True
        start_time = time.time()  # Record the current time as the start time
        reading_button.config(text="Stop Reading Values")
        read_values()

def set_values():
    try:
        if not device or not device.is_open:
            messagebox.showerror("Error", "Device is not connected.")
            return

        # Get values from the entries
        values = {
            #"CI": filament_entry.get(),     #filament current setpoint
            "AE": 1,                         #Auto error logging
            "DV": discharge_entry.get(),    #discharge voltage setpoint
            "BV": beam_entry.get(),         #beam voltage setpoint
            "AV": accelerator_entry.get(),  #accelerator voltage setpoint
            "AB": 20,                       #A/B ratio in percentage
            "AC": 1,                        #Auto cathode mode 1(on)
            "CL": 8,                        #Cathode limit
            "DT": 0.16,
            #"DI": 0.22,                     #Discharge current threshold
            "BE": 40,                       #Beam current tolerance in percentage 10% here
            "BI": 18,                       #Beam current in mA
            "NL": 0.02,                     #neutralizer limit, setpoint works in manual mode but not in others                       
            "NE": 1,
            }

        # Send commands to the device
        for command, value in values.items():
            if value:  # Only send if the entry is not empty
                full_command = f"{command}{value}\r".encode('utf-8')
                device.write(full_command)
                time.sleep(0.5)  # Small delay between commands
                print(f"Sent: {full_command.decode('utf-8')}")
                response = device.read_all().decode('utf-8')
                print(response)

        messagebox.showinfo("Success", "Values set successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to set values: {e}")

# Function to toggle the ion source
def toggle_source():
    """Toggle the ion source on or off."""
    global source_on
    try:
        if not device or not device.is_open:
            messagebox.showerror("Error", "Device is not connected.")
            return

        # Toggle the source state
        if source_on:
            # Turn off the source
            device.write(b"S0\r")
            time.sleep(0.5)
            print("Sent: S0")
            device.read_all()  # Clear the input buffer
            source_on = False
            source_button.config(text="Turn Source On")
            messagebox.showinfo("Success", "Ion source turned off.")
        else:
            # Turn on the source
            device.write(b"S1\r")
            time.sleep(0.5)
            print("Sent: S1")
            device.read_all()  # Clear the input buffer
            source_on = True
            source_button.config(text="Turn Source Off")
            messagebox.showinfo("Success", "Ion source turned on.")

        # Update the beam button state
        update_beam_button_state()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to toggle ion source: {e}")

def toggle_beam():
    global beam_on  # Declare beam_on as global to modify the global variable
    if not device or not device.is_open:
        messagebox.showerror("Error", "Device is not connected.")
        return

    if not source_on:
        messagebox.showwarning("Warning", "The source must be turned on before enabling the beam.")
        return

    # Toggle the beam state
    if beam_on:
        # Turn off the beam
        device.write(b"B0\r")
        time.sleep(0.5)
        print("Sent: B0")
        device.read_all()  # Clear the input buffer
        beam_on = False
        beam_button.config(text="Turn Beam On")
    else:
        # Turn on the beam
        device.write(b"B1\r")
        time.sleep(0.5)
        print("Sent: B1")
        device.read_all()  # Clear the input buffer
        beam_on = True
        beam_button.config(text="Turn Beam Off")

def update_beam_button_state():
    """Enable or disable the beam button based on the source state."""
    if source_on:
        beam_button.config(state=tk.NORMAL)
    else:
        beam_button.config(state=tk.DISABLED)

def create_plot_window():
    """Create a separate window for the plot and position it to the right of the screen."""
    global ax, ax_pressure, canvas, timestamps, discharge_currents, beam_currents, pressure

    # Create a new Toplevel window
    plot_window = tk.Toplevel(root)
    plot_window.title("Ion Source Data Plot")

    # Position the plot window to the right of the screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    plot_window.geometry(f"800x500+{screen_width - 820}+100")  # Adjusted height to accommodate the toolbar

    # Create a matplotlib figure for displaying the readings
    fig, ax = plt.subplots(figsize=(8, 4))

    # Create a secondary y-axis for pressure
    ax_pressure = ax.twinx()  # Share the same x-axis with the primary plot

    # Create the canvas for embedding the plot in the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=plot_window)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Add the Matplotlib toolbar below the figure
    toolbar = NavigationToolbar2Tk(canvas, plot_window)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    # Initialize the plot with empty data
    ax.plot(timestamps, discharge_currents, label="Discharge Current (A)", marker="o", color="blue")
    ax.plot(timestamps, beam_currents, label="Beam Current (mA)", marker="o", color="green")
    ax.set_title("Discharge and Beam Current Over Time")
    ax.set_xlabel("Time")
    ax.set_ylabel("Current")
    ax.legend(loc="upper left")

    # Initialize the pressure plot on the secondary y-axis
    ax_pressure.plot(timestamps, pressure, label="Pressure (mbar)", marker="o", color="red")
    ax_pressure.set_ylabel("Pressure (mbar)", color="red")
    ax_pressure.tick_params(axis="y", labelcolor="red")
    ax_pressure.legend(loc="upper right")

    # Draw the canvas
    canvas.draw()

def save_data():
    """Close the data log file to finalize data logging."""
    global data_log_file

    try:
        if data_log_file:
            # Close the data log file
            data_log_file.close()
            data_log_file = None  # Reset the global variable
            messagebox.showinfo("Success", "Data log file has been closed successfully.")
            print("Data log file closed successfully.")
        else:
            messagebox.showwarning("No File", "No data log file is currently open.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to close the data log file: {e}")

def create_sequence():
    """Create a sequence where the beam is turned on and off for specified periods, collecting data during each period."""
    global reading_active  # Access the global variable to control the reading loop
    try:
        if not device or not device.is_open:
            messagebox.showerror("Error", "Device is not connected.")
            return

        if not source_on:
            messagebox.showwarning("Warning", "The source must be turned on before starting the sequence.")
            return

        # Pause the reading loop if it is active
        if reading_active:
            reading_active = False
            print("Reading loop paused for sequence.")

        # Get timing and period values from entries
        on_time = float(on_time_entry.get())  # Time in seconds to keep the beam on
        off_time = float(off_time_entry.get())  # Time in seconds to keep the beam off
        periods = int(periods_entry.get())  # Number of on/off cycles

        # Validate input
        if on_time <= 0 or off_time <= 0 or periods <= 0:
            messagebox.showerror("Error", "All values must be positive numbers.")
            return

        # Run the sequence
        for i in range(periods):
            print(f"Starting period {i + 1}/{periods}...")

            # Turn the beam on
            device.write(b"B1\r")
            time.sleep(0.5)
            print("Sent: B1 (Beam On)")
            device.read_all()  # Clear the input buffer
            beam_button.config(text="Turn Beam Off")

            # Collect data during the beam-on period
            start_time = time.time()
            while time.time() - start_time < on_time:
                read_values(force_read=True)  # Collect data and update the plot
                time.sleep(0.5)  # Small delay to avoid overwhelming the device

            # Turn the beam off
            device.write(b"B0\r")
            time.sleep(0.5)
            print("Sent: B0 (Beam Off)")
            device.read_all()  # Clear the input buffer
            beam_button.config(text="Turn Beam On")

            # Collect data during the beam-off period
            start_time = time.time()
            while time.time() - start_time < off_time:
                read_values(force_read=True)  # Collect data and update the plot
                time.sleep(0.5)  # Small delay to avoid overwhelming the device

        # Resume the reading loop if it was active before
        if not reading_active:
            reading_active = True
            print("Reading loop resumed after sequence.")
            read_values()

        messagebox.showinfo("Sequence Complete", "The beam sequence has been completed.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to execute sequence: {e}")

def refresh_plot():
    """Refresh the plot with the latest data."""
    global ax, ax_pressure, canvas, timestamps, discharge_currents, beam_currents, pressure

    # Clear the plot and redraw with updated data
    ax.clear()
    ax.plot(timestamps, discharge_currents, label="Discharge Current (A)", marker="o", color="blue")
    ax.plot(timestamps, beam_currents, label="Beam Current (mA)", marker="o", color="green")
    ax.set_title("Discharge and Beam Current Over Time")
    ax.set_xlabel("Time (MM:SS)")
    ax.set_ylabel("Current")
    ax.legend(loc="upper left")

    ax_pressure.clear()
    ax_pressure.plot(timestamps, pressure, label="Pressure (mbar)", marker="o", color="red")
    ax_pressure.set_ylabel("Pressure (mbar)", color="red")
    ax_pressure.tick_params(axis="y", labelcolor="red")
    ax_pressure.legend(loc="upper right")

    canvas.draw()

def update_pressure():
    """Query the MaxiGauge for pressure at sensor 3 and update the display."""
    global maxigauge

    try:
        if not maxigauge or not maxigauge.connection or not maxigauge.connection.is_open:
            pressure_entry.config(state="normal")
            pressure_entry.delete(0, tk.END)
            pressure_entry.insert(0, "Not Connected")
            pressure_entry.config(state="readonly")
            source_button.config(state=tk.DISABLED)  # Disable source button
            return

        # Get the pressure at sensor 3
        pressure_sensor_3 = maxigauge.get_pressure(sensor=3)
        if pressure_sensor_3 is not None:
            pressure_entry.config(state="normal")
            pressure_entry.delete(0, tk.END)
            pressure_entry.insert(0, f"{pressure_sensor_3:.3e}")  # Display in scientific notation
            pressure_entry.config(state="readonly")

            # Enable or disable the source button based on pressure range
            if 3e-4 <= pressure_sensor_3 <= 10e-4:
                source_button.config(state=tk.NORMAL)  # Enable source button
            else:
                source_button.config(state=tk.DISABLED)  # Disable source button
        else:
            pressure_entry.config(state="normal")
            pressure_entry.delete(0, tk.END)
            pressure_entry.insert(0, "Invalid Data")
            pressure_entry.config(state="readonly")
            source_button.config(state=tk.DISABLED)  # Disable source button
    except Exception as e:
        pressure_entry.config(state="normal")
        pressure_entry.delete(0, tk.END)
        pressure_entry.insert(0, "Error")
        pressure_entry.config(state="readonly")
        source_button.config(state=tk.DISABLED)  # Disable source button
        print(f"Error updating pressure: {e}")

    # Schedule the next update
    root.after(500, update_pressure)  # Refresh every 0.5 seconds

# Function to clear data and reset the plot
def clear_data():
    """Clear the data arrays and reset the plot."""
    global timestamps, discharge_currents, beam_currents, pressure, ax, ax_pressure, canvas

    # Clear the data arrays
    timestamps.clear()
    discharge_currents.clear()
    beam_currents.clear()
    pressure.clear()

    # Clear the plot
    ax.clear()
    ax.set_title("Discharge and Beam Current Over Time")
    ax.set_xlabel("Time (MM:SS)")
    ax.set_ylabel("Current")
    ax.legend(loc="upper left")

    ax_pressure.clear()
    ax_pressure.set_ylabel("Pressure (mbar)", color="red")
    ax_pressure.tick_params(axis="y", labelcolor="red")
    ax_pressure.legend(loc="upper right")

    # Redraw the canvas
    canvas.draw()

    print("Data and plot cleared.")

def on_exit():
    """Close the data log file and exit the program."""
    global data_log_file
    if data_log_file:
        data_log_file.close()
        print("Data log file closed.")
    root.destroy()

# Create the main tkinter window
root = tk.Tk()
root.title("Ion Source Control")

# Create a frame for the parameter entries
frame = tk.Frame(root)
frame.pack(pady=10)

# Filament Current
filament_label = tk.Label(frame, text="Filament Current (A):")
filament_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
filament_entry = tk.Entry(frame)
filament_entry.grid(row=0, column=1, padx=5, pady=5)
filament_entry.insert(0, "7")  # Set initial value to 7

# Discharge Voltage
discharge_label = tk.Label(frame, text="Discharge Voltage (V):")
discharge_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
discharge_entry = tk.Entry(frame)
discharge_entry.grid(row=1, column=1, padx=5, pady=5)
discharge_entry.insert(0, "40")  # Set initial value to 40

# Beam Voltage
beam_label = tk.Label(frame, text="Beam Voltage (V):")
beam_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
beam_entry = tk.Entry(frame)
beam_entry.grid(row=2, column=1, padx=5, pady=5)
beam_entry.insert(0, "400")  # Set initial value to 400

# Accelerator Voltage
accelerator_label = tk.Label(frame, text="Accelerator Voltage (V):")
accelerator_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')
accelerator_entry = tk.Entry(frame)
accelerator_entry.grid(row=3, column=1, padx=5, pady=5)
accelerator_entry.insert(0, "60")  # Set initial value to 60

# Pressure Display
pressure_label = tk.Label(root, text="Pressure at Sensor 3 (mbar):")
pressure_label.pack(pady=5)
pressure_entry = tk.Entry(root, state="readonly", justify="center", width=20)
pressure_entry.pack(pady=5)

# Create a button to connect to the device
connect_button = tk.Button(root, text="Connect to Device", command=connect_to_device)
connect_button.pack(pady=10)

# Create a button to set the values
set_values_button = tk.Button(root, text="Set Values", command=set_values)
set_values_button.pack(pady=10)

# Create a toggle button for the reading loop
reading_button = tk.Button(root, text="Start Reading Values", command=toggle_reading)
reading_button.pack(pady=10)

# Add buttons to toggle the ion source
source_button = tk.Button(root, text="Turn Source On", command=toggle_source)
source_button.pack(pady=10)

# Create a toggle button for the beam current
beam_button = tk.Button(root, text="Turn Beam On", command=toggle_beam, state=tk.DISABLED)
beam_button.pack(pady=10)

# Create a button to open the plot window
plot_button = tk.Button(root, text="Open Plot Window", command=create_plot_window)
plot_button.pack(pady=10)

# Create a button to save the data
save_button = tk.Button(root, text="Save Data", command=save_data)
save_button.pack(pady=10)

# Add a button to clear the data
clear_button = tk.Button(root, text="Clear Data", command=clear_data)
clear_button.pack(pady=10)

# Create a frame for the sequence controls
sequence_frame = tk.Frame(root)
sequence_frame.pack(pady=10)

# On Time Entry
on_time_label = tk.Label(sequence_frame, text="Beam On Time (s):")
on_time_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
on_time_entry = tk.Entry(sequence_frame)
on_time_entry.grid(row=0, column=1, padx=5, pady=5)
on_time_entry.insert(0, "5")  # Default value

# Off Time Entry
off_time_label = tk.Label(sequence_frame, text="Beam Off Time (s):")
off_time_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
off_time_entry = tk.Entry(sequence_frame)
off_time_entry.grid(row=1, column=1, padx=5, pady=5)
off_time_entry.insert(0, "5")  # Default value

# Periods Entry
periods_label = tk.Label(sequence_frame, text="Number of Periods:")
periods_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
periods_entry = tk.Entry(sequence_frame)
periods_entry.grid(row=2, column=1, padx=5, pady=5)
periods_entry.insert(0, "3")  # Default value

# Create a button to start the sequence
sequence_button = tk.Button(sequence_frame, text="Start Sequence", command=create_sequence)
sequence_button.grid(row=3, column=0, columnspan=2, pady=10)

# Run initialize_data_logging on startup
root.after(50, initialize_data_logging)

# Run connect_to_device on startup
root.after(100, connect_to_device)

# Run connect_to_maxigauge on startup
root.after(150, connect_to_maxigauge)

# Run create_plot_window on startup
root.after(200, create_plot_window)  # Delay slightly to ensure the main window is initialized

# Run update_pressure on startup
root.after(500, update_pressure)

# Bind the on_exit function to the window close event
root.protocol("WM_DELETE_WINDOW", on_exit)

# Run the tkinter main loop
root.mainloop()