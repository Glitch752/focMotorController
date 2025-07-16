import dearpygui.dearpygui as dpg

class TimeSeriesPlot:
    """Manages a time series plot with fixed buffer size."""
    
    history_length: float
    show_latest: bool
    times: list[float]
    series_data: dict[str, list[float]]
    series_handles: dict[str, str | int]
    plot: int | str
    x_axis: int | str
    y_axis: int | str
    
    def __init__(self, label, y_label, history_length=0.5, show_latest=True, height=400, width=1000, default_visible=True):
        self.history_length = history_length
        self.show_latest = show_latest
        self.times = []
        self.series_data = {}
        self.series_handles = {}
        
        with dpg.collapsing_header(label=label, default_open=default_visible):
            self.plot = dpg.add_plot(label=label, height=height, width=width)
            
            dpg.add_plot_legend(parent=self.plot)    
            
            self.x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", parent=self.plot)
            self.y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_label, parent=self.plot)
            
            if self.show_latest:
                dpg.set_axis_limits(self.x_axis, 0, history_length)
    
    def set_y_range(self, min: float, max: float):
        dpg.set_axis_limits(self.y_axis, min, max)
    
    def add_series(self, name, color=None):
        """Add a new data series to the plot."""
        self.series_data[name] = []
        
        series_id = dpg.add_line_series([], [], label=name, parent=self.y_axis)
        self.series_handles[name] = series_id
        return series_id
    
    def add_data_point(self, time_point, data_dict):
        """Add a data point to the plot, where data_dict maps series names to values."""
        
        # Add time point if needed
        if not self.times or self.times[-1] != time_point:
            self.times.append(time_point)
        
        # Add data points for each series
        for name, value in data_dict.items():
            if name not in self.series_data:
                self.add_series(name)
            self.series_data[name].append(value)
        
        # Keep the series length within the history length
        while len(self.times) > 0 and (self.times[-1] - self.times[0]) > self.history_length:
            self.times.pop(0)
            for series in self.series_data.values():
                series.pop(0)
    
    def update_plot(self):
        """Update all series in the plot with current data."""
        if not self.times:
            return
            
        for name, series_id in self.series_handles.items():
            dpg.set_value(series_id, [self.times, self.series_data[name]])
            
        if self.show_latest:
            dpg.set_axis_limits(self.x_axis, self.times[0], self.times[0] + self.history_length)