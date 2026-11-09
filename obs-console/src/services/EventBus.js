// 1. Create and export a single, shared event emitter.
export const eventBus = new EventTarget();

// 2. Define and export event names to avoid typos.
export const USERS_UPDATED_EVENT = 'onUsersUpdated';