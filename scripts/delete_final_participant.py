#!/usr/bin/env python3
"""Offline Final participant erasure. Dry-run by default; see FINAL_DATA_DELETION_GUIDE.md.

All application workers MUST be stopped and their in-memory timing buffers flushed
before using this tool. The database must be the isolated Final database.
"""
import argparse
import os
import re
import sys
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text

CHILD_TABLES = ('eligibility_player', 'attitudes_player', 'random_matrix_player', 'household_player', 'otree_chatmessage')
EXPECTED_COUNTS = {'eligibility_player': 1, 'attitudes_player': 1, 'random_matrix_player': 6, 'household_player': 1}


def run(url, reference, execute=False):
    if not re.fullmatch(r'[A-Za-z0-9]{8,16}', reference):
        raise ValueError('Invalid reference ID format.')
    if not url or not url.startswith(('sqlite:///', 'postgresql://', 'postgres://')):
        raise ValueError('Set FINAL_DELETION_DATABASE_URL to the isolated Final database URL.')
    url = url.replace('postgres://', 'postgresql://', 1)
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            if engine.dialect.name == 'sqlite':
                conn.execute('PRAGMA foreign_keys=ON')
            tx = conn.begin()
            if engine.dialect.name == 'sqlite':
                conn.execute('BEGIN IMMEDIATE')
            try:
                md = MetaData()
                required = ('otree_participant', 'otree_session', 'otree_pagetimebatch') + CHILD_TABLES
                tables = {name: Table(name, md, autoload=True, autoload_with=conn) for name in required}
                # Refuse unexpected direct participant relations, rather than silently orphaning them.
                inspector = inspect(conn)
                refs = {name for name in inspector.get_table_names() for fk in inspector.get_foreign_keys(name)
                        if fk['referred_table'] == 'otree_participant'}
                if refs != set(CHILD_TABLES):
                    raise ValueError('Unexpected participant-linked schema; review before deletion.')
                if engine.dialect.name == 'postgresql':
                    for name in sorted(required):
                        conn.execute(text('LOCK TABLE "' + name + '" IN ACCESS EXCLUSIVE MODE'))
                p = tables['otree_participant']
                rows = conn.execute(select([p.c.id, p.c.code, p.c._session_code]).where(p.c.code == reference)).fetchall()
                if len(rows) != 1:
                    raise ValueError('Reference ID must match exactly one participant.')
                pid, _, session_code = rows[0]
                eligibility = tables['eligibility_player']
                version = conn.execute(select([eligibility.c.survey_flow_version]).where(eligibility.c.participant_id == pid)).fetchall()
                if len(version) != 1 or version[0][0] != 'final':
                    raise ValueError('The participant is not from a Final session; refusing to modify it.')
                counts = {}
                for name in CHILD_TABLES:
                    t = tables[name]
                    counts[name] = len(conn.execute(select([t.c.id]).where(t.c.participant_id == pid)).fetchall())
                if any(counts[name] != count for name, count in EXPECTED_COUNTS.items()):
                    raise ValueError('Unexpected participant row counts; no changes made.')
                batches = tables['otree_pagetimebatch']
                updates = []
                time_rows = 0
                for batch_id, content in conn.execute(select([batches.c.id, batches.c.text])):
                    retained = []
                    for line in (content or '').splitlines(keepends=True):
                        values = line.rstrip('\r\n').split(',')
                        if len(values) != 10:
                            raise ValueError('Unrecognized native timing batch format; no changes made.')
                        if values[0] == session_code and values[2] == reference:
                            time_rows += 1
                        else:
                            retained.append(line)
                    replacement = ''.join(retained)
                    if replacement != (content or ''):
                        updates.append((batch_id, replacement))
                print(f'Matched one Final participant; linked row counts: {counts}; native timing rows: {time_rows}.')
                if execute:
                    for batch_id, replacement in updates:
                        conn.execute(batches.update().where(batches.c.id == batch_id).values(text=replacement))
                    for name in CHILD_TABLES:
                        t = tables[name]
                        conn.execute(t.delete().where(t.c.participant_id == pid))
                    result = conn.execute(p.delete().where(p.c.id == pid))
                    if result.rowcount != 1:
                        raise ValueError('Participant deletion did not affect exactly one row.')
                    tx.commit()
                    print('Database transaction committed. External copies, logs and backups still need handling.')
                else:
                    tx.rollback()
                    print('Dry run only; no data changed.')
            except BaseException:
                if tx.is_active: tx.rollback()
                raise
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference_id', help='Survey Reference ID (avoid shared terminal history)')
    parser.add_argument('--execute', action='store_true', help='Delete after explicit interactive confirmation')
    parser.add_argument('--maintenance-confirmed', action='store_true', help='All workers stopped, buffers flushed, backup verified')
    args = parser.parse_args()
    try:
        if args.execute:
            if not args.maintenance_confirmed:
                raise ValueError('Stop all workers, flush timing buffers and verify backup before execution.')
            confirm = input('Type the exact Reference ID to confirm irreversible database deletion: ').strip()
            if confirm != args.reference_id:
                raise ValueError('Confirmation did not match; no changes made.')
        run(os.environ.get('FINAL_DELETION_DATABASE_URL'), args.reference_id, args.execute)
    except Exception as exc:
        # Database exceptions may contain credentials or query values; avoid printing them.
        message = str(exc) if isinstance(exc, ValueError) else 'Database operation failed; transaction rolled back.'
        print('ERROR: ' + message, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
