import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QSlider, QFileDialog, QCheckBox, QComboBox, QTableWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from PyQt5.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene
from matplotlib.patches import Circle
from scipy.signal import freqz, zpk2tf, butter, cheby1, cheby2, ellip, bessel,freqz_zpk
from scipy.signal import zpk2tf
import numpy as np
from scipy.signal import zpk2sos
import csv
from PyQt5.QtWidgets import QDialog
import sys
import numpy as np  
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QSlider
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.signal import zpk2tf, lfilter

import numpy as np
from scipy.signal import butter, cheby1, ellip, bessel, zpk2tf, tf2zpk

class FilterDesignApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Digital Filter Design")
        self.setGeometry(100, 100, 1200, 800)

        # Main widget and layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        self.tab_widget = QTabWidget()

        # Add it to your main layout
        self.main_layout.addWidget(self.tab_widget)

        # Initialize data and UI components
        self.zeros = []
        self.poles = []
        self.history = []  # Undo/Redo history
        self.redo_stack = []
        self.unit_circle_radius = 1
        self.sample_rate = 1000
        self.signal = np.random.randn(10000)  # Example lengthy signal
        self.filtered_signal = np.zeros_like(self.signal)
        self.index = 0  # Current processing index

        self.speed = 10  # Default points per second
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_next_point)

        self.selected_point = None
        self.selected_type = None

        self.all_pass_filters = {
            "Butterworth": self.get_butterworth_filter,
            "Chebyshev Type I": self.get_chebyshev_filter,
            "Elliptic": self.get_elliptic_filter,
            "Bessel": self.get_bessel_filter
        }
        
        self.all_pass_filters_libraries = []
        
        self.active_all_pass_filters = [] # for storing active all pass filters 

        self.initialize_ui()

    def create_plot_canvas(self):
        fig, ax = plt.subplots()
        fig.tight_layout()
        canvas = FigureCanvas(fig)

        # Connect mouse events for dragging
        canvas.mpl_connect('button_press_event', self.on_click)
        canvas.mpl_connect('button_release_event', self.on_release)
        canvas.mpl_connect('motion_notify_event', self.on_motion)

        return canvas, ax

    def initialize_ui(self):
        # Layouts for different sections
        self.graph_layout = QHBoxLayout()
        self.controls_layout = QVBoxLayout()
        self.main_layout.addLayout(self.graph_layout)
        self.main_layout.addLayout(self.controls_layout)
         # Graph2 Layout
        self.graph_layout2 = QHBoxLayout()
        self.main_layout.addLayout(self.graph_layout2)

        # Z-Plane Plot
        self.z_plane_canvas, self.z_plane_ax = self.create_plot_canvas()
        self.graph_layout.addWidget(self.z_plane_canvas)

        # Frequency Response Plot
        self.freq_response_canvas, self.freq_response_ax = self.create_plot_canvas()
        self.graph_layout.addWidget(self.freq_response_canvas)

        # Phase Response Plot
        self.phase_response_canvas, self.phase_response_ax = self.create_plot_canvas()
        self.graph_layout.addWidget(self.phase_response_canvas)



        # Original Signal Plot
        self.original_fig, self.original_ax = plt.subplots()
        self.original_canvas = FigureCanvas(self.original_fig)
        self.original_ax.set_title("Original Signal")
        self.original_ax.set_xlim(0, 1000)
        self.original_ax.set_ylim(-3, 3)
        self.original_plot, = self.original_ax.plot([], [], color="blue")
        self.graph_layout2.addWidget(self.original_canvas)

        # Filtered Signal Plot
        self.filtered_fig, self.filtered_ax = plt.subplots()
        self.filtered_canvas = FigureCanvas(self.filtered_fig)
        self.filtered_ax.set_title("Filtered Signal")
        self.filtered_ax.set_xlim(0, 1000)
        self.filtered_ax.set_ylim(-3, 3)
        self.filtered_plot, = self.filtered_ax.plot([], [], color="green")
        self.graph_layout2.addWidget(self.filtered_canvas)

        # Controls Section
        self.add_buttons()
        self.add_sliders()
        self.add_checkboxes_and_comboboxes()

        # All-Pass filter controls

        self.enable_all_pass_checkbox = QCheckBox("Enable All-Pass Filters")
        
        self.controls_layout.addWidget(self.enable_all_pass_checkbox)
        
        self.all_pass_combobox = QComboBox()
        self.all_pass_combobox.addItems(self.all_pass_filters.keys())
        # self.all_pass_combobox.currentIndexChanged.connect(self.add_to_main)
        self.controls_layout.addWidget(QLabel("All-Pass Filters"))
        self.controls_layout.addWidget(self.all_pass_combobox)

        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self.preview_all_pass_filter)
        self.controls_layout.addWidget(self.preview_button)

        self.a_slider = QSlider(Qt.Horizontal)
        self.a_slider.setMinimum(0)
        self.a_slider.setMaximum(100)  # Set max to 100 for more precision
        self.a_slider.setValue(50)
        
        self.a_slider.valueChanged.connect(self.updateLabel)
        self.value_label = QLabel('"A" Value : 0.50', self)
        self.controls_layout.addWidget(self.value_label)
        self.controls_layout.addWidget(self.a_slider)


        self.add_all_pass_button = QPushButton("Add All-Pass Filter")
        self.add_all_pass_button.clicked.connect(self.add_all_pass_filter)
        self.controls_layout.addWidget(self.add_all_pass_button)
        
        

        

        # self.add_editable_table()
        self.plot_z_plane()
        self.plot_frequency_response()
        self.plot_phase_response()
    


    def preview_all_pass_filter(self):
        # Create and show the new window when preview is clicked
        new_window = PreviewWindow(self)
        new_window.exec_()

        

    def updateLabel(self, value):
        self.value_label.setText(f'"A" Value : {value / 100:.2f}')
        

    # def add_all_pass_filter(self):
    #     selected_filter = self.all_pass_combobox.currentText()
    #     if selected_filter in self.all_pass_filters:
    #         self.active_all_pass_filters.append(self.all_pass_filters[selected_filter])
    #         self.plot_z_plane()
    #         self.plot_frequency_response()
    #         self.plot_phase_response()

    # def toggle_all_pass_filters(self):
    #     if self.enable_all_pass_checkbox.isChecked():
    #         # Combine All-Pass filters with the main filter
    #         self.plot_z_plane()
    #         self.plot_frequency_response()
    #         self.plot_phase_response()
    #     else:
    #         # Plot only the main filter
    #         self.plot_z_plane()
    #         self.plot_frequency_response()
    #         self.plot_phase_response()
            
    # def apply_selected_all_pass_filter(self, index):
    #     # Get the selected filter function
    #     filter_name = self.all_pass_combobox.currentText()
    #     if filter_name in self.all_pass_filters:
    #         zeros, poles = self.all_pass_filters[filter_name]()
    #         # Add to existing poles and zeros
    #         self.poles.extend(poles)
    #         self.zeros.extend(zeros)
    #         # Update all plots
    #         self.plot_z_plane()
    #         self.plot_frequency_response()
    #         self.plot_phase_response()

    def get_butterworth_filter(self):
        b, a = butter(1, 0.5, analog=False)
        return self.extract_zeros_poles(b, a)

    def get_chebyshev_filter(self):
        b, a = cheby1(1, 1, 0.5, analog=False)
        return self.extract_zeros_poles(b, a)

    def get_elliptic_filter(self):
        b, a = ellip(1, 1, 10, 0.5, analog=False)
        return self.extract_zeros_poles(b, a)

    def get_bessel_filter(self):
        b, a = bessel(1, 0.5, analog=False)
        return self.extract_zeros_poles(b, a)

    def extract_zeros_poles(self, b, a):
        z, p, k = tf2zpk(b, a)  # Correct function to extract zeros, poles, and gain
        return z, p

    def add_buttons(self):
        # Horizontal layout for buttons
        self.buttons_layout = QHBoxLayout()

        # Add buttons for filter operations
        self.add_zero_button = QPushButton("Add Zero")
        self.add_pole_button = QPushButton("Add Pole")
        self.clear_zeros_button = QPushButton("Clear Zeros")
        self.clear_poles_button = QPushButton("Clear Poles")
        self.clear_all_button = QPushButton("Clear All")
        self.swap_zeros_poles_button = QPushButton("Swap Zeros/Poles")
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        self.save_filter_button = QPushButton("Save Filter")
        self.load_filter_button = QPushButton("Load Filter")
        self.generate_c_code_button = QPushButton("Generate C Code")
        self.export_realization_button = QPushButton("Export Realization")

        # Add buttons to layout
        buttons = [
            self.add_zero_button, self.add_pole_button, self.clear_zeros_button,
            self.clear_poles_button, self.clear_all_button, self.swap_zeros_poles_button,
            self.undo_button, self.redo_button, self.save_filter_button,
            self.load_filter_button, self.generate_c_code_button, self.export_realization_button
        ]
        for button in buttons:
            self.buttons_layout.addWidget(button)

        self.controls_layout.addLayout(self.buttons_layout)

        # Connect buttons to actions
        self.add_zero_button.clicked.connect(lambda: self.add_element("zero"))
        self.add_pole_button.clicked.connect(lambda: self.add_element("pole"))
        self.clear_zeros_button.clicked.connect(self.clear_zeros)
        self.clear_poles_button.clicked.connect(self.clear_poles)
        self.clear_all_button.clicked.connect(self.clear_all)
        self.swap_zeros_poles_button.clicked.connect(self.swap_zeros_poles)
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.save_filter_button.clicked.connect(self.save_filter)
        self.load_filter_button.clicked.connect(self.load_filter)
        self.generate_c_code_button.clicked.connect(self.generate_c_code)
        self.export_realization_button.clicked.connect(self.export_realization)

         # Start/Stop Buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        self.start_button.clicked.connect(self.start_filtering)
        self.stop_button.clicked.connect(self.stop_filtering)

        self.controls_layout.addWidget(self.start_button)
        self.controls_layout.addWidget(self.stop_button)


    def add_sliders(self):
        # Speed Slider
        speed_label = QLabel("Filtering Speed (Points per Second):")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setValue(self.speed)
        self.speed_slider.valueChanged.connect(self.update_speed)

        self.controls_layout.addWidget(speed_label)
        self.controls_layout.addWidget(self.speed_slider)

    def add_checkboxes_and_comboboxes(self):
        self.add_conjugates_checkbox = QCheckBox("Add Conjugates")
        self.controls_layout.addWidget(self.add_conjugates_checkbox)

        self.filter_library_combobox = QComboBox()
        self.filter_library_combobox.addItems([
            "Butterworth LPF", "Butterworth HPF", "Chebyshev I LPF", "Chebyshev I HPF",
            "Elliptic LPF", "Elliptic HPF", "Bessel LPF", "Bessel HPF","Chebyshev II LPF","Chebyshev II HPF"
        ])
        self.filter_library_combobox.currentIndexChanged.connect(self.load_predefined_filter)

        self.controls_layout.addWidget(QLabel("Filter Library"))
        self.controls_layout.addWidget(self.filter_library_combobox)


    def add_element(self, element_type):
        """Adds a new zero or pole with optional conjugate pair."""
        new_element = 0.5 + 0j if element_type == "zero" else 0.7 + 0j
        target_list = self.zeros if element_type == "zero" else self.poles

        # Add the new element
        target_list.append(new_element)

        # Add conjugate if checkbox is checked and the element is not purely real
        if self.add_conjugates_checkbox.isChecked() and new_element.imag != 0:
            target_list.append(new_element.conjugate())

        # Update the table and visualizations
        # self.update_table()
        self.save_to_history()
        self.plot_z_plane()
        self.plot_frequency_response()
        self.plot_phase_response()



    def export_realization(self):
        try:
            # Get coefficients from realization methods
            cascade_coefficients = self.cascade_realization()
            direct_form_coefficients = self.direct_form_ii_realization()

            # Ensure both methods return dictionaries
            if not isinstance(cascade_coefficients, dict) or not isinstance(direct_form_coefficients, dict):
                raise ValueError("Realization methods must return dictionaries.")

            # Combine coefficients
            coefficients = cascade_coefficients.copy()
            coefficients.update(direct_form_coefficients)

            # Export coefficients to a CSV file
            filename = "filter_coefficients.csv"
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                for key, value in coefficients.items():
                    # Ensure value is iterable for CSV writing
                    if isinstance(value, (list, tuple)):
                        writer.writerow([key] + list(value))
                    else:
                        writer.writerow([key, value])

            print(f"Filter coefficients exported to {filename}")
            QMessageBox.information(self, "Export", "Filter realization exported successfully!")

        except Exception as e:
            print(f"Error during export: {e}")
            QMessageBox.critical(self, "Export Error", f"An error occurred: {e}")


    def on_click(self, event):
        if event.inaxes != self.z_plane_ax:
            return

        # Check if the user right-clicked (delete action)
        if event.button == 3:  # Right-click
            # Check main filter zeros
            for idx, z in enumerate(self.zeros):
                if abs(z.real - event.xdata) < 0.05 and abs(z.imag - event.ydata) < 0.05:
                    del self.zeros[idx]  # Delete the zero
                    self.save_to_history()
                    self.plot_z_plane()
                    self.plot_frequency_response()
                    self.plot_phase_response()
                    return

            # Check main filter poles
            for idx, p in enumerate(self.poles):
                if abs(p.real - event.xdata) < 0.05 and abs(p.imag - event.ydata) < 0.05:
                    del self.poles[idx]  # Delete the pole
                    self.save_to_history()
                    self.plot_z_plane()
                    self.plot_frequency_response()
                    self.plot_phase_response()
                    return

            # Check All-Pass filters' zeros and poles
            # for apf_idx, apf in enumerate(self.active_all_pass_filters):
            #     for idx, z in enumerate(apf["zeros"]):
            #         if abs(z.real - event.xdata) < 0.05 and abs(z.imag - event.ydata) < 0.05:
            #             self.selected_point = idx
            #             self.selected_type = "all_pass_zero"
            #             self.selected_apf_idx = apf_idx  # Store the index of the selected All-Pass filter
            #             return
            #     for idx, p in enumerate(apf["poles"]):
            #         if abs(p.real - event.xdata) < 0.05 and abs(p.imag - event.ydata) < 0.05:
            #             self.selected_point = idx
            #             self.selected_type = "all_pass_pole"
            #             self.selected_apf_idx = apf_idx  # Store the index of the selected All-Pass filter
            #             return

        for idx, z in enumerate(self.zeros):
            if abs(z.real - event.xdata) < 0.05 and abs(z.imag - event.ydata) < 0.05:
                self.selected_point = idx
                self.selected_type = "zero"
                return
        for idx, p in enumerate(self.poles):
            if abs(p.real - event.xdata) < 0.05 and abs(p.imag - event.ydata) < 0.05:
                self.selected_point = idx
                self.selected_type = "pole"
                return

    def on_motion(self, event):
        if event.inaxes != self.z_plane_ax or self.selected_point is None:
            return

        new_position = complex(event.xdata, event.ydata)
        if abs(new_position) > 1.5:  # Boundary check
            return

        if self.selected_type == "zero":
            self.zeros[self.selected_point] = new_position
        elif self.selected_type == "pole":
            self.poles[self.selected_point] = new_position
        # elif self.selected_type == "all_pass_zero":
        #     self.active_all_pass_filters[self.selected_apf_idx]["zeros"][self.selected_point] = new_position
        # elif self.selected_type == "all_pass_pole":
        #     self.active_all_pass_filters[self.selected_apf_idx]["poles"][self.selected_point] = new_position

        self.plot_z_plane()
        self.plot_frequency_response()
    
    def on_release(self, event):
        if self.selected_point is not None:
            self.save_to_history()
        self.selected_point = None
        self.selected_type = None
        self.selected_apf_idx = None  # Reset the selected All-Pass filter index

    def clear_zeros(self):
        self.zeros.clear()
        self.save_to_history()
        self.plot_z_plane()
        self.plot_frequency_response()

    def clear_poles(self):
        self.poles.clear()
        self.save_to_history()
        self.plot_z_plane()
        self.plot_frequency_response()

    def clear_all(self):
        self.zeros.clear()
        self.poles.clear()
        self.save_to_history()
        self.plot_z_plane()
        self.plot_frequency_response()

    def swap_zeros_poles(self):
        self.zeros, self.poles = self.poles, self.zeros
        self.save_to_history()
        self.plot_z_plane()
        self.plot_frequency_response()
    def direct_form_ii_realization(self):

        b, a = zpk2tf(self.zeros, self.poles, 1)

        # Exporting filter coefficients
        coefficients = {"Numerator": b.tolist(), "Denominator": a.tolist()}
        return coefficients
    def cascade_realization(self):
        # Convert to second-order sections
        sos = zpk2sos(self.zeros,self. poles, 1)

        # Exporting SOS matrix
        sos_list = sos.tolist()
        return {"SOS": sos_list}

    def undo(self):
        if self.history:
            self.redo_stack.append((self.zeros.copy(), self.poles.copy()))
            self.zeros, self.poles = self.history.pop()
            self.plot_z_plane()
            self.plot_frequency_response()

    def redo(self):
        if self.redo_stack:
            self.history.append((self.zeros.copy(), self.poles.copy()))
            self.zeros, self.poles = self.redo_stack.pop()
            self.plot_z_plane()
            self.plot_frequency_response()

    def save_to_history(self):
        self.history.append((self.zeros.copy(), self.poles.copy()))
        if len(self.history) > 50:  # Limit history size
            self.history.pop(0)

    def save_filter(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Filter", "", "CSV Files (*.csv)")
        if file_name:
            with open(file_name, "w") as file:
                file.write("zeros,poles\n")
                file.write("{}\n".format(",".join(map(str, self.zeros))))
                file.write("{}\n".format(",".join(map(str, self.poles))))

    def load_filter(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Filter", "", "CSV Files (*.csv)")
        if file_name:
            with open(file_name, "r") as file:
                lines = file.readlines()
                self.zeros = [complex(z) for z in lines[1].strip().split(",")]
                self.poles = [complex(p) for p in lines[2].strip().split(",")]
            self.plot_z_plane()
            self.plot_frequency_response()

    def generate_c_code(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Generate C Code", "", "C Files (*.c)")
        if file_name:
            with open(file_name, "w") as file:
                file.write("// C Code for Digital Filter\n")
                file.write("// Zeros: {}\n".format(self.zeros))
                file.write("// Poles: {}\n".format(self.poles))

    def add_all_pass_filter(self):
    # Ensure that the checkbox is checked before proceeding
        
        if self.enable_all_pass_checkbox.isChecked():
            # Get the value of 'a' from the slider
            a = self.a_slider.value() / 100  # Scale to [0, 1]

            # Define the all-pass filter poles and zeros
            # For simplicity, assuming a single pair of complex conjugate poles/zeros based on 'a'
            # Customize this if you want to add more poles/zeros depending on the filter design.
            all_pass_zero = complex(a, 0)
            all_pass_pole = complex(1/a, 0)

            # Add the all-pass filter's zero and pole
            self.zeros.append(all_pass_zero)
            self.poles.append(all_pass_pole)

            # Update the pole-zero diagram and frequency response after adding the filter
            self.plot_z_plane()  # Update pole-zero diagram
            self.plot_frequency_response()  # Update frequency response
            self.plot_phase_response()  # Update phase response

        else:
            print("Enable the all-pass filter first.")
        
    def plot_z_plane(self):
        # Clear previous plot
        self.z_plane_ax.clear()
        self.z_plane_ax.add_artist(Circle((0, 0), self.unit_circle_radius, color="black", fill=False))

        # Plot main filter zeros/poles, including the all-pass filter
        self.z_plane_ax.scatter([z.real for z in self.zeros], [z.imag for z in self.zeros], color="blue", label="Zeros")
        self.z_plane_ax.scatter([p.real for p in self.poles], [p.imag for p in self.poles], color="red", label="Poles", marker='x')

        self.z_plane_ax.set_xlim([-3, 3])
        self.z_plane_ax.set_ylim([-1.5, 1.5])
        self.z_plane_ax.axhline(0, color='gray', linestyle='--', linewidth=0.5)
        self.z_plane_ax.axvline(0, color='gray', linestyle='--', linewidth=0.5)
        self.z_plane_ax.set_aspect('equal', adjustable='box')
        self.z_plane_ax.legend()
        self.z_plane_canvas.draw()

    def plot_frequency_response(self):
        self.freq_response_ax.clear()

        if self.zeros or self.poles:
            # Calculate frequency response based on updated zeros and poles
            b, a = zpk2tf(self.zeros, self.poles, 1)
            w, h = freqz(b, a, worN=8000)
            self.freq_response_ax.plot(w / np.pi, 20 * np.log10(abs(h)), color="blue", label="Magnitude Response")
            self.freq_response_ax.set_title("Frequency Response")
            self.freq_response_ax.set_xlabel("Normalized Frequency (xπ rad/sample)")
            self.freq_response_ax.set_ylabel("Magnitude (dB)")
            self.freq_response_ax.grid(True)
        self.freq_response_canvas.draw()

    def plot_phase_response(self):
        # Recalculate phase response based on updated zeros and poles
        w, h = freqz_zpk(self.zeros, self.poles, 1)
        self.phase_response_ax.clear()
        self.phase_response_ax.plot(w / np.pi, np.angle(h), label="Phase Response")
        self.phase_response_ax.set_title("Phase Response")
        self.phase_response_ax.set_xlabel("Normalized Frequency")
        self.phase_response_ax.set_ylabel("Phase (radians)")
        self.phase_response_ax.legend()
        self.phase_response_canvas.draw()


    def load_predefined_filter(self, index):
        predefined_filters = {
            0: butter(4, 0.2, btype='low', output='zpk'),
            1: butter(4, 0.2, btype='high', output='zpk'),
            2: cheby1(4, 1, 0.2, btype='low', output='zpk'),
            3: cheby1(4, 1, 0.2, btype='high', output='zpk'),
            4: ellip(4, 1, 40, 0.2, btype='low', output='zpk'),
            5: ellip(4, 1, 40, 0.2, btype='high', output='zpk'),
            6: bessel(4, 0.2, btype='low', output='zpk'),
            7: bessel(4, 0.2, btype='high', output='zpk'),
            8: cheby2(4, 20, 0.3, btype='low', output='zpk'),
            9: cheby2(4, 20, 0.3, btype='high', output='zpk')
        }
        if index in predefined_filters:
            z, p, _ = predefined_filters[index]
            self.zeros = list(z)
            self.poles = list(p)
            self.plot_z_plane()
            self.plot_frequency_response()
            self.plot_phase_response()

    def update_speed(self, value):
        self.speed = value
        if self.timer.isActive():
            self.timer.setInterval(1000 // self.speed)

    def start_filtering(self):
        self.timer.start(1000 // self.speed)

    def stop_filtering(self):
        self.timer.stop()

    def compute_filter_coefficients(self):
        # Compute filter coefficients from zeros and poles
        if self.zeros or self.poles:
            b, a = zpk2tf(self.zeros, self.poles, 1)
        else:
            b, a = [1.0], [1.0]  # Default passthrough filter
        print(b)
        print(a)
        return b, a

    def process_next_point(self):
        if self.index >= len(self.signal):
            self.stop_filtering()
            return

        # Get filter coefficients
        b, a = self.compute_filter_coefficients()

        # Apply filtering point-by-point
        self.filtered_signal[self.index] = lfilter(b, a, [self.signal[self.index]])[0]

        # Update plots
        self.update_plots()
        self.index += 1

    def update_plots(self):
        # Update original signal plot
        start = max(0, self.index - 1000)
        self.original_plot.set_data(np.arange(start, self.index), self.signal[start:self.index])
        self.original_ax.set_xlim(start, self.index)
        self.original_canvas.draw()

        # Update filtered signal plot
        self.filtered_plot.set_data(np.arange(start, self.index), self.filtered_signal[start:self.index])
        self.filtered_ax.set_xlim(start, self.index)
        self.filtered_canvas.draw()

class PreviewWindow(QDialog):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window  # Store the reference to the main window
        self.setWindowTitle("Preview Window")   
        self.setGeometry(150, 150, 800, 600)

        # Layout for the new window
        layout = QVBoxLayout()

        # Create a horizontal layout for the plots
        plot_layout = QHBoxLayout()

        # Create the canvas and axes for the pole-zero and phase plots
        self.z_plane_fig, self.z_plane_ax = plt.subplots()
        self.z_plane_canvas = FigureCanvas(self.z_plane_fig)
        plot_layout.addWidget(self.z_plane_canvas)

        self.phase_fig, self.phase_ax = plt.subplots()
        self.phase_canvas = FigureCanvas(self.phase_fig)
        plot_layout.addWidget(self.phase_canvas)

        layout.addLayout(plot_layout)

        # Example content for the new window
        label = QLabel("Pole-Zero and Phase Response Plots")
        layout.addWidget(label)

        # Add a button to close the window
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)  # Close the window when clicked
        layout.addWidget(close_button)

        # Add a button to close the window
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_to_main)  # Close the window when clicked
        layout.addWidget(add_button)


        self.setLayout(layout)

        # Plot the initial pole-zero and phase response using methods from the main window
        self.plot_pole_zero()
        self.plot_phase_response()
    
    def add_to_main(self):
        # Get the selected filter function
        filter_name = self.main_window.all_pass_combobox.currentText()
        if filter_name in self.main_window.all_pass_filters:
            zeros, poles = self.main_window.all_pass_filters[filter_name]()
            # Add to existing poles and zeros
            self.main_window.poles.extend(poles)
            self.main_window.zeros.extend(zeros)
            # Update all plots
            self.main_window.plot_z_plane()
            self.main_window.plot_frequency_response()
            self.main_window.plot_phase_response()


    def plot_pole_zero(self):
            # Get the selected filter from the combobox in the main window
        selected_filter = self.main_window.all_pass_combobox.currentText()

        # Get zeros and poles for the selected filter
        if selected_filter == 'Butterworth':
            zeros, poles = self.main_window.get_butterworth_filter()
        elif selected_filter == 'Chebyshev Type I':
            zeros, poles = self.main_window.get_chebyshev_filter()
        elif selected_filter == 'Elliptic':
            zeros, poles = self.main_window.get_elliptic_filter()
        elif selected_filter == 'Bessel':
            zeros, poles = self.main_window.get_bessel_filter()
        else:
            return  # If no filter is selected, do nothing

        # Plot poles and zeros
        self.z_plane_ax.cla()  # Clear previous plots
        self.z_plane_ax.plot([z.real for z in zeros], [z.imag for z in zeros], 'bo', label="Zeros")
        self.z_plane_ax.plot([p.real for p in poles], [p.imag for p in poles], 'rx', label="Poles")

        # Draw unit circle
        unit_circle = plt.Circle((0, 0), 1, color='g', fill=False, linestyle='--')
        self.z_plane_ax.add_artist(unit_circle)

        # Set the limits to ensure the unit circle is fully visible
        self.z_plane_ax.set_xlim(-1.5, 1.5)
        self.z_plane_ax.set_ylim(-1.5, 1.5)

        # Add labels and title
        self.z_plane_ax.set_title('Pole-Zero Plot')
        self.z_plane_ax.set_xlabel('Real')
        self.z_plane_ax.set_ylabel('Imaginary')
        self.z_plane_ax.axhline(0, color='black', linewidth=1)
        self.z_plane_ax.axvline(0, color='black', linewidth=1)

        # Display legend
        self.z_plane_ax.legend()

        # Redraw the canvas
        self.z_plane_canvas.draw()

    def plot_phase_response(self):
        # Get the selected filter from the combobox in the main window
        selected_filter = self.main_window.all_pass_combobox.currentText()

        # Get transfer function for the selected filter
        if selected_filter == 'Butterworth':
            b, a = self.main_window.get_butterworth_filter()
        elif selected_filter == 'Chebyshev Type I':
            b, a = self.main_window.get_chebyshev_filter()
        elif selected_filter == 'Elliptic':
            b, a = self.main_window.get_elliptic_filter()
        elif selected_filter == 'Bessel':
            b, a = self.main_window.get_bessel_filter()
        else:
            return  # If no filter is selected, do nothing

        # Plot the phase response
        w, h = freqz_zpk(b, a,1)
        self.phase_ax.cla()
        self.phase_ax.plot(w, np.angle(h), label="Phase Response")
        
        self.phase_ax.set_title('Phase Response')
        self.phase_ax.set_xlabel('Frequency (rad/sample)')
        self.phase_ax.set_ylabel('Phase (radians)')
        self.phase_ax.legend()

        self.phase_canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FilterDesignApp()
    window.show()
    sys.exit(app.exec_())
