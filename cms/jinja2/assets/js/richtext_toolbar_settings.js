function makeInitialRichtextToolbarSticky(){
  if (localStorage.getItem("wagtail:draftail-toolbar") === null){
    localStorage.setItem('wagtail:draftail-toolbar', 'sticky');
  }
};

makeInitialRichtextToolbarSticky();