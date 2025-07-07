function toggleDateTextVisibility() {
  const statusField = document.getElementById('id_status');
  if (!statusField) {
    return;
  }
  const isProvisional = statusField.value.toLowerCase() === 'provisional';

  const dateTextInput = document.getElementById('id_release_date_text');
  if (dateTextInput) {
    const panelWrapper = dateTextInput.closest('.w-panel__wrapper');
    panelWrapper.style.display = isProvisional ? 'block' : 'none';
  }
}

document.addEventListener('DOMContentLoaded', function () {
  toggleDateTextVisibility();

  const statusField = document.getElementById('id_status');
  statusField?.addEventListener('change', toggleDateTextVisibility);
});
