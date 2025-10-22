/**
 * Dataset chooser published filter handler
 * Automatically submits the search form when the published status filter changes
 */
(function initDatasetChooser() {
  const $ = window.jQuery;
  const getClosestForm = (element) => element.closest('form[data-chooser-modal-search]');
  const BOOTSTRAP_MODAL_SHOWN_EVENT = 'shown.bs.modal';
  const PUBLISHED_SELECTOR = 'select[name="published"]';

  const updateMultipleChoiceFormPublishedFilter = (form, publishedValue) => {
    const sibling = form?.nextElementSibling;
    if (sibling?.matches('[data-multiple-choice-form]')) {
      // This is a modal with a multiple choice form (the sibling).
      // We need to append the published filter to it as well.
      let publishedInput = sibling.querySelector('input[name="published"]');
      if (!publishedInput) {
        // Field doesn't exist yet, create it
        publishedInput = document.createElement('input');
        publishedInput.type = 'hidden';
        publishedInput.name = 'published';
        sibling.appendChild(publishedInput);
      }
      publishedInput.value = publishedValue;
    }
  };

  // Use event delegation to handle changes to the published filter
  // This works for both initial page load and dynamically loaded modals
  document.addEventListener('change', ({ target }) => {
    // Check if the changed element is the published filter within a chooser modal
    if (target.matches(PUBLISHED_SELECTOR)) {
      const searchForm = getClosestForm(target);
      if (searchForm) {
        // Trigger form submission to reload results with the new filter
        searchForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));

        // Also update the multiple choice form if present
        updateMultipleChoiceFormPublishedFilter(searchForm, target.value);
      }
    }
  });

  // Run when a modal is shown
  $('body').on(BOOTSTRAP_MODAL_SHOWN_EVENT, (e) => {
    const modal = e.target;
    const publishedSelect = modal.querySelector(PUBLISHED_SELECTOR);
    if (publishedSelect) {
      updateMultipleChoiceFormPublishedFilter(
        getClosestForm(publishedSelect),
        publishedSelect.value,
      );
    }
  });
})();
