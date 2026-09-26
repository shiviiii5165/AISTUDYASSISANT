/**
 * LearnByGenie — Live Quiz IndexedDB Durability Journal (§3, §15)
 * =============================================================
 * Provides client-side durable buffering for live quiz answers.
 * When a student clicks an answer, it is recorded into IndexedDB FIRST,
 * immediately dispatched to the backend, and retained until server ACK.
 * If network fails or server returns 429/503, the unacknowledged answer
 * is preserved and retried safely with jittered exponential backoff.
 *
 * Backward-compatibility: Migrates any pending answers from legacy
 * teachgenie_live_db without losing data.
 */

export interface JournaledAnswer {
  id: string; // key: `${sessionId}_${questionId}`
  session_id: string;
  question_id: string;
  selected_option_id: string;
  response_time_ms: number;
  progression_token?: string;
  idempotency_key: string;
  timestamp: number;
  status: 'pending' | 'acked';
  retries: number;
}

const PRIMARY_DB_NAME = 'learnbygenie_live_db';
const LEGACY_DB_NAME = 'teachgenie_live_db';
const DB_VERSION = 1;
const STORE_NAME = 'live_quiz_journal';

let legacyMigrated = false;

async function migrateLegacyDB(primaryDb: IDBDatabase): Promise<void> {
  if (legacyMigrated || typeof window === 'undefined' || !window.indexedDB) return;
  legacyMigrated = true;

  try {
    const legacyReq = window.indexedDB.open(LEGACY_DB_NAME, DB_VERSION);
    legacyReq.onsuccess = () => {
      const legacyDb = legacyReq.result;
      if (!legacyDb.objectStoreNames.contains(STORE_NAME)) {
        legacyDb.close();
        return;
      }
      const tx = legacyDb.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const getAllReq = store.getAll();
      getAllReq.onsuccess = () => {
        const records: JournaledAnswer[] = getAllReq.result || [];
        if (records.length > 0) {
          const writeTx = primaryDb.transaction(STORE_NAME, 'readwrite');
          const writeStore = writeTx.objectStore(STORE_NAME);
          for (const item of records) {
            writeStore.put(item);
          }
        }
        legacyDb.close();
      };
      getAllReq.onerror = () => legacyDb.close();
    };
    legacyReq.onerror = () => {
      // Legacy DB does not exist or cannot be opened — normal for new users
    };
  } catch {
    // Graceful fallback
  }
}

function openJournalDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      return reject(new Error('IndexedDB not supported in this environment'));
    }
    const request = window.indexedDB.open(PRIMARY_DB_NAME, DB_VERSION);

    request.onupgradeneeded = (e: IDBVersionChangeEvent) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        store.createIndex('session_id', 'session_id', { unique: false });
        store.createIndex('status', 'status', { unique: false });
      }
    };

    request.onsuccess = async () => {
      const db = request.result;
      await migrateLegacyDB(db);
      resolve(db);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function recordPendingAnswer(
  sessionId: string,
  questionId: string,
  selectedOptionId: string,
  responseTimeMs: number,
  progressionToken?: string,
  idempotencyKey?: string
): Promise<JournaledAnswer> {
  const item: JournaledAnswer = {
    id: `${sessionId}_${questionId}`,
    session_id: sessionId,
    question_id: questionId,
    selected_option_id: selectedOptionId,
    response_time_ms: responseTimeMs,
    progression_token: progressionToken,
    idempotency_key: idempotencyKey || `${questionId}_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
    timestamp: Date.now(),
    status: 'pending',
    retries: 0,
  };

  try {
    const db = await openJournalDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.put(item);
      req.onsuccess = () => resolve(item);
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('[IndexedDBJournal] Failed to persist pending answer; falling back to memory', err);
    return item;
  }
}

export async function markAnswerAcked(sessionId: string, questionId: string): Promise<void> {
  const id = `${sessionId}_${questionId}`;
  try {
    const db = await openJournalDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.delete(id);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('[IndexedDBJournal] Failed to mark answer acked', err);
  }
}

export async function getPendingAnswers(sessionId: string): Promise<JournaledAnswer[]> {
  try {
    const db = await openJournalDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const index = store.index('session_id');
      const req = index.getAll(IDBKeyRange.only(sessionId));

      req.onsuccess = () => {
        const results = (req.result || []).filter((r: JournaledAnswer) => r.status === 'pending');
        resolve(results);
      };
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('[IndexedDBJournal] Failed to query pending answers', err);
    return [];
  }
}
