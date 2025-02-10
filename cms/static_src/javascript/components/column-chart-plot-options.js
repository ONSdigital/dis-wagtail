class ColumnChartPlotOptions {
  static plotOptions() {
    return this.plotOptions;
  }

  constructor() {
    this.plotOptions = {
      column: {
        groupPadding: 0.2,
        borderWidth: 0,
        borderRadius: 0,
      },
    };
  }
}

export default ColumnChartPlotOptions;
