import ChartConstants from './chart-constants';

class BarChartPlotOptions {
  static plotOptions() {
    return this.plotOptions;
  }

  constructor() {
    const constants = ChartConstants.constants();
    this.plotOptions = {
      bar: {
        // Set the width of the bars to be 30px and the spacing between them to be 10px
        pointWidth: 30, // Fixed bar height
        groupPadding: 0, // No padding between groups
        pointPadding: 0, // No padding within groups
        borderWidth: 0,
        borderRadius: 0,
        spacing: [10, 0, 0, 0], // [top, right, bottom, left] spacing between bars
        // Set the data labels to be enabled and positioned outside the bars
        // We can add custom formatting on each chart to move the labels inside the bars if the bar is wide enough
        dataLabels: {
          enabled: true,
          inside: false,
          style: {
            textOutline: 'none',
            // there is no semibold font weight available in the design system fonts, so we use 400 instead
            fontWeight: '400',
            color: constants.labelColor,
            fontSize: constants.mobileFontSize,
          },
        },
      },
    };
  }
}

export default BarChartPlotOptions;
