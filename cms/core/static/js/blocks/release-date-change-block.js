/* global ReadonlyStructBlockDefinition */
class ReleaseDateChangeBlockDefinition extends ReadonlyStructBlockDefinition {
  frozenHelpText = '<b>This release date change is published and cannot be deleted.</b>';
}

window.telepath.register(
  'cms.release_calendar.blocks.ReleaseDateChangeBlock',
  ReleaseDateChangeBlockDefinition,
);
