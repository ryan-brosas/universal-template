import type { Session } from './session.ts';

/** Extra Chrome-extension commands (tabs / windows / groups). Browser-level; extension transport only. */
export const bindChrome = (session: Session) => ({
  updateTab: (params: Record<string, unknown>) => session._call('Chrome.updateTab', params),
  moveTabs: (params: Record<string, unknown>) => session._call('Chrome.moveTabs', params),
  discardTab: (params: Record<string, unknown>) => session._call('Chrome.discardTab', params),
  reloadTab: (params: Record<string, unknown>) => session._call('Chrome.reloadTab', params),
  duplicateTab: (params: Record<string, unknown>) => session._call('Chrome.duplicateTab', params),
  highlight: (params: Record<string, unknown>) => session._call('Chrome.highlight', params),
  group: (params: Record<string, unknown>) => session._call('Chrome.group', params),
  ungroup: (params: Record<string, unknown>) => session._call('Chrome.ungroup', params),
  getTabGroups: (params: Record<string, unknown> = {}) => session._call('Chrome.getTabGroups', params),
  updateTabGroup: (params: Record<string, unknown>) => session._call('Chrome.updateTabGroup', params),
  moveTabGroup: (params: Record<string, unknown>) => session._call('Chrome.moveTabGroup', params),
  getWindows: (params: Record<string, unknown> = {}) => session._call('Chrome.getWindows', params),
  createWindow: (params: Record<string, unknown> = {}) => session._call('Chrome.createWindow', params),
  updateWindow: (params: Record<string, unknown>) => session._call('Chrome.updateWindow', params),
  removeWindow: (params: Record<string, unknown>) => session._call('Chrome.removeWindow', params),
});

export type ChromeApi = ReturnType<typeof bindChrome>;
