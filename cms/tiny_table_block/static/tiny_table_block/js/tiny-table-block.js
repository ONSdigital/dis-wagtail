/* global tinymce */
class TinyTableBlockDefinition extends window.wagtailStreamField.blocks.StructBlockDefinition {
  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);

    tinymce.init({
        selector: "#" + prefix + "-data",
        plugins: "table autoresize",
        menubar: "",
        toolbar: "undo redo | table | tablerowheader tablecolheader tablemergecells tablesplitcells | tableinsertcolbefore tableinsertcolafter tableinsertrowbefore tableinsertrowafter",
        valid_elements: 'table[border|width|height|align|summary],tr[align|valign],td[align|valign|width|colspan|rowspan],th[align|valign|width|colspan|rowspan],a[href|target|rel],caption',
        table_toolbar: "",  // disable the floating toolbar
        table_advtab: false,
        table_cell_advtab: false,
        table_row_advtab: false,
        table_clone_elements: '',
        contextmenu_never_use_native: true,
        skin: (window.matchMedia("(prefers-color-scheme: dark)").matches ? "oxide-dark" : "oxide"),
        content_css: (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default"),
        branding: false,
        promotion: false,
        license_key: "gpl",
    });

    return block;
  }
}

window.telepath.register("streamblock.blocks.TinyTableBlockAdapter", TinyTableBlockDefinition);
