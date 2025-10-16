/**
 * Dataset chooser filter handler
 * Listens for changes to the published filter and triggers a new search
 */
const initDatasetChooser = () => {
  const publishedFilter = document.querySelector('select[name="published"]');

  if (!publishedFilter) {
    return;
  }

  publishedFilter.addEventListener('change', () => {
    // Trigger the search form submission to reload results with the new filter
    const searchForm = publishedFilter.closest('form');
    if (searchForm) {
      searchForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }
  });
};

// Initialize when the chooser modal is shown
document.addEventListener('shown.bs.modal', initDatasetChooser);

// Also initialize on page load in case the chooser is embedded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDatasetChooser);
} else {
  initDatasetChooser();
}
