// ═══════════════════════════════════════════════════════════════
// Storage Service — localStorage with QuotaExceeded handling
// ═══════════════════════════════════════════════════════════════

export const StorageService = {
  save<T>(key: string, data: T): boolean {
    try {
      localStorage.setItem(key, JSON.stringify(data));
      return true;
    } catch (e) {
      if (e instanceof DOMException && e.name === 'QuotaExceededError') {
        console.error('[StorageService] localStorage quota exceeded.');
        return false;
      }
      throw e;
    }
  },

  load<T>(key: string): T | null {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : null;
    } catch {
      console.error(`[StorageService] Failed to parse key: ${key}`);
      return null;
    }
  },

  remove(key: string): void {
    localStorage.removeItem(key);
  },

  exportAll(): string {
    const data: Record<string, unknown> = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith('mindflow_')) {
        data[key] = JSON.parse(localStorage.getItem(key) || 'null');
      }
    }
    return JSON.stringify(data, null, 2);
  },

  importData(jsonString: string): boolean {
    try {
      const data = JSON.parse(jsonString) as Record<string, unknown>;
      for (const [key, value] of Object.entries(data)) {
        if (key.startsWith('mindflow_')) {
          localStorage.setItem(key, JSON.stringify(value));
        }
      }
      return true;
    } catch {
      console.error('[StorageService] Import failed — invalid JSON.');
      return false;
    }
  },

  clearAll(): void {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith('mindflow_')) keys.push(key);
    }
    keys.forEach((k) => localStorage.removeItem(k));
  },
};
