import sys
import matplotlib.pyplot as plt
import os
import numpy as np

# Define the sampling frequency to plot the data on a time-based axis.
# This value should match the fs variable in the C program.
SAMPLING_RATE_HZ = 1000.0

def plot_data(file_path):
    """
    Reads floating-point data from a file and plots it.

    Args:
        file_path (str): The path to the input text file containing filtered data.
    """
    data = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data.append(float(line.strip()))
                except ValueError:
                    # Skip any lines that are not valid numbers
                    continue
    except FileNotFoundError:
        print(f"Error: Input file not found at {file_path}")
        sys.exit(1)

    if not data:
        print("Error: No valid data found in the input file to plot.")
        sys.exit(1)
    
    # Generate the time array for the x-axis based on the sampling rate
    time_array = np.arange(len(data)) / SAMPLING_RATE_HZ

    # Get the base filename for the plot title and output file name
    base_name = os.path.basename(file_path)

    # Create the plot using the style from the live plotter
    plt.style.use('seaborn-v0_8-darkgrid')
    plt.figure(figsize=(12, 6))
    
    plt.plot(time_array, data, 'b-', label="Filtered Data")
    
    # Set plot titles and labels
    plt.title(f"Filtered Data Over Time - {base_name}", fontsize=16)
    plt.xlabel("Time (s)", fontsize=12)
    plt.ylabel("Value", fontsize=12)
    plt.legend()
    plt.grid(True)
    
    # Adjust Y-limits dynamically
    min_y, max_y = min(data), max(data)
    padding_y = (max_y - min_y) * 0.1
    plt.ylim(min_y - padding_y, max_y + padding_y)

    # Create a directory to save the plot if it doesn't exist
    output_dir = "plots"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the plot with a descriptive filename
    plot_file = os.path.join(output_dir, f"plot_static_{base_name.replace('.txt', '.png')}")
    plt.savefig(plot_file)
    
    print(f"Plot saved to {plot_file}")
    
    # Show the plot
    plt.show()

if __name__ == "__main__":
    # Hardcode the path to the data file instead of using a command line argument.
    # Replace this with the actual path to your filtered data file.
    data_file_path = "output/filtered_535g20250502pm427ms20hz0.txt"
    plot_data(data_file_path)
