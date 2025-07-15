import dearpygui.dearpygui as dpg
from .main import SAMPLE_SEPARATION, TIMESTEP

class TimeSeriesPlot:
    """Manages a time series plot with fixed buffer size."""
    
    max_values: int
    show_latest: bool
    times: list[float]
    series_data: dict[str, list[float]]
    series_handles: dict[str, str | int]
    visible: bool
    plot: int | str
    x_axis: int | str
    y_axis: int | str
    
    def __init__(self, label, y_label, max_values=500, show_latest=True, height=400, width=1000, visible=True):
        self.max_values = max_values
        self.show_latest = show_latest
        self.times = []
        self.series_data = {}
        self.series_handles = {}
        self.visible = visible
        
        if visible:
            self.plot = dpg.add_plot(label=label, height=height, width=width)
            
            dpg.add_plot_legend(parent=self.plot)    
            
            self.x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", parent=self.plot)
            self.y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_label, parent=self.plot)
            
            if self.show_latest:
                dpg.set_axis_limits(self.x_axis, 0, max_values * TIMESTEP * SAMPLE_SEPARATION)
    
    def set_y_range(self, min: float, max: float):
        if self.visible:
            dpg.set_axis_limits(self.y_axis, min, max)
    
    def add_series(self, name, color=None):
        """Add a new data series to the plot."""
        self.series_data[name] = []
        if self.visible:
            series_id = dpg.add_line_series([], [], label=name, parent=self.y_axis)
            self.series_handles[name] = series_id
            return series_id
            
        return None
    
    def add_data_point(self, time_point, data_dict):
        """Add a data point to the plot, where data_dict maps series names to values."""
        if not self.visible:
            return
            
        # Add time point if needed
        if len(self.times) < self.max_values:
            self.times.append(time_point)
        else:
            self.times.pop(0)
            self.times.append(time_point)
        
        # Add data points for each series
        for name, value in data_dict.items():
            if name in self.series_data:
                if len(self.series_data[name]) < self.max_values:
                    self.series_data[name].append(value)
                else:
                    self.series_data[name].pop(0)
                    self.series_data[name].append(value)
    
    def update_plot(self):
        """Update all series in the plot with current data."""
        if not self.visible or not self.times:
            return
            
        for name, series_id in self.series_handles.items():
            dpg.set_value(series_id, [self.times, self.series_data[name]])
            
        if self.show_latest:
            dpg.set_axis_limits(self.x_axis, self.times[0], self.times[0] + self.max_values * TIMESTEP * SAMPLE_SEPARATION)