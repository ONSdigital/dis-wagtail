/**
 * Dataset chooser published filter handler
 * Automatically submits the search form when the published status filter changes
 */
(function initDatasetChooser() {
  // Use event delegation to handle changes to the published filter
  // This works for both initial page load and dynamically loaded modals
  document.addEventListener('change', ({ target }) => {
    // Check if the changed element is the published filter within a chooser modal
    if (target.matches('select[name="published"]')) {
      const searchForm = target.closest('form[data-chooser-modal-search]');
      if (searchForm) {
        // Trigger form submission to reload results with the new filter
        searchForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      }
    }
  });
})();
