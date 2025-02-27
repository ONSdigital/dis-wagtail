/* global tinymce */
class TinyTableBlockDefinition extends window.wagtailStreamField.blocks.FieldBlockDefinition {
  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);

    tinymce.init({
        selector: "#" + prefix,
        plugins: "table autoresize",
        menubar: "",
        toolbar: "undo redo | tablerowheader tablecolheader tablemergecells tablesplitcells | tableinsertcolbefore tableinsertcolafter tableinsertrowbefore tableinsertrowafter",
        valid_elements: 'br,table[border|width|height|align|summary],tr[align|valign],td[align|valign|width|colspan|rowspan],th[align|valign|width|colspan|rowspan|scope],thead,tbody,a[href|target|rel]',
        table_toolbar: "",  // disable the floating toolbar
        table_advtab: false,
        table_appearance_options: false,
        table_cell_advtab: false,
        table_row_advtab: false,
        table_sizing_mode: 'responsive',
        table_resize_bars: false,
        object_resizing: false,
        contextmenu_never_use_native: true,
        skin: (window.matchMedia("(prefers-color-scheme: dark)").matches ? "oxide-dark" : "oxide"),
        content_css: (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default"),
        statusbar: false,
        branding: false,
        promotion: false,
        license_key: "gpl",
        setup: (editor) => {
          let tableExists = false;

          editor.on("init", () => {
            tableExists = editor.getBody().getElementsByTagName("table").length > 0;
            if (!tableExists) {
                editor.execCommand("mceInsertTable", false, { rows: 2, columns: 2 });
            }
          });

          editor.on("change NodeChange SetContent", () => {
            // Check for tables after content changes
            tableExists = editor.getBody().getElementsByTagName('table').length > 0;
            // propagate the changes to the hidden input.
            editor.save();
          });

          editor.on("BeforeExecCommand", (e) => {
            // Don't allow inserting a table if one exists.
            if (e.command === 'mceInsertTable' && tableExists) {
              e.preventDefault();
            }
          });

          editor.on("ExecCommand", (e) => {
              if (e.command === "mceTableDelete") {
                  // re-add empty table on delete
                  editor.execCommand("mceInsertTable", false, {rows: 2, columns: 2});
              }
          });

          editor.on("PastePreProcess keydown", (e) => {
              // Only allow adding content into the one table
              const activeNode = editor.selection.getNode();
              const isCell = activeNode.nodeName === "TD" || activeNode.nodeName === "TH";
              const isParentCell = activeNode.parentNode.nodeName === "TD" || activeNode.parentNode.nodeName === "TH";
              if (!isCell && !isParentCell && e.keyCode !== 9) {
                e.preventDefault();
              }
          });
        }
    });

    return block;
  }
}

window.telepath.register("streamblock.blocks.TinyTableBlockAdapter", TinyTableBlockDefinition);
