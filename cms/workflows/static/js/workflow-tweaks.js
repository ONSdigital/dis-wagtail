document.addEventListener('DOMContentLoaded', () => {
  const editForm = document.getElementById('page-edit-form');

  if (!editForm) {
    return; // Exit if the edit form is not found
  }

  // Store the initial form payload on load
  const initialFormPayload = new URLSearchParams(new FormData(editForm)).toString();

  // Function to toggle approve buttons based on form changes
  function toggleApproveButtons() {
    const newPayload = new URLSearchParams(new FormData(editForm)).toString();
    const approveButtons = document.querySelectorAll('[data-workflow-action-name="approve"]');

    const formHasChanged = initialFormPayload !== newPayload;
    // Disable the 'approve' buttons when the form has changed and re-enable them when it returns to its initial state
    /* eslint no-param-reassign: ["error", { "props": false }] */
    approveButtons.forEach((button) => {
      button.disabled = formHasChanged;
      button.classList.toggle('disabled', formHasChanged);
    });
  }

  // Listen to form changes
  editForm.addEventListener('change', toggleApproveButtons);
  editForm.addEventListener('input', toggleApproveButtons);

  // Initial check
  toggleApproveButtons();
});
