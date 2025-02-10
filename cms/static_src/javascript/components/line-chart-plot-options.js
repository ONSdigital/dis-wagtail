class LineChartPlotOptions {
  static plotOptions() {
    return this.plotOptions;
  }

  constructor() {
    this.plotOptions = {
      line: {
        lineWidth: 3, // Sets the line thickness to 3px
        linecap: 'round',
        marker: {
          enabled: false,
          radius: 4, // Sets circle radius to 4px (8px diameter)
          // currently the marker style is configurable but this may change
          // symbol: 'circle',
        },
        states: {
          hover: {
            lineWidth: 3, // Maintain line width on hover
          },
        },
      },
    };
  }
}

export default LineChartPlotOptions;
