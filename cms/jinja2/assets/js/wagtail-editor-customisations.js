function setInitialMinimapExpandedByDefault() {
  if (localStorage.getItem('wagtail:minimap-expanded') === null) {
    localStorage.setItem('wagtail:minimap-expanded', true);
  }
}

function setInitialRichtextToolbarStickyByDefault() {
  if (localStorage.getItem('wagtail:draftail-toolbar') === null) {
    localStorage.setItem('wagtail:draftail-toolbar', 'sticky');
  }
}

setInitialMinimapExpandedByDefault();
setInitialRichtextToolbarStickyByDefault();
