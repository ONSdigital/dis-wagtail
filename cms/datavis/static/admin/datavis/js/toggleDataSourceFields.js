function togglePanelVisibility(dataSourceValue, csvField, manualField) {
    if(dataSourceValue === 'csv') {
        /* eslint-disable no-param-reassign */
        csvField.hidden = false;
        manualField.hidden = true;
        /* eslint-enable no-param-reassign */
    }
    else if(dataSourceValue === 'manual') {
        /* eslint-disable no-param-reassign */
        csvField.hidden = true;
        manualField.hidden = false;
        /* eslint-enable no-param-reassign */
    }
};

function initializeToggleBehaviour() {
    const dataSourceSelect = document.getElementById("id_data_source");
    const csvField = document.getElementById("panel-child-data-data_file-section");
    const dataManualField = document.getElementById("panel-child-data-data_manual-section");
    if(dataSourceSelect !== null) {
        togglePanelVisibility(dataSourceSelect.value, csvField, dataManualField);
        dataSourceSelect.onchange = () => {
            // Update indicator to reflect changes
            togglePanelVisibility(dataSourceSelect.value, csvField, dataManualField);
        };
    }
}

document.addEventListener("DOMContentLoaded", initializeToggleBehaviour);
