import IframeResize from './components/iframe-resize';
import detailsToggle from './components/details';
import HighchartsBaseChart from './components/highcharts-base-chart';
import '../sass/main.scss';

function initComponent(ComponentClass) {
  const items = document.querySelectorAll(ComponentClass.selector());
  items.forEach((item) => new ComponentClass(item));
}

document.addEventListener('DOMContentLoaded', () => {
  initComponent(IframeResize);
  initComponent(detailsToggle);
  initComponent(HighchartsBaseChart);
});
