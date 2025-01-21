/* global jspreadsheet */
class TableDefinition extends window.wagtailStreamField.blocks.StructBlockDefinition {
  render(placeholder, prefix, initialState, initialError) {

    /* Hide TextField and display table instead */
    const block = super.render(placeholder, prefix, initialState, initialError);
    const dataSetField = document.getElementById(`${prefix}-table_data`);
    const table = document.createElement('div');
    table.setAttribute("id", `${prefix}-dataset-table`)
    dataSetField.parentNode.insertBefore( table, dataSetField.nextSibling );
    dataSetField.style.display = 'none';

    const tableTypeField = document.getElementById(`${prefix}-table_type`);
    if(tableTypeField.options.length === 1){
      const typeField = tableTypeField.closest('[data-contentpath=table_type]');
      typeField.style.display = 'none';
    }

    /* Update TextField on changes */
    let spread = null;
    const changed = () => {
      if (spread !== null) {
        dataSetField.value = `{"data": ${JSON.stringify(spread.getData())}, "style": ${JSON.stringify(spread.getStyle())}}`;
      }
    }

    const options = {
      tableOverflow: true,
      tableWidth: "100%",
      columnSorting: false,
      defaultColAlign: 'left',
      defaultColWidth: 175,
      toolbar: false,
      onevent: changed,
    }

    const tdata = JSON.parse(dataSetField.value);
    if(tdata.data && tdata.data.length > 0){
      options.data = tdata.data;
      options.style = tdata.style;
      options.minDimensions = [tdata.data[0].length, tdata.data.length]
    }else{
      options.minDimensions = [2,5]
    }

    spread = jspreadsheet(document.getElementById(`${prefix}-dataset-table`), options);

    return block;
  }
}
window.telepath.register('streams.blocks.TableBlock', TableDefinition);
