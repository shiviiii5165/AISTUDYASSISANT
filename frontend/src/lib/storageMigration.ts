/**
 * LearnByGenie — Backward-Compatible Persisted Storage Migration
 * =============================================================
 * Implements non-destructive dual-read migration for localStorage
 * and sessionStorage keys:
 * 1. Checks new LearnByGenie key first.
 * 2. If absent, checks legacy TeachGenie key.
 * 3. Migrates value to new LearnByGenie key.
 * 4. Preserves legacy key during transition period to ensure zero data loss.
 */

export function getMigratedStorageItem(
  newKey: string,
  legacyKey: string,
  storageType: 'local' | 'session' = 'local'
): string | null {
  if (typeof window === 'undefined') return null;
  const storage = storageType === 'local' ? window.localStorage : window.sessionStorage;
  if (!storage) return null;

  try {
    const val = storage.getItem(newKey);
    if (val !== null) {
      return val;
    }

    const legacyVal = storage.getItem(legacyKey);
    if (legacyVal !== null) {
      // Migrate to new key
      try {
        storage.setItem(newKey, legacyVal);
      } catch {
        // quota exceeded or storage disabled — continue gracefully
      }
      return legacyVal;
    }
  } catch {
    return null;
  }

  return null;
}

export function setMigratedStorageItem(
  newKey: string,
  legacyKey: string,
  value: string,
  storageType: 'local' | 'session' = 'local'
): void {
  if (typeof window === 'undefined') return;
  const storage = storageType === 'local' ? window.localStorage : window.sessionStorage;
  if (!storage) return;

  try {
    storage.setItem(newKey, value);
    // Keep legacy key in sync for backward compatibility during transition
    storage.setItem(legacyKey, value);
  } catch {
    // quota exceeded or disabled
  }
}

export function removeMigratedStorageItem(
  newKey: string,
  legacyKey: string,
  storageType: 'local' | 'session' = 'local'
): void {
  if (typeof window === 'undefined') return;
  const storage = storageType === 'local' ? window.localStorage : window.sessionStorage;
  if (!storage) return;

  try {
    storage.removeItem(newKey);
    storage.removeItem(legacyKey);
  } catch {
    // ignore
  }
}
