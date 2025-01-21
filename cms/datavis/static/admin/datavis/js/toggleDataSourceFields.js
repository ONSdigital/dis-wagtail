function togglePanelVisibility(dataSourceValue, csvField, manualField) {
    if(dataSourceValue === 'csv') {
        csvField.hidden = false;
        manualField.hidden = true;
    }
    else if(dataSourceValue === 'manual') {
        csvField.hidden = true;
        manualField.hidden = false;
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
