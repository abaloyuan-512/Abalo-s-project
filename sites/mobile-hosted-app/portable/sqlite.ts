import { DatabaseSync } from "node:sqlite";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

type Value = null | number | bigint | string | Uint8Array;
type Row = Record<string, Value>;
export type SqlResult<T = Row> = {
  success: true;
  results: T[];
  meta: { changes: number; last_row_id: number; duration: number };
};

/** The D1 statement operations used by the existing app and Drizzle adapter. */
export class SqliteStatement {
  readonly database: DatabaseSync;
  readonly sql: string;
  readonly values: Value[];
  constructor(database: DatabaseSync, sql: string, values: Value[] = []) {
    this.database = database;
    this.sql = sql;
    this.values = values;
  }
  bind(...values: Value[]): SqliteStatement {
    return new SqliteStatement(this.database, this.sql, values);
  }
  execute<T = Row>(): SqlResult<T> {
    const started = performance.now();
    const statement = this.database.prepare(this.sql);
    const before = this.database.prepare("SELECT total_changes() AS n").get()!.n as number;
    const results = statement.columns().length ? statement.all(...this.values) : [];
    let changes = 0;
    let lastId = 0;
    if (!statement.columns().length) {
      const info = statement.run(...this.values);
      changes = Number(info.changes);
      lastId = Number(info.lastInsertRowid);
    } else {
      const after = this.database.prepare("SELECT total_changes() AS n, last_insert_rowid() AS id").get()!;
      changes = Number(after.n) - Number(before);
      lastId = Number(after.id);
    }
    return { success: true, results: results as T[], meta: {
      changes, last_row_id: lastId, duration: performance.now() - started,
    } };
  }
  async run<T = Row>(): Promise<SqlResult<T>> { return this.execute<T>(); }
  async all<T = Row>(): Promise<SqlResult<T>> { return this.execute<T>(); }
  async first<T = Row>(column?: string): Promise<T | null> {
    const row = this.database.prepare(this.sql).get(...this.values) as Row | undefined;
    if (!row) return null;
    if (column !== undefined && !(column in row)) throw new Error("Unknown result column");
    return (column === undefined ? row : row[column]) as T;
  }
  async raw<T = Value[]>(options?: { columnNames?: boolean }): Promise<T[]> {
    const statement = this.database.prepare(this.sql);
    statement.setReturnArrays(true);
    const rows = statement.all(...this.values) as unknown as T[];
    return options?.columnNames ? [statement.columns().map(c => c.name) as T, ...rows] : rows;
  }
}

/** Single-instance SQLite storage; mount the database directory persistently. */
export class SqliteDatabase {
  readonly connection: DatabaseSync;
  constructor(filename: string) {
    if (filename !== ":memory:") mkdirSync(dirname(resolve(filename)), { recursive: true, mode: 0o700 });
    this.connection = new DatabaseSync(filename);
    this.connection.exec("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;");
  }
  prepare(sql: string): SqliteStatement { return new SqliteStatement(this.connection, sql); }
  async batch<T = Row>(statements: SqliteStatement[]): Promise<SqlResult<T>[]> {
    // No awaits inside the transaction: concurrent HTTP requests cannot interleave.
    this.connection.exec("BEGIN IMMEDIATE");
    try {
      const results = statements.map(s => {
        if (s.database !== this.connection) throw new Error("Cross-database batch is unsupported");
        return s.execute<T>();
      });
      this.connection.exec("COMMIT");
      return results;
    } catch (error) {
      this.connection.exec("ROLLBACK");
      throw error;
    }
  }
  close(): void { this.connection.close(); }
}
