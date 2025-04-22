document.addEventListener('DOMContentLoaded', () => {
    const editForm = document.getElementById("page-edit-form");

    if (!editForm) {
        return; // Exit if the edit form is not found
    }

    // Store the initial form payload on load
    const initialFormPayload = new URLSearchParams(new FormData(editForm)).toString();

    // Function to toggle approve buttons based on form changes
    function toggleApproveButtons() {
        const newPayload = new URLSearchParams(new FormData(editForm)).toString();
        const approveButtons = document.querySelectorAll('[data-workflow-action-name="approve"]');

        if (initialFormPayload !== newPayload) {
            // Disable the approve buttons when form has changed
            approveButtons.forEach(button => {
                button.setAttribute('disabled', 'disabled');
                button.classList.add('disabled');
            });
        } else {
            // Re-enable the buttons when form returns to initial state
            approveButtons.forEach(button => {
                button.removeAttribute('disabled');
                button.classList.remove('disabled');
            });
        }
    }

    // Add event listeners to form elements to detect changes
    const formElements = editForm.querySelectorAll('input, textarea, select');
    formElements.forEach(element => {
        element.addEventListener('change', toggleApproveButtons);
        element.addEventListener('input', toggleApproveButtons);
    });

    // Also listen for changes that might be triggered by JavaScript
    editForm.addEventListener('change', toggleApproveButtons);

    // Initial check
    toggleApproveButtons();
});
