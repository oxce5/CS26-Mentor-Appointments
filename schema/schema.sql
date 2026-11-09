CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY,
    student_id      INTEGER NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    umindanao_email TEXT    NOT NULL CHECK (length(trim(umindanao_email)) > 0),
    created_at      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mentors (
    id              INTEGER PRIMARY KEY,
    student_id      INTEGER NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    umindanao_email TEXT    NOT NULL CHECK (length(trim(umindanao_email)) > 0),
    created_at      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mentor_subjects (
    mentor_id INTEGER NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
    subject   TEXT    NOT NULL,
    PRIMARY KEY (mentor_id, subject)
);
