/* global ReadonlyStructBlockDefinition */
class CorrectionBlockDefinition extends ReadonlyStructBlockDefinition {
  frozenHelpText = '<b>This correction is published and cannot be deleted.</b>';

  hiddenFields = ['version_id'];
}

window.telepath.register('cms.core.blocks.panels.CorrectionBlock', CorrectionBlockDefinition);
