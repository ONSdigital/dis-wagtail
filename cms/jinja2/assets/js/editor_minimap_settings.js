function setInitialMinimapExpanded(){
  if (localStorage.getItem("wagtail:minimap-expanded") === null){
    localStorage.setItem('wagtail:minimap-expanded', true);
  }
};

setInitialMinimapExpanded();